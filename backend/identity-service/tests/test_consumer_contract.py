"""Contract checks using a representative consumer, without integrating services."""

import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa


def may_organize(token, public_key, account_response):
    try:
        claims = jwt.decode(token, public_key, algorithms=["RS256"], issuer="identity", audience="platform", options={"require": ["sub", "iss", "aud", "exp", "iat"]})
        account_id = str(uuid.UUID(claims["sub"]))
        data = account_response()
        return data["account_id"] == account_id and any(
            role["role"] == "organizador" and role["status"] == "habilitado"
            for role in data["roles"]
        )
    except (jwt.InvalidTokenError, KeyError, TypeError, ValueError, ConnectionError):
        return False


def test_consumer_rejects_disabled_or_unverifiable_roles():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    account_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    claims = {"sub": account_id, "iss": "identity", "aud": "platform", "iat": now, "exp": now + timedelta(minutes=10)}
    token = jwt.encode(claims, key, algorithm="RS256")
    roles = {"account_id": account_id, "roles": [{"role": "organizador", "status": "habilitado"}]}
    assert may_organize(token, key.public_key(), lambda: roles)
    roles["roles"][0]["status"] = "deshabilitado"
    assert not may_organize(token, key.public_key(), lambda: roles)
    assert not may_organize(token, key.public_key(), lambda: {})

    def unavailable():
        raise ConnectionError("Identity unavailable")

    assert not may_organize(token, key.public_key(), unavailable)


@pytest.mark.parametrize("fault", ["signature", "algorithm", "issuer", "audience", "expired"])
def test_consumer_rejects_invalid_jwt(fault):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    account_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    claims = {"sub": account_id, "iss": "identity", "aud": "platform", "iat": now, "exp": now + timedelta(minutes=10)}
    signing_key = key
    algorithm = "RS256"
    if fault == "signature":
        signing_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    elif fault == "algorithm":
        signing_key = "untrusted-secret"
        algorithm = "HS256"
    elif fault == "issuer":
        claims["iss"] = "other"
    elif fault == "audience":
        claims["aud"] = "other"
    else:
        claims["exp"] = now - timedelta(seconds=1)
    token = jwt.encode(claims, signing_key, algorithm=algorithm)
    response = {"account_id": account_id, "roles": [{"role": "organizador", "status": "habilitado"}]}
    assert not may_organize(token, key.public_key(), lambda: response)
