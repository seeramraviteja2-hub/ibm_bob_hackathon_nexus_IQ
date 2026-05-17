"""
NexusIQ — Auth API endpoints.
POST /auth/register
POST /auth/login
POST /auth/refresh
"""
import uuid
from datetime import timedelta

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from db.models import User, UserRole
from db.session import get_db
from exceptions.base import AuthException, ValidationException
from utils.security import (
    create_access_token, create_refresh_token,
    decode_token, hash_password, verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    first_name: str = ""
    last_name: str = ""
    role: str = "employee"   # "manager" | "employee"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    role: str
    user_id: str


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    existing = await db.scalar(select(User).where(User.email == data.email))
    if existing:
        raise ValidationException("Email already registered")

    try:
        role = UserRole(data.role)
    except ValueError:
        raise ValidationException(f"Invalid role: {data.role}")

    user = User(
        id=uuid.uuid4(),
        email=data.email,
        first_name=data.first_name,
        last_name=data.last_name,
        hashed_password=hash_password(data.password),
        role=role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token_data = {"sub": str(user.id), "role": user.role.value}
    return TokenResponse(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data),
        role=user.role.value,
        user_id=str(user.id),
    )


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)):
    user = await db.scalar(select(User).where(User.email == data.email, User.is_active == True))
    if not user or not verify_password(data.password, user.hashed_password):
        raise AuthException("Invalid email or password")

    token_data = {"sub": str(user.id), "role": user.role.value}
    access  = create_access_token(token_data)
    refresh = create_refresh_token(token_data)

    # Also set HttpOnly cookie (used by WebSocket auth)
    response.set_cookie(
        key="access_token",
        value=access,
        httponly=True,
        samesite="lax",
        secure=settings.ENVIRONMENT != "dev",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )

    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        role=user.role.value,
        user_id=str(user.id),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(body: dict, db: AsyncSession = Depends(get_db)):
    token = body.get("refresh_token")
    if not token:
        raise AuthException("Missing refresh_token")

    payload = decode_token(token)
    if payload.get("type") != "refresh":
        raise AuthException("Not a refresh token")

    user_id = payload.get("sub")
    user = await db.scalar(select(User).where(User.id == uuid.UUID(user_id), User.is_active == True))
    if not user:
        raise AuthException("User not found")

    token_data = {"sub": str(user.id), "role": user.role.value}
    return TokenResponse(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data),
        role=user.role.value,
        user_id=str(user.id),
    )
