import os
from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt


def issue_access_token(account_id: UUID, session_id: UUID, session_expiry: datetime) -> tuple[str, int]:
    now = datetime.now(timezone.utc)
    expires_at = min(now + timedelta(hours=1), session_expiry)
    expires_in = int((expires_at - now).total_seconds())
    if expires_in <= 0:
        raise ValueError("Session expired")
    token = jwt.encode(
        {"sub": str(account_id), "sid": str(session_id), "iss": os.environ["JWT_ISSUER"], "aud": os.environ["JWT_AUDIENCE"], "iat": now, "exp": expires_at},
        os.environ["JWT_PRIVATE_KEY"],
        algorithm="RS256",
    )
    return token, expires_in


def verify_access_token(token: str) -> tuple[UUID, UUID]:
    claims = jwt.decode(
        token,
        os.environ["JWT_PUBLIC_KEY"],
        algorithms=["RS256"],
        issuer=os.environ["JWT_ISSUER"],
        audience=os.environ["JWT_AUDIENCE"],
        options={"require": ["sub", "sid", "iss", "aud", "exp", "iat"]},
    )
    if not isinstance(claims["sub"], str) or not isinstance(claims["sid"], str):
        raise ValueError("Invalid token claims")
    return UUID(claims["sub"]), UUID(claims["sid"])
