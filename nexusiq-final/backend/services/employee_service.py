"""
NexusIQ — Employee Service (Production Rewrite).

KEY FIX: _get_or_init_state rebuilds from DB when Redis state is missing.
All redis.set() calls now include ex=STATE_TTL (7 days).
"""
import json, uuid
from typing import Any
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from agents.interview_sub_agent import interview_sub_agent
from agents.task_sub_agent import task_sub_agent
from agents.teaching_agent import teaching_agent
from agents.tutor_agent import tutor_agent
from demo.demo_cache import DEMO_MODE
from demo.demo_middleware import (
    demo_teaching_response, demo_task_response,
    demo_interview_response, demo_wrap_agent,
)

# Pre-build wrapped agents once at module load — zero overhead per request
_teaching_agent   = demo_wrap_agent(teaching_agent,   demo_teaching_response)
_task_agent       = demo_wrap_agent(task_sub_agent,   demo_task_response)
_interview_agent  = demo_wrap_agent(interview_sub_agent, demo_interview_response)
_tutor_agent_fn   = demo_wrap_agent(tutor_agent,      lambda s: s)
from db.models import Course, EmployeeCourse, EmployeeCourseStatus, Module, ModuleProgress
from exceptions.base import AppException, AgentExecutionException, NotFoundException
from orchestrator.state import NexusState
from services.course_service import advance_module, get_or_create_module_progress, update_module_progress, get_course_progress
from services.generation_service import STATE_TTL
from storage.minio_handler import MinIOHandler

def _key(session_id: str) -> str:
    return f"state:{session_id}"

def _mod_to_dict(m: Module) -> dict:
    raw = m.concepts or []
    return {
        "id":            str(m.id),
        "title":         m.title,
        "concepts":      [c.get("name","") for c in raw],
        "code_examples": [{"title":c.get("name",""),"language":"code","code":c.get("code_example","")} for c in raw if c.get("code_example")],
        "learning_goals": m.learning_objectives or [],
        "difficulty":    m.difficulty.value,
        "estimated_hours": m.estimated_hours,
    }

async def _load_ec(db: AsyncSession, employee_id: str, course_id: str) -> EmployeeCourse:
    ec = await db.scalar(
        select(EmployeeCourse)
        .where(EmployeeCourse.employee_id==uuid.UUID(employee_id), EmployeeCourse.course_id==uuid.UUID(course_id))
        .options(joinedload(EmployeeCourse.course).selectinload(Course.modules))
    )
    if not ec:
        raise NotFoundException(f"No assignment: employee={employee_id} course={course_id}")
    if not ec.course.modules:
        raise AppException(detail="Course has no modules yet — manager must run course generation first.", status_code=409)
    return ec

async def _build_state(ec: EmployeeCourse, redis: Any, keep_history: dict | None = None) -> NexusState:
    mods = sorted(ec.course.modules, key=lambda m: m.order_index)
    idx  = min(ec.current_module_index, len(mods)-1)
    state: NexusState = {
        "session_id": ec.session_id,
        "user_id":    str(ec.employee_id),
        "mode":       ec.course.mode,
        "input_data": {},
        "skill_manifest": {},
        "course_plan": {
            "course_id":    str(ec.course_id),
            "title":        ec.course.title,
            "total_modules": len(mods),
            "modules":      [_mod_to_dict(m) for m in mods],
        },
        "current_module_index":     idx,
        "current_module":           _mod_to_dict(mods[idx]),
        "teaching_history":         [],
        "interview_history":        [],
        "interview_question_count": 0,
        "agents_status":            {},
        "passed":                   False,
        "consecutive_fails":        getattr(ec, "consecutive_fails", 0),
        "error":                    None,
    }
    if keep_history:
        state.update({k: keep_history[k] for k in ("teaching_history","interview_history","interview_question_count","agents_status") if k in keep_history})
    await redis.set(_key(ec.session_id), json.dumps(state), ex=STATE_TTL)
    return state

async def _get_state(ec: EmployeeCourse, redis: Any) -> NexusState:
    raw = await redis.get(_key(ec.session_id))
    if raw:
        return json.loads(raw)
    logger.info(f"[emp_svc] Rebuilding state for session={ec.session_id}")
    return await _build_state(ec, redis)

async def _save(state: NexusState, redis: Any) -> None:
    await redis.set(_key(state["session_id"]), json.dumps(state), ex=STATE_TTL)

# ── Public ─────────────────────────────────────────────────────────────────────

async def get_current_module(employee_id: str, course_id: str, db: AsyncSession, redis: Any) -> dict:
    ec = await _load_ec(db, employee_id, course_id)
    if not ec.session_id:
        ec.session_id = str(uuid.uuid4()); await db.commit()
    state = await _get_state(ec, redis)
    return {
        "session_id": state["session_id"],
        "current_module_index": state["current_module_index"],
        "current_module": state["current_module"],
        "total_modules": state["course_plan"].get("total_modules", 0),
        "course_title": state["course_plan"].get("title",""),
        "agents_status": state.get("agents_status",{}),
        "modules": state["course_plan"].get("modules", []),
    }

async def submit_teaching_message(employee_id: str, course_id: str, message: str, db: AsyncSession, redis: Any) -> dict:
    ec = await _load_ec(db, employee_id, course_id)
    if not ec.session_id:
        ec.session_id = str(uuid.uuid4()); await db.commit()
    state = await _get_state(ec, redis)
    state["input_data"] = {**state.get("input_data",{}), "user_message": message}
    new_state = await _teaching_agent(state)
    await _save(new_state, redis)
    history = new_state.get("teaching_history", [])
    last = next((m["content"] for m in reversed(history) if m["role"]=="assistant"), "")
    complete = "[TEACHING_COMPLETE]" in last
    return {
        "session_id": new_state["session_id"],
        "response": last.replace("[TEACHING_COMPLETE]","").strip(),
        "teaching_complete": complete,
        "agents_status": new_state.get("agents_status",{}),
    }

