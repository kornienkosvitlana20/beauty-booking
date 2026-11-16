from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import SessionLocal
from .models import Master, User
from .security import decode_token

bearer = HTTPBearer(auto_error=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    user_id = decode_token(creds.credentials) if creds else None
    user = db.get(User, user_id) if user_id else None
    if user is None:
        raise HTTPException(401, "Потрібна авторизація")
    return user


def require_client(user: User = Depends(get_current_user)) -> User:
    if user.role != "client":
        raise HTTPException(403, "Дія доступна лише клієнтам")
    return user


def require_master(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> Master:
    if user.role != "master":
        raise HTTPException(403, "Дія доступна лише майстрам")
    master = db.scalar(select(Master).where(Master.user_id == user.id))
    if master is None:
        raise HTTPException(404, "Спочатку створіть профіль майстра")
    return master
