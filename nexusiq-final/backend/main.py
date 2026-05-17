"""
NexusIQ — FastAPI application entry point.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from core.config import settings
from db.session import create_all_tables
from db.redis_client import close_redis
from db.qdrant_client import close_qdrant
from exceptions.base import register_exception_handlers

from api.v1.auth     import router as auth_router
from api.v1.employee import router as employee_router
from api.v1.manager  import router as manager_router
from api.v1.ws       import router as ws_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ───────────────────────────────────────────────────────────
    logger.info("NexusIQ starting up...")
    await create_all_tables()
    logger.info("Database tables ready")
    yield
    # ── Shutdown ──────────────────────────────────────────────────────────
    await close_redis()
    await close_qdrant()
    logger.info("NexusIQ shutdown complete")


app = FastAPI(
    title="NexusIQ",
    description="AI-powered corporate training platform with IBM Bob",
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Exception handlers ────────────────────────────────────────────────────────
register_exception_handlers(app)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth_router,     prefix="/api/v1")
app.include_router(employee_router, prefix="/api/v1")
app.include_router(manager_router,  prefix="/api/v1")
app.include_router(ws_router)


@app.get("/health")
async def health():
    return {"status": "ok", "demo_mode": settings.DEMO_MODE}
