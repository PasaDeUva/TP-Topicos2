import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.accounts import create_account
from app.database import get_session
from app.models import ACCOUNT_EMAIL_CONSTRAINT, Account, RefreshCredential, RoleAssignment, Session as LoginSession
from app.observability import request_log
from app.passwords import verify_password
from app.schemas import (
    AccountOut, AccountRolesOut, Login, OrganizerStatus, OrganizerStatusOut,
    RefreshRequest, Registration, RoleOut, RoleRequest, RolesOut, TokenOut,
)
from app.service_auth import authorize_service
from app.tokens import issue_access_token, verify_access_token

app = FastAPI(title="Identity Service")
app.middleware("http")(request_log)
bearer = HTTPBearer(auto_error=False)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.exception_handler(RequestValidationError)
def invalid_request(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=400, content={"code": "invalid_request", "message": "Invalid request"})


@app.post("/auth/register", response_model=AccountOut, status_code=201)
def register(payload: Registration, session: Session = Depends(get_session)):
    try:
        account = create_account(session, payload.email, payload.password)
        status = "activo" if payload.role == "cliente" else "pendiente"
        session.add(RoleAssignment(account_id=account.id, role=payload.role, status=status))
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        if getattr(exc.orig.diag, "constraint_name", None) == ACCOUNT_EMAIL_CONSTRAINT:
            return JSONResponse(status_code=409, content={"code": "email_exists", "message": "Email already registered"})
        raise
    return AccountOut(account_id=account.id, email=account.email, roles=[RoleOut(role=payload.role, status=status)])


@app.exception_handler(HTTPException)
def http_error(request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"code": exc.detail, "message": "Request rejected"})


def current_account(credentials: HTTPAuthorizationCredentials | None = Depends(bearer), session: Session = Depends(get_session)) -> Account:
    if credentials is None:
        raise HTTPException(status_code=401, detail="invalid_credentials")
    try:
        account_id = verify_access_token(credentials.credentials)
    except (jwt.InvalidTokenError, ValueError, TypeError):
        raise HTTPException(status_code=401, detail="invalid_credentials") from None
    account = session.get(Account, account_id)
    if account is None:
        raise HTTPException(status_code=401, detail="invalid_credentials")
    return account


@app.post("/auth/login", response_model=TokenOut)
def login(payload: Login, session: Session = Depends(get_session)):
    account = session.scalar(select(Account).where(Account.email == payload.email).with_for_update())
    if account is None or not verify_password(payload.password, account.password_hash):
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
    access_token, expires_in = issue_access_token(account.id, login_session.expires_at)
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


@app.post("/auth/refresh", response_model=TokenOut)
def refresh(payload: RefreshRequest, session: Session = Depends(get_session)):
    login_session, credential = locked_refresh_session(session, payload.refresh_token)
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
    access_token, expires_in = issue_access_token(login_session.account_id, login_session.expires_at)
    session.commit()
    return {"access_token": access_token, "refresh_token": new_token, "token_type": "Bearer", "expires_in": expires_in}


@app.post("/auth/logout", status_code=204)
def logout(payload: RefreshRequest, session: Session = Depends(get_session)):
    login_session, credential = locked_refresh_session(session, payload.refresh_token)
    if credential.consumed or login_session.revoked or login_session.expires_at <= datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="invalid_credentials")
    login_session.revoked = True
    session.commit()
    return Response(status_code=204)


@app.post("/auth/me/roles", response_model=RolesOut)
def request_role(payload: RoleRequest, account: Account = Depends(current_account), session: Session = Depends(get_session)):
    status = "activo" if payload.role == "cliente" else "pendiente"
    session.add(RoleAssignment(account_id=account.id, role=payload.role, status=status))
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        if getattr(exc.orig.diag, "constraint_name", None) == "uq_role_assignments_account_role":
            raise HTTPException(status_code=409, detail="role_exists") from None
        raise
    roles = session.scalars(select(RoleAssignment).where(RoleAssignment.account_id == account.id).order_by(RoleAssignment.role)).all()
    return {"roles": [{"role": role.role, "status": role.status} for role in roles]}


@app.get("/auth/me", response_model=AccountOut)
def get_me(account: Account = Depends(current_account), session: Session = Depends(get_session)):
    roles = session.scalars(select(RoleAssignment).where(RoleAssignment.account_id == account.id).order_by(RoleAssignment.role)).all()
    return AccountOut(
        account_id=account.id,
        email=account.email,
        roles=[RoleOut(role=role.role, status=role.status) for role in roles],
    )


@app.patch("/admin/organizers/{account_id}/status", response_model=OrganizerStatusOut)
def set_organizer_status(account_id: UUID, payload: OrganizerStatus, account: Account = Depends(current_account), session: Session = Depends(get_session)):
    admin = session.scalar(select(RoleAssignment).where(RoleAssignment.account_id == account.id, RoleAssignment.role == "administrador", RoleAssignment.status == "activo"))
    if admin is None:
        raise HTTPException(status_code=403, detail="forbidden")
    role = session.scalar(select(RoleAssignment).where(RoleAssignment.account_id == account_id, RoleAssignment.role == "organizador").with_for_update())
    if role is None:
        raise HTTPException(status_code=404, detail="not_found")
    role.status = payload.status
    session.commit()
    return {"account_id": str(account_id), "status": payload.status}


@app.get("/internal/accounts/{account_id}/roles", response_model=AccountRolesOut, dependencies=[Depends(authorize_service)])
def get_account_roles(account_id: UUID, session: Session = Depends(get_session)):
    if session.get(Account, account_id) is None:
        raise HTTPException(status_code=404, detail="not_found")
    roles = session.scalars(select(RoleAssignment).where(RoleAssignment.account_id == account_id).order_by(RoleAssignment.role)).all()
    return {"account_id": str(account_id), "roles": [{"role": role.role, "status": role.status} for role in roles]}