async def submit_task_file(employee_id: str, course_id: str, file_bytes: bytes, filename: str, db: AsyncSession, redis: Any, minio: Any) -> dict:
    ec = await _load_ec(db, employee_id, course_id)
    state = await _get_state(ec, redis)
    handler = MinIOHandler(minio)
    bucket  = "nexusiq-submissions"
    obj     = f"tasks/{ec.session_id}/{uuid.uuid4()}/{filename}"
    await handler.upload_file(bucket, obj, file_bytes, "text/plain")
    state["input_data"] = {**state.get("input_data",{}), "submission_object_name": obj, "submission_bucket": bucket, "submission_filename": filename}
    new_state = await _task_agent(state)
    await _save(new_state, redis)
    task_score = float(new_state.get("task_score", 0))
    mods = sorted(ec.course.modules, key=lambda m: m.order_index)
    prog = await get_or_create_module_progress(db, str(ec.id), str(mods[ec.current_module_index].id))
    await update_module_progress(db, str(prog.id), task_score=task_score)
    return {
        "session_id": new_state["session_id"],
        "task_score": task_score,
        "passed_task": task_score >= 60,
        "feedback": new_state.get("input_data",{}).get("task_feedback",""),
        "agents_status": new_state.get("agents_status",{}),
    }

async def submit_interview_message(employee_id: str, course_id: str, message: str | None, db: AsyncSession, redis: Any) -> dict:
    ec = await _load_ec(db, employee_id, course_id)
    state = await _get_state(ec, redis)
    state["input_data"] = {**state.get("input_data",{}), "user_message": message}
    new_state = await _interview_agent(state)
    await _save(new_state, redis)
    history  = new_state.get("interview_history",[])
    last_msg = history[-1]["content"] if history else ""
    done     = "[INTERVIEW_DONE]" in last_msg
    result   = {
        "session_id": new_state["session_id"],
        "question_count": new_state.get("interview_question_count",0),
        "response": last_msg.split("[INTERVIEW_DONE]")[0].strip() if done else last_msg,
        "interview_complete": done,
        "agents_status": new_state.get("agents_status",{}),
    }
    if done:
        interview_score = float(new_state.get("interview_score", 0))
        result["interview_score"] = interview_score
        mods = sorted(ec.course.modules, key=lambda m: m.order_index)
        prog = await get_or_create_module_progress(db, str(ec.id), str(mods[ec.current_module_index].id))
        await update_module_progress(db, str(prog.id), interview_score=interview_score)
        prog = await db.scalar(select(ModuleProgress).where(ModuleProgress.id==prog.id))
        passed, final_score = (prog.passed, prog.final_score) if prog else (False, 0.0)
        result.update({"final_score": final_score, "passed": passed})
        new_state["passed"] = passed
        new_state["consecutive_fails"] = 0 if passed else new_state.get("consecutive_fails",0)+1
        await _save(new_state, redis)
        if passed:
            adv = await advance_module(db, str(ec.id))
            if adv.status == EmployeeCourseStatus.completed:
                result["course_complete"] = True
            else:
                await _build_state(adv, redis)
                result["next_module_index"] = adv.current_module_index
    return result

async def get_tutor_plan(employee_id: str, course_id: str, db: AsyncSession, redis: Any) -> dict:
    ec = await _load_ec(db, employee_id, course_id)
    state = await _get_state(ec, redis)
    if state.get("passed"):
        raise AppException(detail="Module already passed — no tutor plan needed", status_code=409)
    new_state = await _tutor_agent_fn(state)
    await _build_state(ec, redis)   # reset history for retry attempt
    return {"session_id": new_state["session_id"], "tutor_plan": new_state.get("tutor_plan",{}), "agents_status": new_state.get("agents_status",{})}

async def get_progress(employee_id: str, course_id: str, db: AsyncSession) -> dict:
    ec = await db.scalar(select(EmployeeCourse).where(EmployeeCourse.employee_id==uuid.UUID(employee_id), EmployeeCourse.course_id==uuid.UUID(course_id)))
    if not ec:
        raise NotFoundException("Assignment not found")
    return await get_course_progress(db, str(ec.id))


async def get_assigned_courses(employee_id: str, db: AsyncSession) -> list[dict]:
    """Return all courses assigned to this employee with progress summary."""
    from services.course_service import get_employee_courses
    assignments = await get_employee_courses(db, employee_id)
    return [
        {
            "course_id":    str(ec.course_id),
            "title":        ec.course.title,
            "mode":         ec.course.mode,
            "status":       ec.status.value,
            "current_module_index": ec.current_module_index,
            "total_modules": len(ec.course.modules) if ec.course and ec.course.modules else 0,
        }
        for ec in assignments
    ]


async def get_or_generate_task(employee_id: str, course_id: str, db: AsyncSession, redis: Any) -> dict:
    """
    Returns the generated task for the current module.
    If not yet generated (first visit to evaluate page), calls task_sub_agent
    in generation mode (no submission file) to produce it, then caches in state.
    """
    ec = await _load_ec(db, employee_id, course_id)
    state = await _get_state(ec, redis)

    existing = state.get("input_data", {}).get("generated_task")
    if existing:
        return existing

    # Phase 1: generate task without submission
    new_state = await _task_agent(state)
    await _save(new_state, redis)

    task = new_state.get("input_data", {}).get("generated_task")
    if not task:
        raise AgentExecutionException("Task agent failed to generate a task")
    return task
