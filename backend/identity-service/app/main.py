import hashlib
import hmac
from datetime import datetime, timezone
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
from app.models import ACCOUNT_EMAIL_CONSTRAINT, Account, RoleAssignment
from app.observability import request_log
from app.schemas import (
    AccountOut, AccountRolesOut, CsrfOut, ErrorOut, Login, OrganizerStatus, OrganizerStatusOut,
    PASSWORD_MIN_LENGTH, RefreshRequest, Registration, RoleOut, RoleRequest, RolesOut, TokenOut, WebLoginOut, WebTokenOut, OrganizerOut,
)
from app.service_auth import authorize_service
from app.sessions import locked_refresh_session, revoke_session, rotate_session, start_session
from app.tokens import verify_access_token
from app.web_config import WebSessionConfig, load_web_session_config
from app.web_cors import WebCORSMiddleware

app = FastAPI(title="Identity Service", responses={500: {"model": ErrorOut, "description": "Internal server error"}})
app.middleware("http")(request_log)
app.add_middleware(WebCORSMiddleware)
bearer = HTTPBearer(auto_error=False)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.exception_handler(RequestValidationError)
def invalid_request(request: Request, exc: RequestValidationError):
    if request.method == "POST" and request.url.path == "/auth/register":
        for error in exc.errors():
            if error.get("loc") == ("body", "password") and error.get("type") == "string_too_short":
                return JSONResponse(
                    status_code=400,
                    content={"code": "invalid_request", "message": f"Password must contain at least {PASSWORD_MIN_LENGTH} characters"},
                )
    return JSONResponse(status_code=400, content={"code": "invalid_request", "message": "Invalid request"})


@app.post("/auth/register", response_model=AccountOut, status_code=201, responses={400: {"model": ErrorOut}, 409: {"model": ErrorOut}})
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
    headers = {"Cache-Control": "no-store"} if request.url.path.startswith("/auth/web/") else None
    return JSONResponse(status_code=exc.status_code, content={"code": exc.detail, "message": "Request rejected"}, headers=headers)


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


@app.post("/auth/login", response_model=TokenOut, responses={400: {"model": ErrorOut}, 401: {"model": ErrorOut}})
def login(payload: Login, session: Session = Depends(get_session)):
    return start_session(session, payload.email, payload.password)


def csrf_for_session(secret: bytes, session_id: UUID) -> str:
    return hmac.new(secret, str(session_id).encode(), hashlib.sha256).hexdigest()


def web_openapi(*, cookie: bool, csrf: bool, origin_required: bool, set_cookie: bool, status: str = "200"):
    parameters = [{"name": "Origin", "in": "header", "required": origin_required, "schema": {"type": "string"}, "description": "Configured browser origin; required for POST requests."}]
    if cookie:
        parameters.append({"name": "identity_refresh", "in": "cookie", "required": True, "schema": {"type": "string"}, "description": "HttpOnly refresh credential."})
    if csrf:
        parameters.append({"name": "X-CSRF-Token", "in": "header", "required": True, "schema": {"type": "string"}, "description": "CSRF token bound to the session."})
    headers = {"Cache-Control": {"description": "Responses must not be cached.", "schema": {"type": "string"}}}
    if set_cookie:
        headers["Set-Cookie"] = {"description": "Host-only HttpOnly refresh cookie, issued, rotated or deleted.", "schema": {"type": "string"}}
    return {"parameters": parameters, "responses": {status: {"headers": headers}}}


@app.post("/auth/web/login", response_model=WebLoginOut, responses={400: {"model": ErrorOut, "description": "Invalid request"}, 401: {"model": ErrorOut, "description": "Invalid credentials"}, 403: {"model": ErrorOut, "description": "Origin not allowed"}, 503: {"model": ErrorOut, "description": "Web session configuration unavailable"}}, openapi_extra=web_openapi(cookie=False, csrf=False, origin_required=True, set_cookie=True))
def web_login(payload: Login, request: Request, response: Response, session: Session = Depends(get_session)):
    try:
        config = load_web_session_config()
    except ValueError:
        raise HTTPException(status_code=503, detail="web_session_unavailable") from None
    if request.headers.get("origin") not in config.allowed_origins:
        raise HTTPException(status_code=403, detail="origin_not_allowed")
    tokens = start_session(session, payload.email, payload.password)
    login_session, _ = locked_refresh_session(session, tokens["refresh_token"])
    csrf_token = csrf_for_session(config.csrf_secret, login_session.id)
    response.headers["Cache-Control"] = "no-store"
    response.set_cookie(
        key=config.cookie_name, value=tokens["refresh_token"], path=config.cookie_path,
        secure=config.cookie_secure, httponly=True, samesite=config.cookie_samesite,
    )
    return {"access_token": tokens["access_token"], "token_type": tokens["token_type"], "expires_in": tokens["expires_in"], "csrf_token": csrf_token}


