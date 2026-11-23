from uuid import UUID

import httpx
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.identity_config import IdentityConfig, load_identity_config

bearer = HTTPBearer(auto_error=False)


async def current_organizer(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> UUID:
    if credentials is None:
        raise HTTPException(status_code=401, detail="invalid credentials")
    return await authorized_organizer(credentials.credentials)


def _unavailable() -> HTTPException:
    return HTTPException(status_code=503, detail="identity unavailable")


def _account_id(token: str, config: IdentityConfig) -> UUID:
    try:
        claims = jwt.decode(
            token,
            config.public_key,
            algorithms=["RS256"],
            issuer=config.issuer,
            audience=config.audience,
            options={"require": ["sub", "sid", "iss", "aud", "exp", "iat"]},
        )
        if not isinstance(claims["sub"], str) or not isinstance(claims["sid"], str):
            raise ValueError("invalid claims")
        UUID(claims["sid"])
        return UUID(claims["sub"])
    except (jwt.InvalidTokenError, ValueError, TypeError):
        raise HTTPException(status_code=401, detail="invalid credentials") from None


async def authorized_organizer(token: str) -> UUID:
    if not token:
        raise HTTPException(status_code=401, detail="invalid credentials")
    try:
        config = load_identity_config()
    except ValueError:
        raise _unavailable() from None
    account_id = _account_id(token, config)
    headers = {
        "X-Service-Id": config.service_id,
        "X-Service-Token": config.service_token,
    }
    try:
        async with httpx.AsyncClient(
            base_url=config.identity_url,
            timeout=config.timeout_seconds,
            follow_redirects=False,
            trust_env=False,
        ) as client:
            session = await client.post(
                "/internal/sessions/verify",
                headers=headers,
                json={"access_token": token},
            )
            if (
                session.status_code == 401
                and session.json().get("code") == "invalid_credentials"
            ):
                raise HTTPException(status_code=401, detail="invalid credentials")
            if (
                session.status_code != 200
                or UUID(session.json()["account_id"]) != account_id
            ):
                raise _unavailable()
            roles = await client.get(
                f"/internal/accounts/{account_id}/roles", headers=headers
            )
            if roles.status_code != 200:
                raise _unavailable()
            data = roles.json()
            if UUID(data["account_id"]) != account_id or not isinstance(
                data["roles"], list
            ):
                raise _unavailable()
            entries = data["roles"]
            if any(
                not isinstance(role, dict)
                or not isinstance(role.get("role"), str)
                or not isinstance(role.get("status"), str)
                for role in entries
            ):
                raise _unavailable()
            if len({role["role"] for role in entries}) != len(entries):
                raise _unavailable()
    except (httpx.HTTPError, ValueError, TypeError, KeyError, AttributeError):
        raise _unavailable() from None
    if not any(
        role["role"] == "organizador" and role["status"] == "habilitado"
        for role in entries
    ):
        raise HTTPException(status_code=403, detail="forbidden")
    return account_id
