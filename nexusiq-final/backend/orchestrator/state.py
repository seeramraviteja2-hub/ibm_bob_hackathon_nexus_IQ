"""
NexusIQ — Shared LangGraph state definition.
All agents read/write this TypedDict.
"""
from typing import Any, Optional
from typing_extensions import TypedDict


class NexusState(TypedDict, total=False):
    # ── Session identity ───────────────────────────────────────────────────
    session_id: str
    user_id: str
    mode: str                        # "new_project" | "legacy_codebase"

    # ── Setup-phase data ───────────────────────────────────────────────────
    input_data: dict                 # raw files / spec object references
    skill_manifest: dict             # output of requirement_agent
    course_plan: dict                # output of course_gen_agent

    # ── Interactive-phase data ─────────────────────────────────────────────
    current_module_index: int
    current_module: dict
    teaching_history: list[dict]     # {"role": "user"|"assistant", "content": str}
    interview_history: list[dict]
    interview_question_count: int
    generated_task: dict             # output of task_sub_agent (generation mode)
    task_score: float
    interview_score: float
    tutor_plan: dict                 # output of tutor_agent

    # ── Progress tracking ──────────────────────────────────────────────────
    total_modules: int
    completed_modules: int
    consecutive_fails: int
    passed: bool

    # ── Agent orchestration ────────────────────────────────────────────────
    agents_status: dict[str, str]    # agent_name → "running"|"complete"|"failed"|"idle"
    error: Optional[str]
