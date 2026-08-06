"""
Authentication routes: signup, login, token refresh, current-user lookup,
Google Sign-In.

Login uses OAuth2's password-flow form (username + password) so FastAPI's
generated OpenAPI docs get a working "Authorize" button. The `username`
field accepts either the account's username or email.
"""
import logging
import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from core.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
    get_db,
    hash_password,
    verify_password,
)
from models import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


class SignupRequest(BaseModel):
    username: str = Field(min_length=3, max_length=255)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class GoogleAuthRequest(BaseModel):
    credential: str  # the ID token Google Identity Services returns to the frontend


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    is_active: bool

    class Config:
        from_attributes = True


@router.post("/signup", response_model=TokenResponse, status_code=201)
async def signup(payload: SignupRequest, session: AsyncSession = Depends(get_db)):
    existing = await session.execute(
        select(User).where(
            or_(User.username == payload.username, User.email == payload.email)
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with that username or email already exists",
        )

    user = User(
        username=payload.username,
        email=payload.email,
        hashed_password=hash_password(payload.password),
    )
    session.add(user)
    await session.flush()

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


async def _unique_username_from_email(email: str, session: AsyncSession) -> str:
    """Derive a username from the local part of an email, disambiguating
    against existing rows (Google gives no username of its own)."""
    base = email.split("@", 1)[0][:240] or "user"
    candidate = base
    suffix = 0
    while True:
        existing = await session.execute(select(User).where(User.username == candidate))
        if existing.scalar_one_or_none() is None:
            return candidate
        suffix += 1
        candidate = f"{base}{suffix}"


@router.post("/google", response_model=TokenResponse)
async def google_signin(payload: GoogleAuthRequest, session: AsyncSession = Depends(get_db)):
    """Sign in (or auto-register) using a Google Identity Services ID token.

    Verifies the token's signature and audience against GOOGLE_CLIENT_ID -
    no client secret is needed for this flow, only the public Client ID.
    """
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=503, detail="Google sign-in is not configured on this server")

    try:
        # clock_skew_in_seconds defaults to 0 in this library - meaning even
        # a 1-second difference between this machine's clock and Google's
        # token timestamp hard-fails sign-in with "Token used too early".
        # 10s matches common practice (e.g. Google's own JWT libraries
        # elsewhere) and absorbs normal NTP drift without weakening the
        # token's actual freshness guarantee in any meaningful way.
        idinfo = google_id_token.verify_oauth2_token(
            payload.credential, google_requests.Request(), settings.GOOGLE_CLIENT_ID,
            clock_skew_in_seconds=10,
        )
    except ValueError as e:
        logger.warning(f"Google ID token verification failed: {e}")
        raise HTTPException(status_code=401, detail="Invalid Google credential")

    email = idinfo.get("email")
    if not email or not idinfo.get("email_verified"):
        raise HTTPException(status_code=401, detail="Google account has no verified email")

    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user is None:
        username = await _unique_username_from_email(email, session)
        # Google-authenticated accounts never use a password, but the
        # column is NOT NULL - store an unusable random hash rather than
        # loosening the schema for every other account.
        user = User(
            username=username,
            email=email,
            hashed_password=hash_password(secrets.token_urlsafe(32)),
        )
        session.add(user)
        await session.flush()
    elif not user.is_active:
        raise HTTPException(status_code=403, detail="Inactive user")

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_db),
):
    result = await session.execute(
        select(User).where(
            or_(User.username == form_data.username, User.email == form_data.username)
        )
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username/email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(payload: RefreshRequest, session: AsyncSession = Depends(get_db)):
    user_id = decode_token(payload.refresh_token, expected_type="refresh")

    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)):
    return current_user
