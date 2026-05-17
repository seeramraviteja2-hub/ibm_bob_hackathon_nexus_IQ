"""NexusIQ — Manager API Routes (Complete).

ADDED vs previous version:
  - GET /manager/courses          → list_courses (was missing → courses page crashed)
  - GET /manager/sessions/{id}    → get_session_metadata (was missing → session page crashed)
  - GET /manager/sessions/{id}/logs now passes redis → reads correct nexus:logs: prefix
"""
from fastapi import APIRouter, Depends, UploadFile, File, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from db.session import get_db
from db.redis_client import get_redis
from storage.minio_client import get_minio_client
from db.models import User
from middleware.auth_middleware import require_role
from schemas.course import CourseCreate, CourseResponse, ModuleCreate, ModuleResponse
from services import manager_service
from services.generation_service import start_course_generation, get_generation_status

router = APIRouter(prefix="/manager", tags=["manager"])


class AssignRequest(BaseModel):
    user_ids: list[str]


@router.get("/dashboard")
async def dashboard(
    current_user: User = Depends(require_role("manager")),
    db: AsyncSession = Depends(get_db),
):
    return await manager_service.get_dashboard(str(current_user.id), db)


# ADDED: was missing — manager/courses page crashed on first load
@router.get("/courses")
async def list_courses(
    current_user: User = Depends(require_role("manager")),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """List all courses created by this manager."""
    return await manager_service.list_courses(str(current_user.id), db)


@router.post("/courses", response_model=CourseResponse)
async def create_course(
    data: CourseCreate,
    current_user: User = Depends(require_role("manager")),
    db: AsyncSession = Depends(get_db),
):
    course = await manager_service.create_course(data, str(current_user.id), db)
    return CourseResponse(
        id=course.id,
        title=course.title,
        description=course.description,
        mode=course.mode,
        status=course.status.value,
        manager_id=course.manager_id,
        total_modules=0,
    )


@router.post("/courses/{course_id}/assign")
async def assign(
    course_id: str,
    data: AssignRequest,
    current_user: User = Depends(require_role("manager")),
    db: AsyncSession = Depends(get_db),
):
    return await manager_service.assign_employees(course_id, data.user_ids, str(current_user.id), db)


@router.post("/courses/{course_id}/generate")
async def generate(
    course_id: str,
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
    current_user: User = Depends(require_role("manager")),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
    minio=Depends(get_minio_client),
):
    """
    Triggers AI pipeline: requirement_agent → [rag_agent] → course_gen_agent.
    Returns immediately. Poll /generate/status for completion.
    """
    job_id = await start_course_generation(
        course_id, str(current_user.id), files, db, redis, minio, background_tasks
    )
    return {"job_id": job_id, "status_url": f"/api/v1/manager/courses/{course_id}/generate/status"}


@router.get("/courses/{course_id}/generate/status")
async def gen_status(
    course_id: str,
    current_user: User = Depends(require_role("manager")),
    redis=Depends(get_redis),
):
    return await get_generation_status(course_id, redis)


@router.get("/courses/{course_id}/progress")
async def course_progress(
    course_id: str,
    current_user: User = Depends(require_role("manager")),
    db: AsyncSession = Depends(get_db),
):
    return await manager_service.get_course_progress(course_id, str(current_user.id), db)


# ADDED: was missing — session detail page crashed without metadata
@router.get("/sessions/{session_id}")
async def get_session(
    session_id: str,
    current_user: User = Depends(require_role("manager")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return session metadata + WebSocket URL for real-time log streaming."""
    return await manager_service.get_session_metadata(session_id, str(current_user.id), db)


@router.get("/sessions/{session_id}/logs")
async def agent_logs(
    session_id: str,
    current_user: User = Depends(require_role("manager")),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> dict:
    """
    Return historical log entries for a session.
    FIX: redis now injected so correct key prefix nexus:logs:{session_id} is used.
    """
    metadata = await manager_service.get_session_metadata(session_id, str(current_user.id), db)
    logs = await manager_service.fetch_session_logs_from_redis(session_id, redis)
    return {**metadata, "logs": logs}


@router.put("/courses/{course_id}/modules/{module_index}", response_model=ModuleResponse)
async def update_module(
    course_id: str,
    module_index: int,
    data: ModuleCreate,
    current_user: User = Depends(require_role("manager")),
    db: AsyncSession = Depends(get_db),
):
    return await manager_service.update_module(course_id, module_index, data, str(current_user.id), db)
