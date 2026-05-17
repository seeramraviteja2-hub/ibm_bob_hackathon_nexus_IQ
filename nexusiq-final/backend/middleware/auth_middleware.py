"""
NexusIQ — Auth middleware / FastAPI dependency.
require_role("manager") / require_role("employee") guards all protected routes.
"""
import uuid
from typing import Callable

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import User, UserRole
from db.session import get_db
from exceptions.base import AuthException
from utils.security import decode_token

_bearer = HTTPBearer(auto_error=False)


async def _get_token(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> str:
    """
    Extract JWT from:
      1. Authorization: Bearer <token>  header
      2. access_token HttpOnly cookie (set by /auth/login)
    """
    if credentials and credentials.credentials:
        return credentials.credentials
    cookie_token = request.cookies.get("access_token")
    if cookie_token:
        return cookie_token
    raise AuthException("Missing authentication token")


async def _get_current_user(
    token: str = Depends(_get_token),
    db: AsyncSession = Depends(get_db),
) -> User:
    payload = decode_token(token)
    user_id_str: str | None = payload.get("sub")
    if not user_id_str:
        raise AuthException("Token missing subject claim")

    try:
        uid = uuid.UUID(user_id_str)
    except ValueError:
        raise AuthException("Invalid user ID in token")

    user = await db.scalar(select(User).where(User.id == uid, User.is_active == True))
    if not user:
        raise AuthException("User not found or inactive")
    return user


def require_role(*roles: str) -> Callable:
    """
    Returns a FastAPI dependency that validates the user has one of the given roles.

    Usage:
        current_user: User = Depends(require_role("manager"))
        current_user: User = Depends(require_role("manager", "employee"))
    """
    allowed = {UserRole(r) for r in roles}

    async def dependency(user: User = Depends(_get_current_user)) -> User:
        if user.role not in allowed:
            raise AuthException(
                f"Access denied. Required role(s): {[r.value for r in allowed]}"
            )
        return user

    return dependency
