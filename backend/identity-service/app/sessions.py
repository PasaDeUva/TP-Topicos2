import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Account, RefreshCredential, RoleAssignment, Session as LoginSession
from app.passwords import verify_password
from app.tokens import issue_access_token


def start_session(session: Session, email: str, password: str):
    account = session.scalar(select(Account).where(Account.email == email).with_for_update())
    if account is None or not verify_password(password, account.password_hash):
        raise HTTPException(status_code=401, detail="invalid_credentials")
    roles = session.scalars(select(RoleAssignment).where(RoleAssignment.account_id == account.id)).all()
    if not any(role.status in ("activo", "habilitado", "pendiente") for role in roles):
        raise HTTPException(status_code=401, detail="invalid_credentials")
    now = datetime.now(timezone.utc)
    login_session = LoginSession(account_id=account.id, started_at=now, expires_at=now + timedelta(hours=24), revoked=False)
    session.add(login_session)
    session.flush()
    refresh_token = secrets.token_urlsafe(32)
    session.add(RefreshCredential(session_id=login_session.id, secret_hash=hashlib.sha256(refresh_token.encode()).hexdigest(), consumed=False))
    access_token, expires_in = issue_access_token(account.id, login_session.id, login_session.expires_at)
    session.commit()
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "Bearer", "expires_in": expires_in}


def locked_refresh_session(session: Session, refresh_token: str):
    digest = hashlib.sha256(refresh_token.encode()).hexdigest()
    login_session = session.scalar(
        select(LoginSession)
        .join(RefreshCredential, RefreshCredential.session_id == LoginSession.id)
        .where(RefreshCredential.secret_hash == digest)
        .with_for_update(of=LoginSession)
    )
    if login_session is None:
        raise HTTPException(status_code=401, detail="invalid_credentials")
    credential = session.scalar(select(RefreshCredential).where(RefreshCredential.secret_hash == digest))
    return login_session, credential


def rotate_session(session: Session, refresh_token: str):
    login_session, credential = locked_refresh_session(session, refresh_token)
    now = datetime.now(timezone.utc)
    if credential.consumed:
        login_session.revoked = True
        session.commit()
        raise HTTPException(status_code=401, detail="invalid_credentials")
    if login_session.revoked or login_session.expires_at <= now:
        raise HTTPException(status_code=401, detail="invalid_credentials")
    roles = session.scalars(select(RoleAssignment).where(RoleAssignment.account_id == login_session.account_id)).all()
    if not any(role.status in ("activo", "habilitado", "pendiente") for role in roles):
        raise HTTPException(status_code=401, detail="invalid_credentials")
    credential.consumed = True
    session.flush()
    new_token = secrets.token_urlsafe(32)
    session.add(RefreshCredential(session_id=login_session.id, secret_hash=hashlib.sha256(new_token.encode()).hexdigest(), consumed=False))
    access_token, expires_in = issue_access_token(login_session.account_id, login_session.id, login_session.expires_at)
    session.commit()
    return {"access_token": access_token, "refresh_token": new_token, "token_type": "Bearer", "expires_in": expires_in}


def revoke_session(session: Session, refresh_token: str):
    login_session, credential = locked_refresh_session(session, refresh_token)
    if credential.consumed or login_session.revoked or login_session.expires_at <= datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="invalid_credentials")
    login_session.revoked = True
    session.commit()