@app.get("/auth/web/csrf", response_model=CsrfOut, responses={401: {"model": ErrorOut, "description": "Invalid or expired session"}, 403: {"model": ErrorOut, "description": "Origin not allowed"}, 503: {"model": ErrorOut, "description": "Web session configuration unavailable"}}, openapi_extra=web_openapi(cookie=True, csrf=False, origin_required=False, set_cookie=False))
def web_csrf(request: Request, response: Response, session: Session = Depends(get_session)):
    try:
        config = load_web_session_config()
    except ValueError:
        raise HTTPException(status_code=503, detail="web_session_unavailable") from None
    origin = request.headers.get("origin")
    if origin is not None and origin not in config.allowed_origins:
        raise HTTPException(status_code=403, detail="origin_not_allowed")
    refresh_token = request.cookies.get(config.cookie_name)
    if not refresh_token:
        raise HTTPException(status_code=401, detail="invalid_credentials")
    login_session, credential = locked_refresh_session(session, refresh_token)
    if credential.consumed or login_session.revoked or login_session.expires_at <= datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="invalid_credentials")
    roles = session.scalars(select(RoleAssignment).where(RoleAssignment.account_id == login_session.account_id)).all()
    if not any(role.status in ("activo", "habilitado", "pendiente") for role in roles):
        raise HTTPException(status_code=401, detail="invalid_credentials")
    response.headers["Cache-Control"] = "no-store"
    return {"csrf_token": csrf_for_session(config.csrf_secret, login_session.id)}


def authorize_web_mutation(request: Request, session: Session) -> tuple[WebSessionConfig, str]:
    try:
        config = load_web_session_config()
    except ValueError:
        raise HTTPException(status_code=503, detail="web_session_unavailable") from None
    if request.headers.get("origin") not in config.allowed_origins:
        raise HTTPException(status_code=403, detail="origin_not_allowed")
    refresh_token = request.cookies.get(config.cookie_name)
    if not refresh_token:
        raise HTTPException(status_code=401, detail="invalid_credentials")
    login_session, _ = locked_refresh_session(session, refresh_token)
    expected = csrf_for_session(config.csrf_secret, login_session.id).encode()
    provided = request.headers.get("x-csrf-token", "").encode()
    if not hmac.compare_digest(expected, provided):
        raise HTTPException(status_code=403, detail="invalid_csrf")
    return config, refresh_token


@app.post("/auth/web/refresh", response_model=WebTokenOut, responses={401: {"model": ErrorOut, "description": "Invalid or expired session"}, 403: {"model": ErrorOut, "description": "Invalid origin or CSRF token"}, 503: {"model": ErrorOut, "description": "Web session configuration unavailable"}}, openapi_extra=web_openapi(cookie=True, csrf=True, origin_required=True, set_cookie=True))
def web_refresh(request: Request, response: Response, session: Session = Depends(get_session)):
    config, refresh_token = authorize_web_mutation(request, session)
    tokens = rotate_session(session, refresh_token)
    response.headers["Cache-Control"] = "no-store"
    response.set_cookie(
        key=config.cookie_name, value=tokens["refresh_token"], path=config.cookie_path,
        secure=config.cookie_secure, httponly=True, samesite=config.cookie_samesite,
    )
    return {"access_token": tokens["access_token"], "token_type": tokens["token_type"], "expires_in": tokens["expires_in"]}


