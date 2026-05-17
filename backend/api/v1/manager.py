"""NexusIQ — Manager API Routes (Updated with Deletion)."""
from fastapi import APIRouter, Depends, UploadFile, File, Form, BackgroundTasks, HTTPException
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

class AssignSingleRequest(BaseModel):
    employee_id: str


@router.get("/dashboard")
async def dashboard(
    current_user: User = Depends(require_role("manager")),
    db: AsyncSession = Depends(get_db),
):
    return await manager_service.get_dashboard(str(current_user.id), db)


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


@router.get("/employees")
async def list_employees(
    current_user: User = Depends(require_role("manager")),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """List all employee users."""
    return await manager_service.list_employees(db)


@router.post("/courses/{course_id}/assign")
async def assign(
    course_id: str,
    data: AssignSingleRequest,
    current_user: User = Depends(require_role("manager")),
    db: AsyncSession = Depends(get_db),
):
    return await manager_service.assign_employees(course_id, [data.employee_id], str(current_user.id), db)


@router.post("/courses/{course_id}/unassign")
async def unassign(
    course_id: str,
    data: AssignSingleRequest,
    current_user: User = Depends(require_role("manager")),
    db: AsyncSession = Depends(get_db),
):
    return await manager_service.unassign_employee(course_id, data.employee_id, str(current_user.id), db)


@router.get("/courses/{course_id}/assigned")
async def get_assigned(
    course_id: str,
    current_user: User = Depends(require_role("manager")),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """List employees assigned to a course."""
    return await manager_service.get_assigned_employees(course_id, str(current_user.id), db)


@router.get("/courses/{course_id}")
async def get_course(
    course_id: str,
    current_user: User = Depends(require_role("manager")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    return await manager_service.get_course_detail(course_id, str(current_user.id), db)


# NEW: Course Deletion Route
@router.delete("/courses/{course_id}")
async def delete_course(
    course_id: str,
    current_user: User = Depends(require_role("manager")),
    db: AsyncSession = Depends(get_db),
):
    """Permanently delete a course and its associated modules/data."""
    success = await manager_service.delete_course(course_id, str(current_user.id), db)
    if not success:
        raise HTTPException(status_code=404, detail="Course not found or unauthorized")
    return {"status": "success", "message": "Course deleted successfully"}


@router.get("/courses/{course_id}/generate/logs")
async def gen_logs(
    course_id: str,
    current_user: User = Depends(require_role("manager")),
    redis=Depends(get_redis),
) -> dict:
    import json
    key = f"nexus:logs:{course_id}"
    raw = await redis.lrange(key, 0, -1)
    logs = []
    for r in raw:
        try:
            logs.append(json.loads(r))
        except Exception:
            logs.append({"message": str(r), "agent": "agent", "provider": "IBM Bob"})
    return {"logs": logs}


@router.post("/courses/{course_id}/generate")
async def generate(
    course_id: str,
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(default=[]),
    github_url: str | None = Form(default=None),
    current_user: User = Depends(require_role("manager")),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
    minio=Depends(get_minio_client),
):
    job_id = await start_course_generation(
        course_id, str(current_user.id), files, db, redis, minio, background_tasks,
        github_url=github_url,
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


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: str,
    current_user: User = Depends(require_role("manager")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    return await manager_service.get_session_metadata(session_id, str(current_user.id), db)


@router.get("/sessions/{session_id}/logs")
async def agent_logs(
    session_id: str,
    current_user: User = Depends(require_role("manager")),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> dict:
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
