import os
import json
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Barrier

import pytest
import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from fastapi import HTTPException, Request, Response
from sqlalchemy import create_engine, delete, select
from sqlalchemy.orm import Session

from app.database import get_session
from app.accounts import create_account
from app.admin import initialize_admin, recover_admin
from app.main import app, csrf_for_session, login, refresh, web_refresh
from app.models import Account, RefreshCredential, RoleAssignment, Session as LoginSession
from app.schemas import Login, RefreshRequest


@pytest.fixture
def client(monkeypatch):
    url = os.environ.get("IDENTITY_TEST_DATABASE_URL")
    if not url:
        pytest.fail("IDENTITY_TEST_DATABASE_URL is required for PostgreSQL persistence tests")
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode()
    public = key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    monkeypatch.setenv("JWT_PRIVATE_KEY", private)
    monkeypatch.setenv("JWT_PUBLIC_KEY", public)
    monkeypatch.setenv("JWT_ISSUER", "identity-test")
    monkeypatch.setenv("JWT_AUDIENCE", "services-test")
    engine = create_engine(url)
    with engine.connect() as connection:
        transaction = connection.begin()
        with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
            app.dependency_overrides[get_session] = lambda: session
            try:
                with TestClient(app) as test_client:
                    yield test_client
            finally:
                app.dependency_overrides.clear()
        transaction.rollback()
    engine.dispose()


@pytest.mark.parametrize(("role", "status"), [("cliente", "activo"), ("organizador", "pendiente")])
def test_register_role(client, role, status):
    email = f"{uuid.uuid4()}@example.com"
    response = client.post("/auth/register", json={"email": email, "password": "password123", "role": role})
    assert response.status_code == 201
    assert response.json()["email"] == email
    assert response.json()["roles"] == [{"role": role, "status": status}]
    assert "password" not in response.json()


def test_duplicate_email(client):
    payload = {"email": f"{uuid.uuid4()}@example.com", "password": "password123", "role": "cliente"}
    assert client.post("/auth/register", json=payload).status_code == 201
    assert client.post("/auth/register", json=payload).status_code == 409


@pytest.mark.parametrize("changes", [{"email": "invalid"}, {"password": "short"}, {"role": "administrador"}])
def test_invalid_registration(client, changes):
    payload = {"email": f"{uuid.uuid4()}@example.com", "password": "password123", "role": "cliente"}
    payload.update(changes)
    assert client.post("/auth/register", json=payload).status_code == 400


def test_short_password_reports_minimum_without_exposing_password(client, capsys):
    password = "short7!"
    payload = {"email": f"{uuid.uuid4()}@example.com", "password": password, "role": "cliente"}
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 400
    assert response.json() == {"code": "invalid_request", "message": "Password must contain at least 8 characters"}
    assert password not in response.text
    assert password not in capsys.readouterr().out


def test_password_minimum_is_accepted_and_other_errors_remain_generic(client):
    payload = {"email": f"{uuid.uuid4()}@example.com", "password": "abcdefgh", "role": "cliente"}
    assert client.post("/auth/register", json=payload).status_code == 201
    payload["email"] = "invalid"
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 400
    assert response.json() == {"code": "invalid_request", "message": "Invalid request"}


def test_long_password_and_refresh_token_are_not_rejected_by_length(client):
    email = f"{uuid.uuid4()}@example.com"
    password = "a" * 1025
    assert client.post("/auth/register", json={"email": email, "password": password, "role": "cliente"}).status_code == 201
    assert client.post("/auth/login", json={"email": email, "password": password}).status_code == 200
    for endpoint in ("/auth/refresh", "/auth/logout"):
        assert client.post(endpoint, json={"refresh_token": "x" * 257}).status_code == 401


def test_openapi_documents_success_response_models(client):
    paths = client.get("/openapi.json").json()["paths"]
    expected = {
        ("/auth/login", "post"): "TokenOut",
        ("/auth/refresh", "post"): "TokenOut",
        ("/auth/me/roles", "post"): "RolesOut",
        ("/admin/organizers/{account_id}/status", "patch"): "OrganizerStatusOut",
        ("/internal/accounts/{account_id}/roles", "get"): "AccountRolesOut",
    }
    for (path, method), model in expected.items():
        schema = paths[path][method]["responses"]["200"]["content"]["application/json"]["schema"]
        assert schema["$ref"] == f"#/components/schemas/{model}"


def test_openapi_documents_actual_error_responses(client):
    paths = client.get("/openapi.json").json()["paths"]
    expected = {
        ("/auth/register", "post"): {"400", "409", "500"},
        ("/auth/login", "post"): {"400", "401", "500"},
        ("/auth/refresh", "post"): {"400", "401", "500"},
        ("/auth/logout", "post"): {"400", "401", "500"},
        ("/auth/me", "get"): {"401", "500"},
        ("/auth/me/roles", "post"): {"400", "401", "409", "500"},
        ("/admin/organizers/{account_id}/status", "patch"): {"400", "401", "403", "404", "500"},
        ("/internal/accounts/{account_id}/roles", "get"): {"400", "401", "403", "404", "500", "503"},
    }
    for (path, method), statuses in expected.items():
        responses = paths[path][method]["responses"]
        assert "422" not in responses
        assert statuses <= responses.keys()
        for status in statuses:
            schema = responses[status]["content"]["application/json"]["schema"]
            assert schema["$ref"] == "#/components/schemas/ErrorOut"


