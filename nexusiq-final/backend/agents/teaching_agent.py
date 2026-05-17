"""
NexusIQ — Teaching Agent.
Zero FastAPI imports.

FIX (BUG-1): Replaced `llm_router.get_llm()` + `llm.ainvoke()` with
             `llm_router.invoke(messages)` so the retry + key-rotation
             logic in LLMRouter is always active during teaching turns.
"""

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from orchestrator.state import NexusState
from orchestrator.logger import AgentLogger
from exceptions.base import AgentExecutionException
from db.redis_client import get_redis
from utils.llm_router import llm_router


async def teaching_agent(state: NexusState) -> NexusState:
    """Teaching Agent node — chat-based interactive tutor."""
    session_id    = state.get("session_id")
    current_module = state.get("current_module")
    input_data    = state.get("input_data", {})
    user_message  = input_data.get("user_message")

    if not session_id or not current_module:
        raise AgentExecutionException(
            "Missing required state fields: session_id or current_module"
        )
    if not user_message:
        raise AgentExecutionException("Missing user_message in input_data")

    redis_client = await get_redis()
    log = AgentLogger(session_id, "teaching_agent", redis_client)

    if "agents_status" not in state:
        state["agents_status"] = {}

    state["agents_status"]["teaching_agent"] = "running"
    await log.set_status("running")
    await log.log("INFO", "Teaching agent turn started")

    try:
        teaching_history: list[dict] = state.get("teaching_history", [])

        # ── Build prompt ──────────────────────────────────────────────────
        system_prompt = f"""You are an expert, conversational technical tutor teaching a software engineering module.

Current Module:
  Title: {current_module.get('title')}
  Concepts: {current_module.get('concepts', [])}
  Code Examples: {current_module.get('code_examples', [])}
  Learning Goals: {current_module.get('learning_goals', [])}

STRICT RULES:
1. Teach ONLY the concepts listed above. Never stray into other modules.
2. Use code examples ONLY from the list above — never invent new ones.
3. Be conversational, not lecture-style. Ask one clarifying question after each concept.
4. NO external links anywhere in your response.
5. IMPORTANT: Keep context of the full conversation history provided.
6. When you are completely certain ALL concepts have been understood by the learner,
   end your final message with exactly this token: [TEACHING_COMPLETE]
   Do not add any text after it."""

        messages = [SystemMessage(content=system_prompt)]

        for m in teaching_history:
            if m["role"] == "user":
                messages.append(HumanMessage(content=m["content"]))
            elif m["role"] == "assistant":
                messages.append(AIMessage(content=m["content"]))

        messages.append(HumanMessage(content=user_message))
        teaching_history.append({"role": "user", "content": user_message})

        await log.log("INFO", f"Sending {len(messages)} messages to LLM")

        # ── LLM call (BUG-1 FIX) ─────────────────────────────────────────
        # Always use llm_router.invoke() — never get_llm() + ainvoke() directly.
        # This ensures the retry decorator + key rotation + provider fallback
        # is active for EVERY teaching turn.
        response = await llm_router.invoke(messages)
        assistant_content: str = response.content

        teaching_history.append({"role": "assistant", "content": assistant_content})
        state["teaching_history"] = teaching_history

        # ── Completion check ──────────────────────────────────────────────
        if "[TEACHING_COMPLETE]" in assistant_content:
            state["agents_status"]["teaching_agent"] = "complete"
            await log.set_status("complete")
            await log.log("INFO", "Module teaching completed — moving to evaluation.")
        else:
            state["agents_status"]["teaching_agent"] = "running"
            await log.set_status("running")
            await log.log("INFO", "Teaching turn complete. Awaiting next user message.")

        return state

    except AgentExecutionException:
        state["error"] = "Teaching agent failed — check agent logs."
        state["agents_status"]["teaching_agent"] = "failed"
        await log.set_status("failed")
        await log.log("ERROR", "AgentExecutionException raised in teaching_agent")
        raise

    except Exception as exc:
        err = f"Unexpected error in teaching_agent: {exc}"
        state["error"] = err
        state["agents_status"]["teaching_agent"] = "failed"
        await log.set_status("failed")
        await log.log("ERROR", err)
        raise AgentExecutionException(err) from exc
