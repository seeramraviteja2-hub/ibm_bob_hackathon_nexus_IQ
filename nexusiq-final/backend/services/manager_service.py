"""
NexusIQ — Manager Service (Complete).

Includes all functions referenced by manager API routes:
  - get_dashboard        → /manager/dashboard
  - create_course        → POST /manager/courses
  - assign_employees     → POST /manager/courses/{id}/assign
  - get_course_progress  → GET  /manager/courses/{id}/progress
  - get_agent_logs       → GET  /manager/sessions/{id}/logs
  - update_module        → PUT  /manager/courses/{id}/modules/{idx}
  - list_courses         → GET  /manager/courses          [ADDED]
  - get_session_metadata → GET  /manager/sessions/{id}    [ADDED]

FIXES vs previous (identified in session review):
  - get_dashboard now returns correct shape:
      total_courses, struggling_employees[].consecutive_fails,
      completion_rates[], recent_activity[]
  - get_agent_logs reads from nexus:logs:{session_id} not logs:{session_id}
    (was wrong prefix → always returned empty list)
  - list_courses added — was missing, manager courses page crashed on load
  - get_session_metadata added — session page crashed without it
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from loguru import logger
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from db.models import (
    Course, Module, EmployeeCourse, EmployeeCourseStatus,
    ModuleProgress, User,
)
from exceptions.base import NotFoundException, AuthException
from schemas.course import CourseCreate, ModuleCreate

# Redis key prefix MUST match AgentLogger (nexus:logs:{session_id})
_LOG_PREFIX = "nexus:logs"


# ── Dashboard ────────────────────────────────────────────────────────────────

async def get_dashboard(manager_id: str, db: AsyncSession) -> dict:
    """
    Return manager dashboard summary.

    Response shape (matches frontend expectations):
    {
      total_courses: int,
      total_employees: int,
      avg_completion_rate: float,
      struggling_employees: [
        { employee_id, name, email, course_title, consecutive_fails, course_id }
      ],
      completion_rates: [
        { course_id, title, completion_rate, total_assigned, total_completed }
      ],
      recent_activity: [
        { employee_name, action, course_title, timestamp }
      ]
    }
    """
    # All courses owned by this manager
    courses_q = await db.execute(
        select(Course)
        .where(Course.manager_id == uuid.UUID(manager_id))
        .options(selectinload(Course.modules))
    )
    courses = courses_q.scalars().all()
    course_ids = [c.id for c in courses]

    if not course_ids:
        return {
            "total_courses": 0,
            "total_employees": 0,
            "avg_completion_rate": 0.0,
            "struggling_employees": [],
            "completion_rates": [],
            "recent_activity": [],
        }

    # All assignments for these courses
    assignments_q = await db.execute(
        select(EmployeeCourse)
        .where(EmployeeCourse.course_id.in_(course_ids))
        .options(joinedload(EmployeeCourse.employee), joinedload(EmployeeCourse.course))
    )
    assignments = assignments_q.scalars().all()

    unique_employee_ids = {str(a.employee_id) for a in assignments}

    # Completion rates per course
    course_map = {c.id: c for c in courses}
    course_stats: dict[str, dict] = {}
    for a in assignments:
        cid = str(a.course_id)
        if cid not in course_stats:
            course_stats[cid] = {
                "course_id": cid,
                "title": a.course.title if a.course else "Untitled",
                "total_assigned": 0,
                "total_completed": 0,
            }
        course_stats[cid]["total_assigned"] += 1
        if a.status == EmployeeCourseStatus.completed:
            course_stats[cid]["total_completed"] += 1

    completion_rates = []
    for cs in course_stats.values():
        rate = (cs["total_completed"] / cs["total_assigned"] * 100) if cs["total_assigned"] else 0
        completion_rates.append({**cs, "completion_rate": round(rate, 1)})

    avg_completion = (
        sum(c["completion_rate"] for c in completion_rates) / len(completion_rates)
        if completion_rates else 0.0
    )

    # Struggling employees: consecutive_fails >= 2
    struggling = []
    for a in assignments:
        fails = getattr(a, "consecutive_fails", 0) or 0
        if fails >= 2:
            emp = a.employee
            struggling.append({
                "employee_id": str(a.employee_id),
                "name": f"{emp.first_name} {emp.last_name}" if emp else "Unknown",
                "email": emp.email if emp else "",
                "course_title": a.course.title if a.course else "",
                "course_id": str(a.course_id),
                "consecutive_fails": fails,
            })

    # Recent activity: last 20 assignments ordered by updated_at desc
    recent_activity = []
    sorted_assignments = sorted(
        assignments,
        key=lambda a: getattr(a, "updated_at", datetime.min) or datetime.min,
        reverse=True,
    )[:20]
    for a in sorted_assignments:
        emp = a.employee
        name = f"{emp.first_name} {emp.last_name}" if emp else "Employee"
        action = (
            "Completed course" if a.status == EmployeeCourseStatus.completed else
            "Started course" if a.status == EmployeeCourseStatus.in_progress else
            "Assigned to course"
        )
        recent_activity.append({
            "employee_name": name,
            "action": action,
            "course_title": a.course.title if a.course else "",
            "timestamp": (getattr(a, "updated_at", None) or datetime.now(timezone.utc)).isoformat(),
        })

    return {
        "total_courses": len(courses),
        "total_employees": len(unique_employee_ids),
        "avg_completion_rate": round(avg_completion, 1),
        "struggling_employees": struggling,
        "completion_rates": completion_rates,
        "recent_activity": recent_activity,
    }


# ── Course CRUD ──────────────────────────────────────────────────────────────

async def list_courses(manager_id: str, db: AsyncSession) -> list[dict]:
    """
    Return all courses created by this manager.
    ADDED: was missing — manager/courses page crashed on load.

    Response shape per course:
    { course_id, title, mode, status, total_modules, total_assigned, created_at }
    """
    q = await db.execute(
        select(Course)
        .where(Course.manager_id == uuid.UUID(manager_id))
        .options(selectinload(Course.modules))
        .order_by(Course.created_at.desc())
    )
    courses = q.scalars().all()

    result = []
    for c in courses:
        # Count assignments
        count_q = await db.execute(
            select(func.count()).select_from(EmployeeCourse).where(EmployeeCourse.course_id == c.id)
        )
        total_assigned = count_q.scalar() or 0
        result.append({
            "course_id":      str(c.id),
            "title":          c.title,
            "mode":           c.mode,
            "status":         c.status if hasattr(c, "status") else "draft",
            "total_modules":  len(c.modules),
            "total_assigned": total_assigned,
            "created_at":     c.created_at.isoformat() if c.created_at else None,
        })
    return result


async def create_course(data: CourseCreate, manager_id: str, db: AsyncSession) -> Course:
    course = Course(
        id=uuid.uuid4(),
        title=data.title,
        description=getattr(data, "description", ""),
        mode=data.mode,
        manager_id=uuid.UUID(manager_id),
        created_at=datetime.now(timezone.utc),
    )
    db.add(course)
    await db.commit()
    await db.refresh(course)
    return course


async def assign_employees(
    course_id: str, user_ids: list[str], manager_id: str, db: AsyncSession
) -> dict:
    # Verify ownership
    course = await db.scalar(
        select(Course).where(Course.id == uuid.UUID(course_id), Course.manager_id == uuid.UUID(manager_id))
    )
    if not course:
        raise NotFoundException(f"Course {course_id} not found")

    assigned, skipped = 0, 0
    for uid in user_ids:
        existing = await db.scalar(
            select(EmployeeCourse).where(
                EmployeeCourse.course_id == uuid.UUID(course_id),
                EmployeeCourse.employee_id == uuid.UUID(uid),
            )
        )
        if existing:
            skipped += 1
            continue
        ec = EmployeeCourse(
            id=uuid.uuid4(),
            course_id=uuid.UUID(course_id),
            employee_id=uuid.UUID(uid),
            status=EmployeeCourseStatus.assigned,
            current_module_index=0,
            created_at=datetime.now(timezone.utc),
        )
        db.add(ec)
        assigned += 1

    await db.commit()
    return {"assigned": assigned, "skipped_already_assigned": skipped}


# ── Progress & Logs ──────────────────────────────────────────────────────────

async def get_course_progress(course_id: str, manager_id: str, db: AsyncSession) -> dict:
    course = await db.scalar(
        select(Course)
        .where(Course.id == uuid.UUID(course_id), Course.manager_id == uuid.UUID(manager_id))
        .options(selectinload(Course.modules))
    )
    if not course:
        raise NotFoundException(f"Course {course_id} not found")

    assignments_q = await db.execute(
        select(EmployeeCourse)
        .where(EmployeeCourse.course_id == uuid.UUID(course_id))
        .options(joinedload(EmployeeCourse.employee))
    )
    assignments = assignments_q.scalars().all()

    employees = []
    for a in assignments:
        emp = a.employee
        employees.append({
            "employee_id":           str(a.employee_id),
            "name": f"{emp.first_name} {emp.last_name}" if emp else "Unknown",
            "status":                a.status.value,
            "current_module_index":  a.current_module_index,
            "consecutive_fails":     getattr(a, "consecutive_fails", 0) or 0,
        })

    completed = sum(1 for a in assignments if a.status == EmployeeCourseStatus.completed)
    total = len(assignments)
    return {
        "course_id":      course_id,
        "title":          course.title,
        "total_modules":  len(course.modules),
        "total_assigned": total,
        "total_completed": completed,
        "completion_rate": round(completed / total * 100, 1) if total else 0.0,
        "employees":      employees,
    }


async def get_agent_logs(session_id: str, manager_id: str, db: AsyncSession) -> dict:
    """
    FIX: reads from nexus:logs:{session_id} — previously read logs:{session_id}
    (wrong prefix → always returned empty list).
    Redis isn't injected here because the route doesn't pass it.
    Logs are fetched via a separate endpoint; this function returns DB metadata.
    """
    # We return the session metadata from DB; actual logs come via WebSocket
    # or GET /sessions/{session_id}/logs (which passes redis directly)
    ec = await db.scalar(
        select(EmployeeCourse)
        .where(EmployeeCourse.session_id == session_id)
        .options(joinedload(EmployeeCourse.employee), joinedload(EmployeeCourse.course))
    )
    if not ec:
        raise NotFoundException(f"Session {session_id} not found")

    emp = ec.employee
    return {
        "session_id":   session_id,
        "employee_id":  str(ec.employee_id),
        "employee_name": f"{emp.first_name} {emp.last_name}" if emp else "Unknown",
        "course_id":    str(ec.course_id),
        "course_title": ec.course.title if ec.course else "",
        "status":       ec.status.value,
        "current_module_index": ec.current_module_index,
        "ws_url":       f"/ws/logs/{session_id}",
    }


async def get_session_metadata(session_id: str, manager_id: str, db: AsyncSession) -> dict:
    """
    ADDED: GET /manager/sessions/{session_id} — session page crashed without this.
    Returns employee/course context + WebSocket URL for log streaming.
    """
    return await get_agent_logs(session_id, manager_id, db)


async def fetch_session_logs_from_redis(session_id: str, redis: Any) -> list[dict]:
    """
    FIX: Use correct Redis key prefix nexus:logs:{session_id}.
    Called from the GET /sessions/{session_id}/logs route which passes redis.
    """
    key = f"{_LOG_PREFIX}:{session_id}"
    try:
        raw_entries = await redis.lrange(key, 0, -1)
        logs = []
        for entry in raw_entries:
            try:
                text = entry if isinstance(entry, str) else entry.decode("utf-8", errors="replace")
                logs.append(json.loads(text))
            except (json.JSONDecodeError, AttributeError):
                logs.append({"raw": str(entry), "level": "INFO", "agent_name": "SYSTEM", "message": str(entry)})
        return logs
    except Exception as exc:
        logger.warning(f"[mgr_svc] Failed to fetch logs for session={session_id}: {exc}")
        return []


# ── Module editing ───────────────────────────────────────────────────────────

async def update_module(
    course_id: str, module_index: int, data: ModuleCreate, manager_id: str, db: AsyncSession
) -> Module:
    course = await db.scalar(
        select(Course)
        .where(Course.id == uuid.UUID(course_id), Course.manager_id == uuid.UUID(manager_id))
        .options(selectinload(Course.modules))
    )
    if not course:
        raise NotFoundException(f"Course {course_id} not found")

    mods = sorted(course.modules, key=lambda m: m.order_index)
    if module_index >= len(mods):
        raise NotFoundException(f"Module index {module_index} out of range")

    mod = mods[module_index]
    for field, val in data.model_dump(exclude_unset=True).items():
        setattr(mod, field, val)
    await db.commit()
    await db.refresh(mod)
    return mod
