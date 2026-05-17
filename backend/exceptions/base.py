"""
NexusIQ — Custom exception hierarchy and FastAPI exception handlers.

Design: every domain-specific exception extends AppException so the
base handler always catches anything that slips through a specific handler.
All handlers return a consistent { error, type } JSON envelope.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


# ── Exception Classes ─────────────────────────────────────────────────────────
# Defined BEFORE register_exception_handlers so all subclasses are visible.


class AppException(Exception):
    """Base application exception. All custom exceptions extend this."""

    def __init__(
        self,
        detail: str = "An unexpected error occurred",
        status_code: int = 500,
    ) -> None:
        self.detail      = detail
        self.status_code = status_code
        super().__init__(self.detail)


class AuthException(AppException):
    """Authentication or authorisation failure (401)."""

    def __init__(self, detail: str = "Authentication failed") -> None:
        super().__init__(detail=detail, status_code=401)


class NotFoundException(AppException):
    """Resource not found (404)."""

    def __init__(self, detail: str = "Not found") -> None:
        super().__init__(detail=detail, status_code=404)


class ValidationException(AppException):
    """Request validation error (422)."""

    def __init__(self, detail: str = "Validation error") -> None:
        super().__init__(detail=detail, status_code=422)


class AgentExecutionException(AppException):
    """AI agent execution failure (500)."""

    def __init__(self, detail: str = "Agent execution failed") -> None:
        super().__init__(detail=detail, status_code=500)


class StorageException(AppException):
    """Object-storage (MinIO) failure (500)."""

    def __init__(self, detail: str = "Storage operation failed") -> None:
        super().__init__(detail=detail, status_code=500)


# ── Exception Handler Registration ───────────────────────────────────────────


def _json(exc: AppException) -> JSONResponse:
    """Shared envelope builder — { error, type }."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "type": type(exc).__name__},
    )


def register_exception_handlers(app: FastAPI) -> None:
    """
    Register JSON error handlers for every custom exception type.

    Registration order matters: more-specific subclasses first so FastAPI
    matches the tightest handler before falling back to the base AppException.
    """

    @app.exception_handler(AuthException)
    async def _auth(request: Request, exc: AuthException) -> JSONResponse:
        return _json(exc)

    @app.exception_handler(NotFoundException)
    async def _not_found(request: Request, exc: NotFoundException) -> JSONResponse:
        return _json(exc)

    @app.exception_handler(ValidationException)
    async def _validation(request: Request, exc: ValidationException) -> JSONResponse:
        return _json(exc)

    @app.exception_handler(AgentExecutionException)
    async def _agent(request: Request, exc: AgentExecutionException) -> JSONResponse:
        return _json(exc)

    @app.exception_handler(StorageException)
    async def _storage(request: Request, exc: StorageException) -> JSONResponse:
        return _json(exc)

    # Base handler — catches any AppException subclass not matched above.
    @app.exception_handler(AppException)
    async def _base(request: Request, exc: AppException) -> JSONResponse:
        return _json(exc)
