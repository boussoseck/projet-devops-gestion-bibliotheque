import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from passlib.context import CryptContext
from sqlalchemy.orm import Session as DbSession

from . import models

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SESSION_DURATION_HOURS = 12


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return pwd_context.verify(password, password_hash)
    except Exception:
        return False


def create_session(db: DbSession, user: models.User) -> models.Session:
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=SESSION_DURATION_HOURS)
    db_session = models.Session(token=token, user_id=user.id, expires_at=expires_at)
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    return db_session


def get_user_from_token(db: DbSession, token: Optional[str]) -> Optional[models.User]:
    if not token:
        return None
    db_session = db.query(models.Session).filter(models.Session.token == token).first()
    if not db_session:
        return None
    expires_at = db_session.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        db.delete(db_session)
        db.commit()
        return None
    return db.query(models.User).filter(models.User.id == db_session.user_id).first()


def delete_session(db: DbSession, token: Optional[str]) -> None:
    if not token:
        return
    db.query(models.Session).filter(models.Session.token == token).delete()
    db.commit()


def log_email(db: DbSession, destinataire: str, sujet: str, corps: str) -> models.EmailLog:
    """Simule l'envoi d'un e-mail : enregistré en base + affiché dans les logs du service."""
    entry = models.EmailLog(destinataire=destinataire, sujet=sujet, corps=corps)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    print(f"[EMAIL SIMULÉ] À: {destinataire} | Sujet: {sujet}\n{corps}\n")
    return entry
