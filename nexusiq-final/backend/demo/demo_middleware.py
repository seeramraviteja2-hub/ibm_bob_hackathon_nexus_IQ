"""
NexusIQ — Demo middleware.
Wraps agent callables so that when DEMO_MODE=true, pre-baked responses
are returned without any LLM call. Agents still log + update agents_status.
"""
from typing import Callable

from demo.demo_cache import (
    DEMO_MODE,
    DEMO_TASK,
    DEMO_TEACHING_RESPONSE,
    DEMO_INTERVIEW_QUESTIONS,
)
from orchestrator.state import NexusState


# ── Pre-baked response factories ──────────────────────────────────────────────

def demo_teaching_response(state: NexusState) -> NexusState:
    history = state.get("teaching_history", [])
    user_msg = state.get("input_data", {}).get("user_message", "")
    history.append({"role": "user", "content": user_msg})

    turn = len([m for m in history if m["role"] == "assistant"])
    if turn >= 3:
        response = DEMO_TEACHING_RESPONSE + " [TEACHING_COMPLETE]"
        state["agents_status"] = {**state.get("agents_status", {}), "teaching_agent": "complete"}
    else:
        response = DEMO_TEACHING_RESPONSE
        state["agents_status"] = {**state.get("agents_status", {}), "teaching_agent": "running"}

    history.append({"role": "assistant", "content": response})
    state["teaching_history"] = history
    return state


def demo_task_response(state: NexusState) -> NexusState:
    input_data = state.get("input_data", {})
    if input_data.get("submission_object_name"):
        # Scoring mode — file was submitted
        state["task_score"] = 75.0
        input_data["task_feedback"] = (
            "Good implementation! Password hashing is correct and JWT is properly signed. "
            "Consider adding token expiry validation."
        )
        input_data["generated_task"] = DEMO_TASK
    else:
        # Generation mode — first visit to evaluate page
        input_data["generated_task"] = DEMO_TASK

    state["input_data"] = input_data
    state["agents_status"] = {**state.get("agents_status", {}), "task_sub_agent": "complete"}
    return state


def demo_interview_response(state: NexusState) -> NexusState:
    history  = state.get("interview_history", [])
    count    = state.get("interview_question_count", 0)
    user_msg = state.get("input_data", {}).get("user_message")

    if user_msg:
        history.append({"role": "user", "content": user_msg})

    if count >= 9:
        # Must match the exact format interview_sub_agent produces so the
        # service's [INTERVIEW_DONE] parser works correctly
        import json as _json
        feedback_block = {
            "score": 82,
            "passed": True,
            "strengths": ["Strong understanding of async Python", "Good grasp of FastAPI DI"],
            "improvements": ["Could elaborate more on JWT expiry handling"],
            "summary": "Excellent performance overall.",
        }
        closing = (
            "Excellent performance! You demonstrated strong understanding of async Python "
            f"and FastAPI. [INTERVIEW_DONE]{_json.dumps(feedback_block)}"
        )
        history.append({"role": "assistant", "content": closing})
        state["interview_score"] = 82.0
    else:
        question = DEMO_INTERVIEW_QUESTIONS[min(count, len(DEMO_INTERVIEW_QUESTIONS) - 1)]
        history.append({"role": "assistant", "content": question})

    state["interview_history"] = history
    state["interview_question_count"] = count + 1
    state["agents_status"] = {**state.get("agents_status", {}), "interview_sub_agent": "running"}
    return state


# ── Wrapper factory ───────────────────────────────────────────────────────────

def demo_wrap_agent(real_agent: Callable, demo_fn: Callable) -> Callable:
    """
    Returns an async callable that:
    - calls demo_fn(state) synchronously when DEMO_MODE=true
    - calls real_agent(state) normally when DEMO_MODE=false

    demo_fn may be sync (returns state dict) — we handle both.
    """
    import asyncio

    async def wrapped(state: NexusState) -> NexusState:
        if DEMO_MODE:
            result = demo_fn(state)
            # Support sync demo functions that return the modified state
            if asyncio.iscoroutine(result):
                return await result
            return result
        return await real_agent(state)

    return wrapped