def test_openapi_documents_web_session_contract(client):
    paths = client.get("/openapi.json").json()["paths"]
    for path, method, status, required in [
        ("/auth/web/login", "post", "200", {("header", "Origin")}),
        ("/auth/web/csrf", "get", "200", {("cookie", "identity_refresh")}),
        ("/auth/web/refresh", "post", "200", {("header", "Origin"), ("header", "X-CSRF-Token"), ("cookie", "identity_refresh")}),
        ("/auth/web/logout", "post", "204", {("header", "Origin"), ("header", "X-CSRF-Token"), ("cookie", "identity_refresh")}),
    ]:
        operation = paths[path][method]
        parameters = {(item["in"], item["name"]) for item in operation["parameters"] if item["required"]}
        assert parameters == required
        headers = operation["responses"][status]["headers"]
        assert "Cache-Control" in headers
        assert ("Set-Cookie" in headers) == (path != "/auth/web/csrf")
        for error in ("401", "403", "503"):
            schema = operation["responses"][error]["content"]["application/json"]["schema"]
            assert schema["$ref"] == "#/components/schemas/ErrorOut"
        assert "422" not in operation["responses"]


def test_login_and_request_additional_role(client):
    payload = {"email": f"{uuid.uuid4()}@example.com", "password": "password123", "role": "cliente"}
    registration = client.post("/auth/register", json=payload)
    assert registration.status_code == 201
    response = client.post("/auth/login", json={"email": payload["email"], "password": payload["password"]})
    assert response.status_code == 200
    tokens = response.json()
    claims = jwt.decode(tokens["access_token"], os.environ["JWT_PUBLIC_KEY"], algorithms=["RS256"], issuer="identity-test", audience="services-test")
    assert claims["sub"] == registration.json()["account_id"]
    assert claims["exp"] - claims["iat"] <= 3600
    assert tokens["refresh_token"]
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    result = client.post("/auth/me/roles", headers=headers, json={"role": "organizador"})
    assert result.status_code == 200
    assert {item["role"]: item["status"] for item in result.json()["roles"]} == {"cliente": "activo", "organizador": "pendiente"}
    assert client.post("/auth/me/roles", headers=headers, json={"role": "organizador"}).status_code == 409


def test_invalid_login_and_token(client):
    payload = {"email": f"{uuid.uuid4()}@example.com", "password": "password123", "role": "organizador"}
    assert client.post("/auth/register", json=payload).status_code == 201
    assert client.post("/auth/login", json={"email": payload["email"], "password": "wrong"}).status_code == 401
    assert client.post("/auth/me/roles", json={"role": "cliente"}).status_code == 401
    assert client.post("/auth/me/roles", headers={"Authorization": "Bearer invalid"}, json={"role": "cliente"}).status_code == 401


def test_web_login_checks_configuration_origin_and_cookie(client, monkeypatch):
    payload = {"email": f"{uuid.uuid4()}@example.com", "password": "password123", "role": "cliente"}
    assert client.post("/auth/register", json=payload).status_code == 201
    credentials = {"email": payload["email"], "password": payload["password"]}
    monkeypatch.setenv("IDENTITY_ENV", "production")
    monkeypatch.setenv("IDENTITY_WEB_ORIGINS", "https://app.example.com")
    monkeypatch.delenv("IDENTITY_WEB_ALLOW_LOCAL_HTTP", raising=False)
    monkeypatch.delenv("IDENTITY_WEB_CSRF_SECRET", raising=False)
    headers = {"Origin": "https://app.example.com"}
    assert client.post("/auth/web/login", headers=headers, json=credentials).status_code == 503
    monkeypatch.setenv("IDENTITY_WEB_CSRF_SECRET", "x" * 32)
    monkeypatch.setenv("IDENTITY_WEB_ORIGINS", "https://app.example.com,https://app.example.com:8443")
    assert client.post("/auth/web/login", headers=headers, json=credentials).status_code == 503
    monkeypatch.setenv("IDENTITY_WEB_ORIGINS", "https://app.example.com")
    assert client.post("/auth/web/login", headers={"Origin": "https://app.example.com:8443"}, json=credentials).status_code == 403
    assert client.post("/auth/web/login", headers={"Origin": "https://evil.example.com"}, json=credentials).status_code == 403
    assert client.post("/auth/web/login", headers=headers, json={**credentials, "password": "wrong"}).status_code == 401
    response = client.post("/auth/web/login", headers=headers, json=credentials)
    assert response.status_code == 200
    assert set(response.json()) == {"access_token", "token_type", "expires_in", "csrf_token"}
    cookie = response.headers["set-cookie"]
    assert "HttpOnly" in cookie and "Secure" in cookie and "SameSite=strict" in cookie
    assert "Path=/auth/web" in cookie and "Domain=" not in cookie
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["access-control-allow-origin"] == headers["Origin"]
    assert response.headers["access-control-allow-credentials"] == "true"


