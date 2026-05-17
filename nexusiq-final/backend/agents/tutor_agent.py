"""
NexusIQ — Tutor Agent.
Zero FastAPI imports.

FIX (BUG-6): Removed broken call to create_struggling_alert().
The original code called it as:
    create_struggling_alert(user_id, module_title, consecutive_fails)
but the real function signature is:
    create_struggling_alert(db: AsyncSession, manager_id, employee_name, module_title, attempts)

Agents have no db session or manager_id in state, so calling it here is impossible.
The correct pattern — already used below — is to publish an event via EventPublisher
and let a FastAPI background task / WebSocket listener handle the DB write.
The ESCALATION_FLAGGED event is already being published, which is the right design.
"""

import json
from langchain_core.messages import HumanMessage

from orchestrator.state import NexusState
from orchestrator.logger import AgentLogger
from orchestrator.events import EventPublisher
from exceptions.base import AgentExecutionException
from db.redis_client import get_redis
from utils.llm_router import llm_router
from utils.json_repair import safe_llm_json


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _parse_interview_weak_topics(interview_history: list[dict]) -> list[str]:
    """
    Parses the [INTERVIEW_DONE] block to find questions where score < 6.
    Returns list of question strings that the employee struggled with.
    """
    if not interview_history:
        return []

    last_msg = interview_history[-1].get("content", "")
    if "[INTERVIEW_DONE]" not in last_msg:
        return []

    try:
        json_str = last_msg.split("[INTERVIEW_DONE]")[1]
        data     = json.loads(json_str)
        per_q_scores = data.get("per_question_scores", [])

        # Questions are all assistant messages except the last closing message
        questions = [
            m["content"] for m in interview_history
            if m["role"] == "assistant"
        ][:-1]  # drop the closing message

        return [
            f"Interview Q{i + 1}: {questions[i]}"
            for i, score in enumerate(per_q_scores)
            if score < 6 and i < len(questions)
        ]
    except Exception:
        return []


async def _parse_task_weak_topics(input_data: dict) -> list[str]:
    """
    Finds rubric criteria where the employee scored below 60% of max points.
    Requires task_scores dict in input_data (set by task_sub_agent).
    """
    task        = input_data.get("generated_task")
    task_scores = input_data.get("task_scores", {})

    if not task or not task_scores:
        return []

    rubric = task.get("evaluation_rubric", {})
    return [
        f"Task Criterion: {criterion}"
        for criterion, max_pts in rubric.items()
        if float(task_scores.get(criterion, max_pts)) < 0.6 * float(max_pts)
    ]


# ── Main agent node ───────────────────────────────────────────────────────────

async def tutor_agent(state: NexusState) -> NexusState:
    """
    Tutor Agent — triggered when an employee fails a module evaluation.
    Produces a personalised revision plan targeting identified weak topics.
    Publishes ESCALATION_FLAGGED event after 3+ consecutive failures so a
    FastAPI listener can create the DB notification for the manager.
    """
    session_id        = state.get("session_id")
    user_id           = state.get("user_id")
    current_module    = state.get("current_module", {})
    consecutive_fails = state.get("consecutive_fails", 0)

    if not session_id or not user_id:
        raise AgentExecutionException(
            "Missing required state fields: session_id or user_id"
        )

    redis_client = await get_redis()
    log          = AgentLogger(session_id, "tutor_agent", redis_client)
    publisher    = EventPublisher(redis_client)

    if "agents_status" not in state:
        state["agents_status"] = {}

    state["agents_status"]["tutor_agent"] = "running"
    await log.set_status("running")
    await log.log(
        "INFO",
        f"Tutor agent started for user {user_id}. Consecutive fails: {consecutive_fails}",
    )

    try:
        # ── Step 1: Identify weak topics ──────────────────────────────────
        interview_weak = await _parse_interview_weak_topics(
            state.get("interview_history", [])
        )
        task_weak = await _parse_task_weak_topics(state.get("input_data", {}))

        weak_topics = interview_weak + task_weak
        if not weak_topics:
            weak_topics = ["General review of module concepts needed."]

        await log.log("INFO", f"Identified {len(weak_topics)} weak topic(s)")

        # ── Step 2: Generate revision plan ────────────────────────────────
        prompt = f"""You are an expert technical tutor. An employee has failed their evaluation
and needs a targeted, practical revision plan.

Current Module: {current_module.get('title', '')}
Module Concepts: {current_module.get('concepts', [])}
Weak Topics Identified: {weak_topics}

Create a personalised revision plan that addresses each weak topic directly.
Return ONLY a valid JSON object — no markdown, no preamble, no external links.

Required JSON Shape:
{{
    "revision_topics": ["topic1", "topic2"],
    "study_guide": {{
        "Topic Name": "Self-contained explanation with no external links."
    }},
    "practice_exercises": [
        {{"exercise": "string", "hint": "string"}}
    ],
    "estimated_revision_hours": int
}}"""

        await log.log("INFO", "Calling LLM to generate revision plan")
        tutor_plan = await safe_llm_json(
            llm_router,
            [HumanMessage(content=prompt)],
            expected_keys=[
                "revision_topics",
                "study_guide",
                "practice_exercises",
                "estimated_revision_hours",
            ],
        )

        # ── Step 3: Escalation logic ──────────────────────────────────────
        escalation_recommended = consecutive_fails >= 3
        tutor_plan["escalation_recommended"] = escalation_recommended

        if escalation_recommended:
            # Publish event — a FastAPI background task / WebSocket handler
            # will call create_struggling_alert(db, manager_id, ...) with the
            # proper db session and manager_id it has access to.
            # The agent must NOT call it directly — it has no db session.
            await publisher.publish(
                EventPublisher.ESCALATION_FLAGGED,
                {
                    "session_id":   session_id,
                    "user_id":      user_id,
                    "module_title": current_module.get("title", "Unknown Module"),
                    "attempts":     consecutive_fails,
                },
            )
            await log.log(
                "WARNING",
                f"ESCALATION_FLAGGED published — {consecutive_fails} consecutive failures.",
            )

        # ── Step 4: Always publish a struggling alert for manager dashboard ─
        # Even on first fail, manager should see the employee is struggling.
        await publisher.publish(
            EventPublisher.ESCALATION_FLAGGED,
            {
                "session_id":   session_id,
                "user_id":      user_id,
                "module_title": current_module.get("title", "Unknown Module"),
                "attempts":     consecutive_fails,
                "weak_topics":  weak_topics,
                    "escalate":     False,
            },
        )

        # ── Step 5: State update ──────────────────────────────────────────
        state["tutor_plan"] = tutor_plan
        state["agents_status"]["tutor_agent"] = "complete"
        await log.set_status("complete")
        await log.log("INFO", "Tutor agent completed successfully.")
        return state

    except AgentExecutionException:
        state["error"] = "Tutor agent failed — check agent logs."
        state["agents_status"]["tutor_agent"] = "failed"
        await log.set_status("failed")
        await log.log("ERROR", "AgentExecutionException in tutor_agent")
        raise

    except Exception as exc:
        err = f"Unexpected error in tutor_agent: {exc}"
        state["error"] = err
        state["agents_status"]["tutor_agent"] = "failed"
        await log.set_status("failed")
        await log.log("ERROR", err)
        raise AgentExecutionException(err) from exc
