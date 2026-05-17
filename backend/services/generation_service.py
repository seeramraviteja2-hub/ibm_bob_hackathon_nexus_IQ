"""
NexusIQ — Course Generation Service.
Runs requirement_agent → [rag_agent] → course_gen_agent as a BackgroundTask.
"""

import json
import uuid
from typing import Any

from fastapi import BackgroundTasks, UploadFile
from loguru import logger
from sqlalchemy import select, delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Course, Module, CourseStatus, DifficultyLevel
from db.session import async_session_factory
from exceptions.base import AppException
from orchestrator.graph import generation_graph
from orchestrator.state import NexusState
from storage.minio_handler import MinIOHandler
from demo.demo_cache import DEMO_MODE, DEMO_COURSE_PLAN, DEMO_SKILL_MANIFEST

_GEN_TTL   = 86_400
STATE_TTL  = 86_400 * 7   # export so employee_service can import


def _status_key(course_id: str) -> str:
    return f"generation:status:{course_id}"


def _map_module(m: dict, difficulty: str, course_uuid: uuid.UUID) -> Module:
    concepts_raw: list = m.get("concepts", [])
    code_examples: list = m.get("code_examples", [])

    structured = []
    for i, name in enumerate(concepts_raw):
        ex = code_examples[i] if i < len(code_examples) else {}
        structured.append({
            "name": str(name),
            "explanation": "",
            "code_example": ex.get("code", "") if isinstance(ex, dict) else "",
            "common_mistakes": [],
        })
    if len(code_examples) > len(concepts_raw) and structured:
        structured[-1]["extra_examples"] = code_examples[len(concepts_raw):]

    try:
        diff = DifficultyLevel(difficulty.lower())
    except ValueError:
        diff = DifficultyLevel.intermediate

    return Module(
        course_id=course_uuid,
        title=m.get("title", f"Module {m.get('index', 0) + 1}"),
        order_index=int(m.get("index", 0)),
        difficulty=diff,
        concepts=structured,
        learning_objectives=m.get("learning_goals", []),
        estimated_hours=round(int(m.get("estimated_minutes", 60)) / 60.0, 2),
        why_this_matters=None,
    )


async def _run_pipeline(course_id: str, state: NexusState, difficulty: str) -> None:
    """BackgroundTask — all exceptions caught, never re-raised."""
    redis = None
    try:
        from db.redis_client import get_redis
        redis = await get_redis()

        async def _set(status: str, detail: str = "") -> None:
            await redis.set(
                _status_key(course_id),
                json.dumps({"status": status, "detail": detail}),
                ex=_GEN_TTL,
            )

        await _set("running")
        logger.info(f"[gen] Pipeline started course={course_id}")

        # Short-circuit with cached demo data — zero LLM calls, zero rate-limit risk
        if DEMO_MODE:
            modules_raw = DEMO_COURSE_PLAN.get("modules", [])
            async with async_session_factory() as db:
                course = await db.scalar(select(Course).where(Course.id == uuid.UUID(course_id)))
                if course:
                    await db.execute(sa_delete(Module).where(Module.course_id == uuid.UUID(course_id)))
                    for m in modules_raw:
                        db.add(_map_module(m, difficulty, uuid.UUID(course_id)))
                    course.status = CourseStatus.active
                    await db.commit()
            await _set("complete", f"{len(modules_raw)} demo modules generated")
            return


        final: NexusState = await generation_graph.ainvoke(state)

        if final.get("error"):
            await _set("failed", final["error"])
            return

        modules_raw = final.get("course_plan", {}).get("modules", [])
        if not modules_raw:
            await _set("failed", "course_gen_agent returned 0 modules")
            return

        async with async_session_factory() as db:
            course = await db.scalar(select(Course).where(Course.id == uuid.UUID(course_id)))
            if not course:
                await _set("failed", "Course not found in DB after pipeline")
                return

            await db.execute(sa_delete(Module).where(Module.course_id == uuid.UUID(course_id)))
            for m in modules_raw:
                db.add(_map_module(m, difficulty, uuid.UUID(course_id)))

            plan_title = final.get("course_plan", {}).get("title")
            if plan_title:
                course.title = plan_title
            course.status = CourseStatus.active
            await db.commit()

        logger.info(f"[gen] Course {course_id} active — {len(modules_raw)} modules")
        await _set("complete", f"{len(modules_raw)} modules generated")

    except Exception as exc:
        logger.exception(f"[gen] Unhandled error course={course_id}: {exc}")
        if redis:
            try:
                await redis.set(
                    _status_key(course_id),
                    json.dumps({"status": "failed", "detail": str(exc)}),
                    ex=_GEN_TTL,
                )
            except Exception:
                pass


