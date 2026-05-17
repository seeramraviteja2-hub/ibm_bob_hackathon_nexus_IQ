"""
NexusIQ — Interview Sub-Agent.
Zero FastAPI imports.

FIX (BUG-1): generate_question() now calls llm_router.invoke() instead of
             llm_router.get_llm() + llm.ainvoke(). This means rate-limit
             retry and provider fallback are active for every question
             generation turn — previously these were completely unprotected.
"""

import json
from langchain_core.messages import HumanMessage

from orchestrator.state import NexusState
from orchestrator.logger import AgentLogger
from exceptions.base import AgentExecutionException
from db.redis_client import get_redis
from utils.llm_router import llm_router
from utils.json_repair import safe_llm_json


# ── Helpers ───────────────────────────────────────────────────────────────────

async def generate_question(
    count: int,
    current_module: dict,
    task: dict,
    history: list[dict],
) -> str:
    """
    Generates the next interview question based on turn count.
    Q1-Q3  → Concept questions (test understanding)
    Q4-Q6  → Task-based questions (test genuine work)
    Q7-Q9  → Optimization / follow-up questions (detect copy-paste)
    """
    if 0 <= count < 3:
        q_type = (
            "Concept question. Ask the candidate to explain or apply a specific "
            "concept from the module. Do NOT ask them to write code."
        )
    elif 3 <= count < 6:
        q_type = (
            "Task-based question. Ask about a specific implementation decision "
            "or a particular requirement from their submitted task. "
            "Do NOT ask them to write new code."
        )
    else:  # 6 <= count < 9
        q_type = (
            "Optimization / follow-up question. Ask about edge cases, performance "
            "improvements, or scalability considerations related to the module. "
            "Do NOT ask them to write code."
        )

    past_questions = [
        m["content"] for m in history if m["role"] == "assistant"
    ]

    prompt = f"""You are a senior technical interviewer conducting a structured evaluation.
Generate exactly ONE interview question.

Question type required: {q_type}

Module Concepts: {current_module.get('concepts', [])}
Submitted Task: {task.get('task_title', '')} — {task.get('description', '')}
Questions already asked (DO NOT REPEAT): {past_questions}

RULES:
1. Return ONLY the question text. Zero preamble, zero markdown.
2. The question must be concise and directly answerable in 3-5 sentences.
3. Never repeat a question that was already asked."""

    # BUG-1 FIX: use llm_router.invoke() — not get_llm() + ainvoke() directly.
    response = await llm_router.invoke([HumanMessage(content=prompt)])
    return response.content.strip()


async def score_answer(question: str, answer: str) -> dict:
    """
    Scores a candidate's answer 0-10 and returns structured feedback.
    Already used safe_llm_json (which calls llm_router.invoke) — no change needed.
    """
    words = answer.split()
    if len(words) < 10 or answer.strip() == question.strip():
        return {
            "score": 0,
            "feedback": "Answer was too short or identical to the question.",
        }

    prompt = f"""You are an expert technical interviewer evaluating a candidate's response.

Question: {question}
Candidate's answer: {answer}

Score the answer 0-10 (integers only). Consider:
- Technical accuracy
- Depth of understanding
- Clarity of explanation
- Whether it sounds like genuine understanding vs. memorization

Return ONLY a valid JSON object — no markdown, no preamble:
{{
    "score": <0-10 integer>,
    "feedback": "<one concise sentence explaining the score>"
}}"""

    result = await safe_llm_json(
        llm_router,
        [HumanMessage(content=prompt)],
        expected_keys=["score", "feedback"],
    )
    result["score"] = max(0, min(10, int(result.get("score", 0))))
    return result


# ── Main agent node ───────────────────────────────────────────────────────────

