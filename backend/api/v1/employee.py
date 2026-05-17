"""
NexusIQ — Employee API Routes.

Fixes vs original:
  - get_current_module: added redis dependency (was missing → crash on every call)
  - InterviewAnswer.answer: made Optional (first call starts interview with no answer)
  - submit_interview_answer: passes None correctly on first call
"""

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from db.session import get_db
from db.redis_client import get_redis
from storage.minio_client import get_minio_client
from db.models import User
from middleware.auth_middleware import require_role
from services import employee_service

router = APIRouter(prefix="/employee", tags=["employee"])

_MAX_FILE_BYTES = 10 * 1024 * 1024  # 10 MB


class TeachMessage(BaseModel):
    message: str


class InterviewAnswer(BaseModel):
    # None on the first call — starts the interview and returns Q1.
    # Non-null on subsequent calls — scores the previous answer and returns next question.
    answer: str | None = None


@router.get("/courses")
async def get_assigned_courses(
    current_user: User = Depends(require_role("employee")),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """List all courses assigned to the authenticated employee."""
    return await employee_service.get_assigned_courses(str(current_user.id), db)


@router.get("/courses/{course_id}/module")
async def get_current_module(
    course_id: str,
    current_user: User = Depends(require_role("employee")),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),          # FIX: was missing → crash on every call
) -> dict:
    """Return the employee's current module and full session state."""
    return await employee_service.get_current_module(
        str(current_user.id), course_id, db, redis
    )


@router.post("/courses/{course_id}/teach")
async def submit_teaching_message(
    course_id: str,
    data: TeachMessage,
    current_user: User = Depends(require_role("employee")),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> dict:
    """Send a message to the teaching agent and receive the next tutoring response."""
    return await employee_service.submit_teaching_message(
        str(current_user.id), course_id, data.message, db, redis
    )


@router.post("/courses/{course_id}/task/submit")
async def submit_task_file(
    course_id: str,
    file: UploadFile = File(...),
    current_user: User = Depends(require_role("employee")),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
    minio=Depends(get_minio_client),
) -> dict:
    """Upload task submission file for evaluation (max 10 MB)."""
    file_bytes = await file.read()
    if len(file_bytes) > _MAX_FILE_BYTES:
        raise HTTPException(status_code=413, detail="File too large. Maximum size is 10 MB.")
    return await employee_service.submit_task_file(
        str(current_user.id), course_id, file_bytes, file.filename or "submission.bin", db, redis, minio
    )


@router.post("/courses/{course_id}/interview")
async def submit_interview_answer(
    course_id: str,
    data: InterviewAnswer,
    current_user: User = Depends(require_role("employee")),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> dict:
    """
    Drive the 9-question interview loop.
    Call with answer=null to start (receive Q1).
    Call with answer=<string> to score previous answer and receive next question.
    Call 9 times total to complete evaluation.
    """
    return await employee_service.submit_interview_message(
        str(current_user.id), course_id, data.answer, db, redis
    )




@router.get("/courses/{course_id}/task")
async def get_task(
    course_id: str,
    current_user: User = Depends(require_role("employee")),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> dict:
    """Generate and return the evaluation task for the current module."""
    return await employee_service.get_or_generate_task(
        str(current_user.id), course_id, db, redis
    )

@router.get("/courses/{course_id}/progress")
async def get_progress(
    course_id: str,
    current_user: User = Depends(require_role("employee")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return full module progress breakdown for this course."""
    return await employee_service.get_progress(str(current_user.id), course_id, db)


@router.get("/courses/{course_id}/tutor")
async def get_tutor_plan(
    course_id: str,
    current_user: User = Depends(require_role("employee")),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> dict:
    """Fetch AI-generated revision plan after a failed module evaluation."""
    return await employee_service.get_tutor_plan(
        str(current_user.id), course_id, db, redis
    )