def test_web_cors_only_allows_configured_origins(client, monkeypatch):
    monkeypatch.setenv("IDENTITY_ENV", "production")
    monkeypatch.setenv("IDENTITY_WEB_ORIGINS", "https://app.example.com")
    monkeypatch.setenv("IDENTITY_WEB_CSRF_SECRET", "x" * 32)
    monkeypatch.delenv("IDENTITY_WEB_ALLOW_LOCAL_HTTP", raising=False)
    headers = {
        "Origin": "https://app.example.com",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type,x-csrf-token",
    }
    response = client.options("/auth/web/login", headers=headers)
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == headers["Origin"]
    assert response.headers["access-control-allow-credentials"] == "true"
    headers["Origin"] = "https://evil.example.com"
    response = client.options("/auth/web/login", headers=headers)
    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers
    monkeypatch.delenv("IDENTITY_WEB_CSRF_SECRET")
    headers["Origin"] = "https://app.example.com"
    assert client.options("/auth/web/login", headers=headers).status_code == 400


def test_admin_patch_cors_preflight_restricts_origin(client, monkeypatch):
    monkeypatch.setenv("IDENTITY_ENV", "production")
    monkeypatch.setenv("IDENTITY_WEB_ORIGINS", "https://app.example.com")
    monkeypatch.setenv("IDENTITY_WEB_CSRF_SECRET", "x" * 32)
    monkeypatch.delenv("IDENTITY_WEB_ALLOW_LOCAL_HTTP", raising=False)
    headers = {"Origin": "https://app.example.com", "Access-Control-Request-Method": "PATCH", "Access-Control-Request-Headers": "authorization,content-type"}
    response = client.options(f"/admin/organizers/{uuid.uuid4()}/status", headers=headers)
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == headers["Origin"]
    headers["Origin"] = "https://evil.example.com"
    response = client.options(f"/admin/organizers/{uuid.uuid4()}/status", headers=headers)
    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


def test_web_csrf_restores_without_rotation_and_rejects_invalid_session(client, monkeypatch):
    monkeypatch.setenv("IDENTITY_ENV", "production")
    monkeypatch.setenv("IDENTITY_WEB_ORIGINS", "https://app.example.com")
    monkeypatch.setenv("IDENTITY_WEB_CSRF_SECRET", "x" * 32)
    monkeypatch.delenv("IDENTITY_WEB_ALLOW_LOCAL_HTTP", raising=False)
    payload = {"email": f"{uuid.uuid4()}@example.com", "password": "password123", "role": "cliente"}
    assert client.post("/auth/register", json=payload).status_code == 201
    login_response = client.post("/auth/web/login", headers={"Origin": "https://app.example.com"}, json=payload)
    cookie = login_response.headers["set-cookie"].split(";", 1)[0]
    headers = {"Cookie": cookie}
    first = client.get("/auth/web/csrf", headers=headers)
    second = client.get("/auth/web/csrf", headers={**headers, "Origin": "https://app.example.com"})
    assert first.status_code == second.status_code == 200
    assert first.json() == second.json() == {"csrf_token": login_response.json()["csrf_token"]}
    assert first.headers["cache-control"] == "no-store" and "set-cookie" not in first.headers
    rejected = client.get("/auth/web/csrf", headers={**headers, "Origin": "https://evil.example.com"})
    assert rejected.status_code == 403 and "access-control-allow-origin" not in rejected.headers
    assert client.get("/auth/web/csrf", headers={"Cookie": "identity_refresh=invalid"}).status_code == 401
    db = app.dependency_overrides[get_session]()
    account = db.scalar(select(Account).where(Account.email == payload["email"]))
    stored = db.scalar(select(LoginSession).where(LoginSession.account_id == account.id))
    stored.revoked = True
    db.commit()
    revoked = client.get("/auth/web/csrf", headers=headers)
    assert revoked.status_code == 401 and revoked.headers["cache-control"] == "no-store"