@app.post("/auth/web/logout", status_code=204, responses={401: {"model": ErrorOut, "description": "Invalid or expired session"}, 403: {"model": ErrorOut, "description": "Invalid origin or CSRF token"}, 503: {"model": ErrorOut, "description": "Web session configuration unavailable"}}, openapi_extra=web_openapi(cookie=True, csrf=True, origin_required=True, set_cookie=True, status="204"))
def web_logout(request: Request, session: Session = Depends(get_session)):
    config, refresh_token = authorize_web_mutation(request, session)
    revoke_session(session, refresh_token)
    response = Response(status_code=204, headers={"Cache-Control": "no-store"})
    response.delete_cookie(
        key=config.cookie_name, path=config.cookie_path, secure=config.cookie_secure,
        httponly=True, samesite=config.cookie_samesite,
    )
    return response


@app.post("/auth/refresh", response_model=TokenOut, responses={400: {"model": ErrorOut}, 401: {"model": ErrorOut}})
def refresh(payload: RefreshRequest, session: Session = Depends(get_session)):
    return rotate_session(session, payload.refresh_token)


@app.post("/auth/logout", status_code=204, responses={400: {"model": ErrorOut}, 401: {"model": ErrorOut}})
def logout(payload: RefreshRequest, session: Session = Depends(get_session)):
    revoke_session(session, payload.refresh_token)
    return Response(status_code=204)


@app.post("/auth/me/roles", response_model=RolesOut, responses={400: {"model": ErrorOut}, 401: {"model": ErrorOut}, 409: {"model": ErrorOut}})
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


@app.get("/auth/me", response_model=AccountOut, responses={401: {"model": ErrorOut}})
def get_me(account: Account = Depends(current_account), session: Session = Depends(get_session)):
    roles = session.scalars(select(RoleAssignment).where(RoleAssignment.account_id == account.id).order_by(RoleAssignment.role)).all()
    return AccountOut(
        account_id=account.id,
        email=account.email,
        roles=[RoleOut(role=role.role, status=role.status) for role in roles],
    )


@app.get("/admin/organizers", response_model=list[OrganizerOut], responses={401: {"model": ErrorOut}, 403: {"model": ErrorOut}})
def list_organizers(account: Account = Depends(current_account), session: Session = Depends(get_session)):
    admin = session.scalar(select(RoleAssignment.id).where(RoleAssignment.account_id == account.id, RoleAssignment.role == "administrador", RoleAssignment.status == "activo"))
    if admin is None:
        raise HTTPException(status_code=403, detail="forbidden")
    rows = session.execute(
        select(Account.id, Account.email, RoleAssignment.status)
        .join(RoleAssignment, RoleAssignment.account_id == Account.id)
        .where(RoleAssignment.role == "organizador")
        .order_by(Account.email, Account.id)
    ).all()
    return [{"account_id": row.id, "email": row.email, "status": row.status} for row in rows]


@app.patch("/admin/organizers/{account_id}/status", response_model=OrganizerStatusOut, responses={400: {"model": ErrorOut}, 401: {"model": ErrorOut}, 403: {"model": ErrorOut}, 404: {"model": ErrorOut}})
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


@app.get("/internal/accounts/{account_id}/roles", response_model=AccountRolesOut, dependencies=[Depends(authorize_service)], responses={400: {"model": ErrorOut}, 401: {"model": ErrorOut}, 403: {"model": ErrorOut}, 404: {"model": ErrorOut}, 503: {"model": ErrorOut}})
def get_account_roles(account_id: UUID, session: Session = Depends(get_session)):
    if session.get(Account, account_id) is None:
        raise HTTPException(status_code=404, detail="not_found")
    roles = session.scalars(select(RoleAssignment).where(RoleAssignment.account_id == account_id).order_by(RoleAssignment.role)).all()
    return {"account_id": str(account_id), "roles": [{"role": role.role, "status": role.status} for role in roles]}


_default_openapi = app.openapi


def openapi_with_actual_validation_errors():
    schema = _default_openapi()
    for path in schema["paths"].values():
        for operation in path.values():
            if not isinstance(operation, dict):
                continue
            responses = operation.get("responses", {})
            validation = responses.get("422", {}).get("content", {}).get("application/json", {}).get("schema", {})
            if validation.get("$ref") == "#/components/schemas/HTTPValidationError":
                responses.pop("422")
    return schema


app.openapi = openapi_with_actual_validation_errors
