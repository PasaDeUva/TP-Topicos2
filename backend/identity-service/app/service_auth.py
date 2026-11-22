import json
import os
import secrets

from fastapi import Header, HTTPException


def _authorize_service(x_service_id: str | None, x_service_token: str | None, permission: str) -> None:
    if not x_service_id or not x_service_token:
        raise HTTPException(status_code=401, detail="invalid_service_credentials")
    try:
        services = json.loads(os.environ["SERVICE_CREDENTIALS_JSON"])
        if not isinstance(services, dict):
            raise ValueError("Invalid service configuration")
        entry = services.get(x_service_id)
        if entry is not None and (
            not isinstance(entry, dict)
            or not isinstance(entry.get("token"), str)
            or not entry["token"]
            or not isinstance(entry.get("roles_read"), bool)
            or ("sessions_read" in entry and not isinstance(entry["sessions_read"], bool))
        ):
            raise ValueError("Invalid service configuration")
    except (KeyError, ValueError, TypeError):
        raise HTTPException(status_code=503, detail="service_auth_unavailable") from None
    if entry is None or not secrets.compare_digest(entry["token"].encode(), x_service_token.encode()):
        raise HTTPException(status_code=401, detail="invalid_service_credentials")
    if not entry.get(permission, False):
        raise HTTPException(status_code=403, detail="forbidden")


def authorize_service(x_service_id: str | None = Header(default=None), x_service_token: str | None = Header(default=None)) -> None:
    _authorize_service(x_service_id, x_service_token, "roles_read")


def authorize_session_service(x_service_id: str | None = Header(default=None), x_service_token: str | None = Header(default=None)) -> None:
    _authorize_service(x_service_id, x_service_token, "sessions_read")