def test_web_refresh_rejects_invalid_protection_and_replay(client, monkeypatch):
    monkeypatch.setenv("IDENTITY_ENV", "production")
    monkeypatch.setenv("IDENTITY_WEB_ORIGINS", "https://app.example.com")
    monkeypatch.setenv("IDENTITY_WEB_CSRF_SECRET", "x" * 32)
    monkeypatch.delenv("IDENTITY_WEB_ALLOW_LOCAL_HTTP", raising=False)
    payload = {"email": f"{uuid.uuid4()}@example.com", "password": "password123", "role": "cliente"}
    account_id = client.post("/auth/register", json=payload).json()["account_id"]
    login_response = client.post("/auth/web/login", headers={"Origin": "https://app.example.com"}, json=payload)
    old_cookie = login_response.headers["set-cookie"].split(";", 1)[0]
    headers = {"Origin": "https://app.example.com", "Cookie": old_cookie, "X-CSRF-Token": login_response.json()["csrf_token"]}
    assert client.post("/auth/web/refresh", headers={**headers, "Origin": "https://evil.example.com"}).status_code == 403
    assert client.post("/auth/web/refresh", headers={**headers, "X-CSRF-Token": "invalid"}).status_code == 403
    db = app.dependency_overrides[get_session]()
    stored = db.scalar(select(LoginSession).where(LoginSession.account_id == uuid.UUID(account_id)))
    expiry = datetime.now(timezone.utc) + timedelta(minutes=30)
    stored.started_at = expiry - timedelta(hours=24)
    stored.expires_at = expiry
    db.commit()
    response = client.post("/auth/web/refresh", headers=headers)
    assert response.status_code == 200
    assert set(response.json()) == {"access_token", "expires_in", "token_type"}
    claims = jwt.decode(response.json()["access_token"], os.environ["JWT_PUBLIC_KEY"], algorithms=["RS256"], issuer="identity-test", audience="services-test")
    assert claims["exp"] <= int(expiry.timestamp())
    assert response.headers["cache-control"] == "no-store"
    new_cookie = response.headers["set-cookie"].split(";", 1)[0]
    assert new_cookie != old_cookie
    assert client.post("/auth/web/refresh", headers=headers).status_code == 401
    assert client.post("/auth/web/refresh", headers={**headers, "Cookie": new_cookie}).status_code == 401


def test_web_logout_requires_protection_and_revokes_session(client, monkeypatch):
    monkeypatch.setenv("IDENTITY_ENV", "production")
    monkeypatch.setenv("IDENTITY_WEB_ORIGINS", "https://app.example.com")
    monkeypatch.setenv("IDENTITY_WEB_CSRF_SECRET", "x" * 32)
    monkeypatch.delenv("IDENTITY_WEB_ALLOW_LOCAL_HTTP", raising=False)
    payload = {"email": f"{uuid.uuid4()}@example.com", "password": "password123", "role": "cliente"}
    assert client.post("/auth/register", json=payload).status_code == 201
    logged_in = client.post("/auth/web/login", headers={"Origin": "https://app.example.com"}, json=payload)
    cookie = logged_in.headers["set-cookie"].split(";", 1)[0]
    headers = {"Origin": "https://app.example.com", "Cookie": cookie, "X-CSRF-Token": logged_in.json()["csrf_token"]}
    bad_origin = client.post("/auth/web/logout", headers={**headers, "Origin": "https://evil.example.com"})
    assert bad_origin.status_code == 403 and "set-cookie" not in bad_origin.headers
    bad_csrf = client.post("/auth/web/logout", headers={**headers, "X-CSRF-Token": "invalid"})
    assert bad_csrf.status_code == 403 and "set-cookie" not in bad_csrf.headers
    assert client.get("/auth/web/csrf", headers={"Cookie": cookie}).status_code == 200
    logout_response = client.post("/auth/web/logout", headers=headers)
    assert logout_response.status_code == 204 and logout_response.content == b""
    deleted_cookie = logout_response.headers["set-cookie"]
    assert "Max-Age=0" in deleted_cookie and "Path=/auth/web" in deleted_cookie
    assert "HttpOnly" in deleted_cookie and "Secure" in deleted_cookie and "SameSite=strict" in deleted_cookie
    assert "Domain=" not in deleted_cookie
    assert logout_response.headers["cache-control"] == "no-store"
    assert client.post("/auth/web/refresh", headers=headers).status_code == 401


def test_concurrent_web_refresh_revokes_session(client, monkeypatch):
    monkeypatch.setenv("IDENTITY_ENV", "production")
    monkeypatch.setenv("IDENTITY_WEB_ORIGINS", "https://app.example.com")
    monkeypatch.setenv("IDENTITY_WEB_CSRF_SECRET", "x" * 32)
    monkeypatch.delenv("IDENTITY_WEB_ALLOW_LOCAL_HTTP", raising=False)
    engine = create_engine(os.environ["IDENTITY_TEST_DATABASE_URL"])
    email = f"{uuid.uuid4()}@example.com"
    with Session(engine) as db:
        account = create_account(db, email, "password123")
        account_id = account.id
        db.add(RoleAssignment(account_id=account_id, role="cliente", status="activo"))
        db.commit()
        token = login(Login(email=email, password="password123"), db)["refresh_token"]
        stored = db.scalar(select(LoginSession).where(LoginSession.account_id == account_id))
        csrf = csrf_for_session(b"x" * 32, stored.id)
    barrier = Barrier(2)

    def attempt():
        headers = [(b"origin", b"https://app.example.com"), (b"cookie", f"identity_refresh={token}".encode()), (b"x-csrf-token", csrf.encode())]
        request = Request({"type": "http", "method": "POST", "path": "/auth/web/refresh", "headers": headers})
        with Session(engine) as db:
            barrier.wait(timeout=10)
            try:
                web_refresh(request, Response(), db)
                return True
            except HTTPException as exc:
                assert exc.status_code == 401
                return False

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            assert sorted(executor.map(lambda _: attempt(), range(2))) == [False, True]
        with Session(engine) as db:
            assert db.scalar(select(LoginSession).where(LoginSession.account_id == account_id)).revoked
    finally:
        with Session(engine) as db:
            ids = select(LoginSession.id).where(LoginSession.account_id == account_id)
            db.execute(delete(RefreshCredential).where(RefreshCredential.session_id.in_(ids)))
            db.execute(delete(LoginSession).where(LoginSession.account_id == account_id))
            db.execute(delete(RoleAssignment).where(RoleAssignment.account_id == account_id))
            db.execute(delete(Account).where(Account.id == account_id))
            db.commit()
        engine.dispose()


