"""
NexusIQ — Course service helpers shared by employee_service.
Handles module advancement and progress tracking.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from db.models import (
    Course, EmployeeCourse, EmployeeCourseStatus,
    Module, ModuleProgress,
)
from exceptions.base import NotFoundException


# ── Module progress ───────────────────────────────────────────────────────────

async def get_or_create_module_progress(
    db: AsyncSession,
    enrollment_id: str,
    module_id: str,
) -> ModuleProgress:
    prog = await db.scalar(
        select(ModuleProgress).where(
            ModuleProgress.enrollment_id == uuid.UUID(enrollment_id),
            ModuleProgress.module_id    == uuid.UUID(module_id),
        )
    )
    if not prog:
        prog = ModuleProgress(
            id=uuid.uuid4(),
            enrollment_id=uuid.UUID(enrollment_id),
            module_id=uuid.UUID(module_id),
            attempts=0,
        )
        db.add(prog)
        await db.flush()
    return prog


async def update_module_progress(
    db: AsyncSession,
    progress_id: str,
    task_score: float | None = None,
    interview_score: float | None = None,
) -> ModuleProgress:
    prog = await db.scalar(
        select(ModuleProgress).where(ModuleProgress.id == uuid.UUID(progress_id))
    )
    if not prog:
        raise NotFoundException(f"ModuleProgress {progress_id} not found")

    if task_score is not None:
        prog.task_score = task_score
    if interview_score is not None:
        prog.interview_score = interview_score

    # Recompute final score and passed status
    t = prog.task_score or 0.0
    i = prog.interview_score or 0.0

    if prog.task_score is not None and prog.interview_score is not None:
        prog.final_score = round(t * 0.4 + i * 0.6, 2)
        prog.passed = prog.final_score >= 60.0
        if prog.passed:
            prog.completed_at = datetime.now(timezone.utc)

    prog.attempts = (prog.attempts or 0) + 1
    prog.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(prog)
    return prog


# ── Module advancement ────────────────────────────────────────────────────────

async def advance_module(db: AsyncSession, enrollment_id: str) -> EmployeeCourse:
    """
    Advance the employee to the next module.
    If already on the last module, marks the course as completed.
    Returns the updated EmployeeCourse.
    """
    ec = await db.scalar(
        select(EmployeeCourse)
        .where(EmployeeCourse.id == uuid.UUID(enrollment_id))
        .options(joinedload(EmployeeCourse.course).selectinload(Course.modules))
    )
    if not ec:
        raise NotFoundException(f"Enrollment {enrollment_id} not found")

    modules = sorted(ec.course.modules, key=lambda m: m.order_index)
    next_idx = ec.current_module_index + 1

    if next_idx >= len(modules):
        ec.status = EmployeeCourseStatus.completed
    else:
        ec.current_module_index = next_idx
        ec.status = EmployeeCourseStatus.in_progress

    ec.consecutive_fails = 0
    ec.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(ec)
    return ec


# ── Progress queries ──────────────────────────────────────────────────────────

async def get_course_progress(db: AsyncSession, enrollment_id: str) -> dict:
    """Return per-module progress breakdown for a single enrollment."""
    ec = await db.scalar(
        select(EmployeeCourse)
        .where(EmployeeCourse.id == uuid.UUID(enrollment_id))
        .options(
            joinedload(EmployeeCourse.course).selectinload(Course.modules),
            selectinload(EmployeeCourse.module_progress),
        )
    )
    if not ec:
        raise NotFoundException(f"Enrollment {enrollment_id} not found")

    modules = sorted(ec.course.modules, key=lambda m: m.order_index)
    prog_map = {str(p.module_id): p for p in ec.module_progress}

    module_rows = []
    for mod in modules:
        p = prog_map.get(str(mod.id))
        module_rows.append({
            "module_id":    str(mod.id),
            "title":        mod.title,
            "order_index":  mod.order_index,
            "task_score":   p.task_score if p else None,
            "interview_score": p.interview_score if p else None,
            "final_score":  p.final_score if p else None,
            "passed":       p.passed if p else False,
            "attempts":     p.attempts if p else 0,
        })

    return {
        "enrollment_id": enrollment_id,
        "status":        ec.status.value,
        "current_module_index": ec.current_module_index,
        "module_progresses": module_rows,
    }


async def get_employee_courses(db: AsyncSession, employee_id: str) -> list[EmployeeCourse]:
    """Return all EmployeeCourse rows for an employee, with course+modules loaded."""
    result = await db.execute(
        select(EmployeeCourse)
        .where(EmployeeCourse.employee_id == uuid.UUID(employee_id))
        .options(joinedload(EmployeeCourse.course).selectinload(Course.modules))
    )
    return result.scalars().all()