async def interview_sub_agent(state: NexusState) -> NexusState:
    """Interview Sub-Agent — 9-question chat interview."""
    session_id     = state.get("session_id")
    current_module = state.get("current_module")
    input_data     = state.get("input_data", {})
    task           = input_data.get("generated_task", {})

    if not session_id or not current_module:
        raise AgentExecutionException(
            "Missing required state fields: session_id or current_module"
        )

    redis_client = await get_redis()
    log = AgentLogger(session_id, "interview_sub_agent", redis_client)

    if "agents_status" not in state:
        state["agents_status"] = {}

    state["agents_status"]["interview_sub_agent"] = "running"
    await log.set_status("running")

    try:
        count        = state.get("interview_question_count", 0)
        history      = state.get("interview_history", [])
        scores_list  = input_data.get("interview_scores", [])
        user_message = input_data.get("user_message")

        await log.log("INFO", f"Interview turn {count + 1}/9 started")

        # ── Turn 0: generate first question ──────────────────────────────
        if count == 0:
            question = await generate_question(count, current_module, task, history)
            history.append({"role": "assistant", "content": question})

            state["interview_question_count"] = 1
            state["interview_history"] = history
            state["input_data"]["interview_scores"] = []
            await log.log("INFO", f"Generated Q1")

        # ── Turns 1-8: score previous answer, generate next question ─────
        elif 1 <= count < 9:
            if not user_message:
                raise AgentExecutionException(
                    "Missing user_message for interview answer turn"
                )

            history.append({"role": "user", "content": user_message})

            # Find the last question (last assistant message)
            last_question = next(
                (m["content"] for m in reversed(history[:-1]) if m["role"] == "assistant"),
                "",
            )

            score_data = await score_answer(last_question, user_message)
            scores_list.append(score_data["score"])
            await log.log("INFO", f"Q{count} scored: {score_data['score']}/10")

            # Generate next question
            next_q = await generate_question(count, current_module, task, history)
            history.append({"role": "assistant", "content": next_q})

            state["interview_question_count"] = count + 1
            state["interview_history"] = history
            state["input_data"]["interview_scores"] = scores_list
            await log.log("INFO", f"Generated Q{count + 1}")

        # ── Turn 9: score final answer, compute result ────────────────────
        elif count == 9:
            if not user_message:
                raise AgentExecutionException(
                    "Missing user_message for final interview answer"
                )

            history.append({"role": "user", "content": user_message})

            last_question = next(
                (m["content"] for m in reversed(history[:-1]) if m["role"] == "assistant"),
                "",
            )
            score_data = await score_answer(last_question, user_message)
            scores_list.append(score_data["score"])
            await log.log("INFO", f"Q9 scored: {score_data['score']}/10")

            # Compute final interview score (out of 100)
            final_score = (sum(scores_list) / 90.0) * 100.0
            state["interview_score"] = float(final_score)

            feedback_block = {
                "total_score": round(final_score, 2),
                "per_question_scores": scores_list,
                "feedback": "Interview completed. Results recorded.",
            }
            closing = (
                "Thank you for completing the interview. "
                f"Your responses have been recorded.\n\n"
                f"[INTERVIEW_DONE]{json.dumps(feedback_block)}"
            )
            history.append({"role": "assistant", "content": closing})

            state["interview_question_count"] = 9
            state["interview_history"] = history
            state["input_data"]["interview_scores"] = scores_list
            state["agents_status"]["interview_sub_agent"] = "complete"
            await log.set_status("complete")
            await log.log("INFO", f"Interview finished. Final score: {round(final_score, 2)}%")

        else:
            raise AgentExecutionException(
                f"Invalid interview_question_count: {count}. Expected 0-9."
            )

        return state

    except AgentExecutionException:
        state["error"] = "Interview agent failed — check agent logs."
        state["agents_status"]["interview_sub_agent"] = "failed"
        await log.set_status("failed")
        await log.log("ERROR", "AgentExecutionException in interview_sub_agent")
        raise

    except Exception as exc:
        err = f"Unexpected error in interview_sub_agent: {exc}"
        state["error"] = err
        state["agents_status"]["interview_sub_agent"] = "failed"
        await log.set_status("failed")
        await log.log("ERROR", err)
        raise AgentExecutionException(err) from exc
