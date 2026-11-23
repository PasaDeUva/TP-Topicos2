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
        "https://identity.test", public, "issuer", "audience", "events", "secret"
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


def test_organizer_requires_current_session_and_role(identity_case, monkeypatch):
    key, account, claims = identity_case
    calls = []

    def handle(request):
        calls.append(request)
        assert request.headers["X-Service-Id"] == "events"
        assert request.headers["X-Service-Token"] == "secret"
        if request.url.path.endswith("/verify"):
            return httpx.Response(200, json={"account_id": str(account)})
        return httpx.Response(
            200,
            json={
                "account_id": str(account),
                "roles": [{"role": "organizador", "status": "habilitado"}],
            },
        )

    real_client = httpx.AsyncClient
    monkeypatch.setattr(
        identity.httpx,
        "AsyncClient",
        lambda **kwargs: real_client(transport=httpx.MockTransport(handle), **kwargs),
    )
    token = jwt.encode(claims, key, algorithm="RS256")
    assert asyncio.run(identity.authorized_organizer(token)) == account
    assert len(calls) == 2


@pytest.mark.parametrize("change", ["expired", "issuer", "missing_sid", "signature"])
def test_invalid_token_is_rejected_before_network(identity_case, monkeypatch, change):
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
    with pytest.raises(HTTPException) as error:
        asyncio.run(
            identity.authorized_organizer(jwt.encode(claims, key, algorithm="RS256"))
        )
    assert error.value.status_code == 401


@pytest.mark.parametrize(
    ("session_status", "session_body", "role_body", "expected"),
    [
        (401, {"code": "invalid_credentials"}, None, 401),
        (401, {"code": "invalid_service_credentials"}, None, 503),
        (403, {}, None, 503),
        (200, {"account_id": "bad"}, None, 503),
        (200, None, {"account_id": "bad", "roles": []}, 503),
        (200, None, {"roles": "invalid"}, 503),
        (200, None, {"roles": [{"role": "organizador", "status": "pendiente"}]}, 403),
        (
            200,
            None,
            {"roles": [{"role": "organizador", "status": "deshabilitado"}]},
            403,
        ),
    ],
)
def test_identity_failure_and_role_states(
    identity_case, monkeypatch, session_status, session_body, role_body, expected
):
    key, account, claims = identity_case

    def handle(request):
        if request.url.path.endswith("/verify"):
            return httpx.Response(
                session_status, json=session_body or {"account_id": str(account)}
            )
        return httpx.Response(200, json={"account_id": str(account), **role_body})

    real_client = httpx.AsyncClient
    monkeypatch.setattr(
        identity.httpx,
        "AsyncClient",
        lambda **kwargs: real_client(transport=httpx.MockTransport(handle), **kwargs),
    )
    with pytest.raises(HTTPException) as error:
        asyncio.run(
            identity.authorized_organizer(jwt.encode(claims, key, algorithm="RS256"))
        )
    assert error.value.status_code == expected


def test_identity_timeout_fails_closed_without_exposing_tokens(
    identity_case, monkeypatch
):
    key, _, claims = identity_case
    token = jwt.encode(claims, key, algorithm="RS256")

    def handle(request):
        raise httpx.ReadTimeout("sensitive details", request=request)

    real_client = httpx.AsyncClient
    monkeypatch.setattr(
        identity.httpx,
        "AsyncClient",
        lambda **kwargs: real_client(transport=httpx.MockTransport(handle), **kwargs),
    )
    with pytest.raises(HTTPException) as error:
        asyncio.run(identity.authorized_organizer(token))
    assert error.value.status_code == 503
    assert token not in str(error.value.detail)
    assert "secret" not in str(error.value.detail)


def test_conflicting_duplicate_roles_fail_closed(identity_case, monkeypatch):
    key, account, claims = identity_case

    def handle(request):
        if request.url.path.endswith("/verify"):
            return httpx.Response(200, json={"account_id": str(account)})
        return httpx.Response(
            200,
            json={
                "account_id": str(account),
                "roles": [
                    {"role": "organizador", "status": "habilitado"},
                    {"role": "organizador", "status": "deshabilitado"},
                ],
            },
        )

    real_client = httpx.AsyncClient
    monkeypatch.setattr(
        identity.httpx,
        "AsyncClient",
        lambda **kwargs: real_client(transport=httpx.MockTransport(handle), **kwargs),
    )
    with pytest.raises(HTTPException) as error:
        token = jwt.encode(claims, key, algorithm="RS256")
        asyncio.run(identity.authorized_organizer(token))
    assert error.value.status_code == 503
