import asyncio
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException

from app import identity
from app.identity_config import IdentityConfig


@pytest.fixture
def identity_case(monkeypatch):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public = (
        key.public_key()
        .public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
        )
        .decode()
    )
    config = IdentityConfig(
        "https://identity.test", public, "issuer", "audience", "purchases", "secret"
    )
    monkeypatch.setattr(identity, "load_identity_config", lambda: config)
    account = uuid4()
    now = datetime.now(timezone.utc)
    claims = {
        "sub": str(account),
        "sid": str(uuid4()),
        "iss": "issuer",
        "aud": "audience",
        "iat": now,
        "exp": now + timedelta(minutes=10),
    }
    return key, account, claims


@pytest.mark.parametrize(
    ("session_status", "session_code", "status", "expected"),
    [
        (200, None, "activo", 200),
        (200, None, "deshabilitado", 403),
        (401, "invalid_credentials", "activo", 401),
        (401, "invalid_service_credentials", "activo", 503),
        (403, "forbidden", "activo", 503),
    ],
)
def test_customer_session_and_role(
    identity_case, monkeypatch, session_status, session_code, status, expected
):
    key, account, claims = identity_case

    def handle(request):
        assert request.headers["X-Service-Id"] == "purchases"
        assert request.headers["X-Service-Token"] == "secret"
        if request.url.path.endswith("/verify"):
            body = {"account_id": str(account), "code": session_code}
            return httpx.Response(session_status, json=body)
        body = {
            "account_id": str(account),
            "roles": [{"role": "cliente", "status": status}],
        }
        return httpx.Response(200, json=body)

    real_client = httpx.AsyncClient
    monkeypatch.setattr(
        identity.httpx,
        "AsyncClient",
        lambda **kwargs: real_client(transport=httpx.MockTransport(handle), **kwargs),
    )
    token = jwt.encode(claims, key, algorithm="RS256")
    if expected == 200:
        assert asyncio.run(identity.authorized_customer(token)) == account
    else:
        with pytest.raises(HTTPException) as error:
            asyncio.run(identity.authorized_customer(token))
        assert error.value.status_code == expected


@pytest.mark.parametrize("change", ["expired", "issuer", "missing_sid", "signature"])
def test_invalid_token_rejected_without_network(identity_case, monkeypatch, change):
    key, _, claims = identity_case
    if change == "expired":
        claims["exp"] = datetime.now(timezone.utc) - timedelta(seconds=1)
    elif change == "issuer":
        claims["iss"] = "wrong"
    elif change == "missing_sid":
        del claims["sid"]
    else:
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    monkeypatch.setattr(
        identity.httpx, "AsyncClient", lambda **kwargs: pytest.fail("network called")
    )
    token = jwt.encode(claims, key, algorithm="RS256")
    with pytest.raises(HTTPException) as error:
        asyncio.run(identity.authorized_customer(token))
    assert error.value.status_code == 401


def test_identity_timeout_fails_closed(identity_case, monkeypatch):
    key, _, claims = identity_case

    def handle(request):
        raise httpx.ReadTimeout("sensitive details", request=request)

    real_client = httpx.AsyncClient
    monkeypatch.setattr(
        identity.httpx,
        "AsyncClient",
        lambda **kwargs: real_client(transport=httpx.MockTransport(handle), **kwargs),
    )
    token = jwt.encode(claims, key, algorithm="RS256")
    with pytest.raises(HTTPException) as error:
        asyncio.run(identity.authorized_customer(token))
    assert error.value.status_code == 503
    assert token not in str(error.value.detail)
    assert "secret" not in str(error.value.detail)


@pytest.mark.parametrize(
    "response_kind", ["missing_role", "wrong_account", "bad_roles"]
)
def test_customer_roles_are_checked_fail_closed(
    identity_case, monkeypatch, response_kind
):
    key, account, claims = identity_case

    def handle(request):
        if request.url.path.endswith("/verify"):
            return httpx.Response(200, json={"account_id": str(account)})
        body = {"account_id": str(account), "roles": []}
        if response_kind == "wrong_account":
            body["account_id"] = str(uuid4())
        elif response_kind == "bad_roles":
            body["roles"] = "invalid"
        return httpx.Response(200, json=body)

    real_client = httpx.AsyncClient
    monkeypatch.setattr(
        identity.httpx,
        "AsyncClient",
        lambda **kwargs: real_client(transport=httpx.MockTransport(handle), **kwargs),
    )
    token = jwt.encode(claims, key, algorithm="RS256")
    with pytest.raises(HTTPException) as error:
        asyncio.run(identity.authorized_customer(token))
    assert error.value.status_code == (403 if response_kind == "missing_role" else 503)
