"""Shared FastAPI dependencies: the database session and the signed-in user."""

import datetime as dt
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import get_db
from .models import AuthToken, User
from .services.auth import hash_token

DbSession = Annotated[Session, Depends(get_db)]


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(request: Request, db: DbSession) -> User:
    """Resolve `Authorization: Bearer <token>` to a user, or respond 401."""
    scheme, _, token = request.headers.get("Authorization", "").partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise _unauthorized("Please sign in.")
    session = db.scalar(select(AuthToken).where(AuthToken.token_hash == hash_token(token)))
    if session is None:
        raise _unauthorized("Your session has ended. Please sign in again.")
    expires = session.expires_at
    if expires.tzinfo is None:  # SQLite drops the timezone
        expires = expires.replace(tzinfo=dt.UTC)
    if expires < dt.datetime.now(dt.UTC):
        db.delete(session)
        db.commit()
        raise _unauthorized("Your session has ended. Please sign in again.")
    request.state.auth_token_id = session.id
    return session.user


CurrentUser = Annotated[User, Depends(get_current_user)]