@pytest.mark.parametrize("invalid_claim", ["signature", "issuer", "audience", "expired"])
def test_rejects_untrusted_access_token(client, invalid_claim):
    now = datetime.now(timezone.utc)
    registration = client.post("/auth/register", json={"email": f"{uuid.uuid4()}@example.com", "password": "password123", "role": "cliente"})
    assert registration.status_code == 201
    claims = {"sub": registration.json()["account_id"], "iss": "identity-test", "aud": "services-test", "iat": now, "exp": now + timedelta(minutes=10)}
    key = os.environ["JWT_PRIVATE_KEY"]
    if invalid_claim == "signature":
        other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        key = other.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode()
    elif invalid_claim == "issuer":
        claims["iss"] = "wrong"
    elif invalid_claim == "audience":
        claims["aud"] = "wrong"
    else:
        claims["exp"] = now - timedelta(seconds=1)
    token = jwt.encode(claims, key, algorithm="RS256")
    response = client.post("/auth/me/roles", headers={"Authorization": f"Bearer {token}"}, json={"role": "cliente"})
    assert response.status_code == 401


def test_pending_organizer_can_login_and_request_client_role(client):
    payload = {"email": f"{uuid.uuid4()}@example.com", "password": "password123", "role": "organizador"}
    assert client.post("/auth/register", json=payload).status_code == 201
    response = client.post("/auth/login", json={"email": payload["email"], "password": payload["password"]})
    assert response.status_code == 200
    headers = {"Authorization": f"Bearer {response.json()['access_token']}"}
    roles = client.post("/auth/me/roles", headers=headers, json={"role": "cliente"})
    assert roles.status_code == 200
    assert {item["role"]: item["status"] for item in roles.json()["roles"]} == {"cliente": "activo", "organizador": "pendiente"}


def test_roles_are_returned_in_stable_order(client, monkeypatch):
    monkeypatch.setenv("SERVICE_CREDENTIALS_JSON", json.dumps({"events": {"token": "events-secret", "roles_read": True}}))
    payload = {"email": f"{uuid.uuid4()}@example.com", "password": "password123", "role": "organizador"}
    account_id = client.post("/auth/register", json=payload).json()["account_id"]
    access = client.post("/auth/login", json={"email": payload["email"], "password": payload["password"]}).json()["access_token"]
    user_headers = {"Authorization": f"Bearer {access}"}
    roles_response = client.post("/auth/me/roles", headers=user_headers, json={"role": "cliente"})
    me = client.get("/auth/me", headers=user_headers)
    internal = client.get(f"/internal/accounts/{account_id}/roles", headers={"X-Service-Id": "events", "X-Service-Token": "events-secret"})
    for response in (roles_response, me, internal):
        assert response.status_code == 200
        assert [role["role"] for role in response.json()["roles"]] == ["cliente", "organizador"]


def test_get_me_requires_authentication_and_omits_password(client):
    payload = {"email": f"{uuid.uuid4()}@example.com", "password": "password123", "role": "cliente"}
    registered = client.post("/auth/register", json=payload).json()
    assert client.get("/auth/me").status_code == 401
    token = client.post("/auth/login", json={"email": payload["email"], "password": payload["password"]}).json()["access_token"]
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json() == {"account_id": registered["account_id"], "email": payload["email"], "roles": [{"role": "cliente", "status": "activo"}]}