async def start_course_generation(
    course_id: str,
    manager_id: str,
    files: list[UploadFile],
    db: AsyncSession,
    redis: Any,
    minio: Any,
    background_tasks: BackgroundTasks,
    github_url: str | None = None,
) -> str:
    course = await db.scalar(
        select(Course).where(
            Course.id == uuid.UUID(course_id),
            Course.manager_id == uuid.UUID(manager_id),
        )
    )
    if not course:
        raise AppException(detail="Course not found or access denied", status_code=404)

    # Must have either files or a github_url
    if not files and not github_url:
        raise AppException(detail="Provide at least one file or a GitHub repository URL.", status_code=400)

    handler  = MinIOHandler(minio)
    bucket   = "nexusiq-uploads"
    mode     = course.mode
    job_id   = str(uuid.uuid4())

    # ── GitHub URL path ──────────────────────────────────────────────────
    if github_url and not files:
        # Both modes support GitHub — treat it as legacy_codebase crawl
        # requirement_agent will detect github_url in input_data and crawl the repo
        input_data = {
            "github_url": github_url.strip(),
            "mode": "github",
        }
        # Override mode to legacy_codebase so the graph uses rag_agent
        mode = "legacy_codebase"

    elif mode == "new_project":
        if len(files) != 1:
            raise AppException(detail="new_project requires exactly 1 spec file (PDF/DOCX/TXT)", status_code=400)
        f = files[0]
        fname = f.filename or "upload.bin"
        if fname.rsplit(".", 1)[-1].lower() not in ("pdf", "docx", "doc", "txt"):
            raise AppException(detail=f"Unsupported file type: {fname}", status_code=400)
        obj = f"specs/{course_id}/{job_id}/{fname}"
        await handler.upload_file(bucket, obj, await f.read(), f.content_type or "application/octet-stream")
        input_data = {"object_name": obj, "bucket": bucket, "filename": fname}

    else:
        allowed = {"py","js","ts","jsx","tsx","java","go","rs","cpp","c","cs","rb","php","kt","swift",
                   "vue","html","css","json","yaml","yml","toml","sh","sql","md","txt"}
        file_paths = []
        for f in files:
            fname = f.filename or "upload.bin"
            ext = fname.rsplit(".", 1)[-1].lower()
            if ext not in allowed:
                raise AppException(detail=f"Unsupported code file: .{ext}", status_code=400)
            obj = f"code/{course_id}/{job_id}/{fname}"
            await handler.upload_file(bucket, obj, await f.read(), "text/plain")
            file_paths.append({"bucket": bucket, "object_name": obj, "file_path": fname})
        input_data = {"file_paths": file_paths}

    difficulty = "intermediate"
    if isinstance(course.tech_stack, dict):
        difficulty = course.tech_stack.get("difficulty", "intermediate")

    session_id = f"gen-{course_id}-{job_id}"
    initial_state: NexusState = {
        "session_id": session_id,
        "user_id":    manager_id,
        "mode":       mode,
        "input_data": input_data,
        "skill_manifest": {},
        "course_plan":    {},
        "agents_status":  {},
        "error":          None,
    }

    await redis.set(
        _status_key(course_id),
        json.dumps({"status": "queued", "detail": "Pipeline enqueued"}),
        ex=_GEN_TTL,
    )
    background_tasks.add_task(_run_pipeline, course_id, initial_state, difficulty)
    logger.info(f"[gen] Enqueued course={course_id} job={job_id}")
    return job_id


async def get_generation_status(course_id: str, redis: Any) -> dict:
    raw = await redis.get(_status_key(course_id))
    if not raw:
        return {"status": "not_started", "detail": "No generation job found"}
    return json.loads(raw)