def test_initialize_and_recover_admin(client):
    db = app.dependency_overrides[get_session]()
    email = f"{uuid.uuid4()}@example.com"
    assert initialize_admin(db, email, "first-password") is True
    db.commit()
    assert initialize_admin(db, email, "another-password") is False
    db.commit()
    old_login = client.post("/auth/login", json={"email": email, "password": "first-password"})
    assert old_login.status_code == 200
    second_login = client.post("/auth/login", json={"email": email, "password": "first-password"})
    assert second_login.status_code == 200
    user_email = f"{uuid.uuid4()}@example.com"
    assert client.post("/auth/register", json={"email": user_email, "password": "user-password", "role": "cliente"}).status_code == 201
    user_login = client.post("/auth/login", json={"email": user_email, "password": "user-password"})
    assert user_login.status_code == 200
    assert client.post("/auth/login", json={"email": email, "password": "another-password"}).status_code == 401
    recover_admin(db, email, "recovered-password")
    db.commit()
    assert client.post("/auth/refresh", json={"refresh_token": old_login.json()["refresh_token"]}).status_code == 401
    assert client.post("/auth/refresh", json={"refresh_token": second_login.json()["refresh_token"]}).status_code == 401
    assert client.post("/auth/refresh", json={"refresh_token": user_login.json()["refresh_token"]}).status_code == 200
    assert client.post("/auth/login", json={"email": email, "password": "first-password"}).status_code == 401
    assert client.post("/auth/login", json={"email": email, "password": "recovered-password"}).status_code == 200


def test_admin_lists_organizers_with_minimal_data_and_stable_order(client):
    db = app.dependency_overrides[get_session]()
    email = f"{uuid.uuid4()}@example.com"
    assert initialize_admin(db, email, "admin-password") is True
    db.commit()
    token = client.post("/auth/login", json={"email": email, "password": "admin-password"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    assert client.get("/admin/organizers", headers=headers).json() == []
    expected = []
    for status in ("pendiente", "habilitado", "deshabilitado"):
        address = f"{uuid.uuid4()}@example.com"
        account = create_account(db, address, "password123")
        db.add(RoleAssignment(account_id=account.id, role="organizador", status=status))
        db.flush()
        expected.append({"account_id": str(account.id), "email": address, "status": status})
    db.commit()
    response = client.get("/admin/organizers", headers=headers)
    assert response.status_code == 200
    assert response.json() == sorted(expected, key=lambda item: (item["email"], item["account_id"]))


def test_admin_list_rejects_invalid_and_revoked_authority(client):
    db = app.dependency_overrides[get_session]()
    email = f"{uuid.uuid4()}@example.com"
    assert initialize_admin(db, email, "admin-password") is True
    db.commit()
    token = client.post("/auth/login", json={"email": email, "password": "admin-password"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    assert client.get("/admin/organizers").status_code == 401
    assert client.get("/admin/organizers", headers={"Authorization": "Bearer invalid"}).status_code == 401
    user_email = f"{uuid.uuid4()}@example.com"
    client.post("/auth/register", json={"email": user_email, "password": "password123", "role": "cliente"})
    user_token = client.post("/auth/login", json={"email": user_email, "password": "password123"}).json()["access_token"]
    assert client.get("/admin/organizers", headers={"Authorization": f"Bearer {user_token}"}).status_code == 403
    role = db.scalar(select(RoleAssignment).where(RoleAssignment.role == "administrador"))
    role.status = "deshabilitado"
    db.commit()
    assert client.get("/admin/organizers", headers=headers).status_code == 403


def test_admin_changes_organizer_without_affecting_client(client):
    db = app.dependency_overrides[get_session]()
    email = f"{uuid.uuid4()}@example.com"
    initialize_admin(db, email, "admin-password")
    db.commit()
    admin_token = client.post("/auth/login", json={"email": email, "password": "admin-password"}).json()["access_token"]
    payload = {"email": f"{uuid.uuid4()}@example.com", "password": "password123", "role": "cliente"}
    account_id = client.post("/auth/register", json=payload).json()["account_id"]
    token = client.post("/auth/login", json={"email": payload["email"], "password": payload["password"]}).json()["access_token"]
    user_headers = {"Authorization": f"Bearer {token}"}
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    assert client.post("/auth/me/roles", headers=user_headers, json={"role": "organizador"}).status_code == 200
    path = f"/admin/organizers/{account_id}/status"
    assert client.patch(path, headers=user_headers, json={"status": "habilitado"}).status_code == 403
    for status in ("habilitado", "deshabilitado", "habilitado"):
        result = client.patch(path, headers=admin_headers, json={"status": status})
        assert result.status_code == 200
        assert result.json()["status"] == status
        me = client.get("/auth/me", headers=user_headers).json()
        assert {role["role"]: role["status"] for role in me["roles"]} == {"cliente": "activo", "organizador": status}
    assert client.patch(f"/admin/organizers/{uuid.uuid4()}/status", headers=admin_headers, json={"status": "habilitado"}).status_code == 404


def test_service_roles_authentication_and_current_state(client, monkeypatch):
    monkeypatch.setenv("SERVICE_CREDENTIALS_JSON", json.dumps({
        "events": {"token": "events-secret", "roles_read": True},
        "purchases": {"token": "purchases-secret", "roles_read": True},
        "other": {"token": "other-secret", "roles_read": False},
    }))
    db = app.dependency_overrides[get_session]()
    admin_email = f"{uuid.uuid4()}@example.com"
    initialize_admin(db, admin_email, "admin-password")
    db.commit()
    admin_token = client.post("/auth/login", json={"email": admin_email, "password": "admin-password"}).json()["access_token"]
    payload = {"email": f"{uuid.uuid4()}@example.com", "password": "password123", "role": "organizador"}
    account_id = client.post("/auth/register", json=payload).json()["account_id"]
    assert client.post("/auth/login", json={"email": payload["email"], "password": payload["password"]}).status_code == 200
    path = f"/internal/accounts/{account_id}/roles"
    headers = {"X-Service-Id": "events", "X-Service-Token": "events-secret"}
    assert client.get(path).status_code == 401
    assert client.get(path, headers={"X-Service-Id": "events", "X-Service-Token": "purchases-secret"}).status_code == 401
    assert client.get(path, headers={"X-Service-Id": "other", "X-Service-Token": "other-secret"}).status_code == 403
    assert client.get(f"/internal/accounts/{uuid.uuid4()}/roles", headers=headers).status_code == 404
    assert client.get(path, headers=headers).json()["roles"] == [{"role": "organizador", "status": "pendiente"}]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    assert client.patch(f"/admin/organizers/{account_id}/status", headers=admin_headers, json={"status": "deshabilitado"}).status_code == 200
    result = client.get(path, headers=headers)
    assert result.status_code == 200
    assert result.json()["roles"] == [{"role": "organizador", "status": "deshabilitado"}]
    assert client.get(path, headers={"X-Service-Id": "purchases", "X-Service-Token": "purchases-secret"}).status_code == 200


def test_refresh_rotation_replay_revokes_session(client):
    payload = {"email": f"{uuid.uuid4()}@example.com", "password": "password123", "role": "cliente"}
    assert client.post("/auth/register", json=payload).status_code == 201
    login = client.post("/auth/login", json={"email": payload["email"], "password": payload["password"]})
    first = login.json()["refresh_token"]
    response = client.post("/auth/refresh", json={"refresh_token": first})
    assert response.status_code == 200
    second = response.json()["refresh_token"]
    assert second != first
    assert client.post("/auth/refresh", json={"refresh_token": first}).status_code == 401
    assert client.post("/auth/refresh", json={"refresh_token": second}).status_code == 401


def test_logout_revokes_refresh(client):
    payload = {"email": f"{uuid.uuid4()}@example.com", "password": "password123", "role": "cliente"}
    assert client.post("/auth/register", json=payload).status_code == 201
    login = client.post("/auth/login", json={"email": payload["email"], "password": payload["password"]})
    token = login.json()["refresh_token"]
    assert client.post("/auth/logout", json={"refresh_token": token}).status_code == 204
    assert client.post("/auth/refresh", json={"refresh_token": token}).status_code == 401
    assert client.post("/auth/logout", json={"refresh_token": token}).status_code == 401


def test_refresh_rejects_account_without_access(client):
    payload = {"email": f"{uuid.uuid4()}@example.com", "password": "password123", "role": "organizador"}
    account_id = client.post("/auth/register", json=payload).json()["account_id"]
    token = client.post("/auth/login", json={"email": payload["email"], "password": payload["password"]}).json()["refresh_token"]
    db = app.dependency_overrides[get_session]()
    role = db.scalar(select(RoleAssignment).where(RoleAssignment.account_id == uuid.UUID(account_id)))
    role.status = "deshabilitado"
    db.commit()
    assert client.post("/auth/refresh", json={"refresh_token": token}).status_code == 401


@pytest.mark.parametrize("minutes_remaining", [30, -1])
def test_refresh_respects_absolute_session_limit(client, minutes_remaining):
    payload = {"email": f"{uuid.uuid4()}@example.com", "password": "password123", "role": "cliente"}
    account_id = client.post("/auth/register", json=payload).json()["account_id"]
    token = client.post("/auth/login", json={"email": payload["email"], "password": payload["password"]}).json()["refresh_token"]
    db = app.dependency_overrides[get_session]()
    stored = db.scalar(select(LoginSession).where(LoginSession.account_id == uuid.UUID(account_id)))
    expiry = datetime.now(timezone.utc) + timedelta(minutes=minutes_remaining)
    stored.started_at = expiry - timedelta(hours=24)
    stored.expires_at = expiry
    db.commit()
    response = client.post("/auth/refresh", json={"refresh_token": token})
    if minutes_remaining < 0:
        assert response.status_code == 401
    else:
        assert response.status_code == 200
        claims = jwt.decode(response.json()["access_token"], os.environ["JWT_PUBLIC_KEY"], algorithms=["RS256"], issuer="identity-test", audience="services-test")
        assert claims["exp"] <= int(expiry.timestamp())
        assert 0 < response.json()["expires_in"] <= 1800


def test_concurrent_refresh_revokes_session(client):
    engine = create_engine(os.environ["IDENTITY_TEST_DATABASE_URL"])
    email = f"{uuid.uuid4()}@example.com"
    with Session(engine) as db:
        account = create_account(db, email, "password123")
        account_id = account.id
        db.add(RoleAssignment(account_id=account_id, role="cliente", status="activo"))
        db.commit()
        token = login(Login(email=email, password="password123"), db)["refresh_token"]

    barrier = Barrier(2)

    def attempt():
        with Session(engine) as db:
            barrier.wait(timeout=10)
            try:
                return refresh(RefreshRequest(refresh_token=token), db)["refresh_token"]
            except HTTPException as exc:
                assert exc.status_code == 401
                return None

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda _: attempt(), range(2)))
        assert sum(result is not None for result in results) == 1
        with Session(engine) as db:
            stored = db.scalar(select(LoginSession).where(LoginSession.account_id == account_id))
            assert stored.revoked is True
            with pytest.raises(HTTPException):
                refresh(RefreshRequest(refresh_token=next(value for value in results if value)), db)
    finally:
        with Session(engine) as db:
            ids = select(LoginSession.id).where(LoginSession.account_id == account_id)
            db.execute(delete(RefreshCredential).where(RefreshCredential.session_id.in_(ids)))
            db.execute(delete(LoginSession).where(LoginSession.account_id == account_id))
            db.execute(delete(RoleAssignment).where(RoleAssignment.account_id == account_id))
            db.execute(delete(Account).where(Account.id == account_id))
            db.commit()
        engine.dispose()


def test_http_contract_success_and_error_responses(client, monkeypatch):
    monkeypatch.setenv("SERVICE_CREDENTIALS_JSON", json.dumps({
        "events": {"token": "service-secret", "roles_read": True},
        "denied": {"token": "denied-secret", "roles_read": False},
    }))
    email = f"{uuid.uuid4()}@example.com"
    payload = {"email": email, "password": "password123", "role": "cliente"}
    registered = client.post("/auth/register", json=payload)
    assert registered.status_code == 201
    assert set(registered.json()) == {"account_id", "email", "roles"}
    account_id = registered.json()["account_id"]

    duplicate = client.post("/auth/register", json=payload)
    assert duplicate.status_code == 409
    assert set(duplicate.json()) == {"code", "message"}
    bad_input = client.post("/auth/register", json={"email": email})
    assert bad_input.status_code == 400
    assert set(bad_input.json()) == {"code", "message"}
    wrong_login = client.post("/auth/login", json={"email": email, "password": "wrong"})
    missing_login = client.post("/auth/login", json={"email": f"{uuid.uuid4()}@example.com", "password": "wrong"})
    assert wrong_login.status_code == missing_login.status_code == 401
    assert wrong_login.json() == missing_login.json()

    login_response = client.post("/auth/login", json={"email": email, "password": payload["password"]})
    assert login_response.status_code == 200
    tokens = login_response.json()
    assert set(tokens) == {"access_token", "refresh_token", "token_type", "expires_in"}
    assert tokens["token_type"] == "Bearer"
    assert isinstance(tokens["expires_in"], int) and 0 < tokens["expires_in"] <= 3600
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    assert client.get("/auth/me").status_code == 401
    assert set(client.get("/auth/me", headers=headers).json()) == {"account_id", "email", "roles"}
    assert client.post("/auth/me/roles", headers=headers, json={"role": "invalid"}).status_code == 400
    added = client.post("/auth/me/roles", headers=headers, json={"role": "organizador"})
    assert added.status_code == 200 and set(added.json()) == {"roles"}
    assert client.post("/auth/me/roles", headers=headers, json={"role": "organizador"}).status_code == 409

    admin_path = f"/admin/organizers/{account_id}/status"
    assert client.patch(admin_path, json={"status": "habilitado"}).status_code == 401
    assert client.patch(admin_path, headers=headers, json={"status": "habilitado"}).status_code == 403
    assert client.patch(admin_path, headers=headers, json={"status": "invalid"}).status_code == 400
    internal_path = f"/internal/accounts/{account_id}/roles"
    service = {"X-Service-Id": "events", "X-Service-Token": "service-secret"}
    assert client.get(internal_path).status_code == 401
    assert client.get(internal_path, headers={"X-Service-Id": "denied", "X-Service-Token": "denied-secret"}).status_code == 403
    internal = client.get(internal_path, headers=service)
    assert internal.status_code == 200 and set(internal.json()) == {"account_id", "roles"}
    assert client.get(f"/internal/accounts/{uuid.uuid4()}/roles", headers=service).status_code == 404

    assert client.post("/auth/refresh", json={}).status_code == 400
    assert client.post("/auth/refresh", json={"refresh_token": "unknown"}).status_code == 401
    rotated = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert rotated.status_code == 200
    assert set(rotated.json()) == {"access_token", "refresh_token", "token_type", "expires_in"}
    fresh = rotated.json()["refresh_token"]
    assert client.post("/auth/logout", json={}).status_code == 400
    assert client.post("/auth/logout", json={"refresh_token": "unknown"}).status_code == 401
    logout_response = client.post("/auth/logout", json={"refresh_token": fresh})
    assert logout_response.status_code == 204 and logout_response.content == b""
    assert client.post("/auth/refresh", json={"refresh_token": fresh}).status_code == 401
