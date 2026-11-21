import ipaddress
import os
from dataclasses import dataclass, field
from urllib.parse import urlsplit


@dataclass(frozen=True)
class WebSessionConfig:
    allowed_origins: frozenset[str]
    csrf_secret: bytes = field(repr=False)
    cookie_secure: bool
    cookie_name: str = "identity_refresh"
    cookie_path: str = "/auth/web"
    cookie_samesite: str = "strict"


def _is_loopback(host: str) -> bool:
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def _validate_origin(origin: str, allow_local_http: bool) -> None:
    try:
        parsed = urlsplit(origin)
        port = parsed.port
    except ValueError:
        raise ValueError("Invalid web origin") from None
    if (
        parsed.scheme not in ("http", "https")
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path
        or parsed.query
        or parsed.fragment
        or not parsed.netloc
        or (port is not None and not 1 <= port <= 65535)
    ):
        raise ValueError("Invalid web origin")
    if parsed.scheme == "http" and not (allow_local_http and _is_loopback(parsed.hostname)):
        raise ValueError("HTTP web origins are restricted to local development")
    if allow_local_http and not _is_loopback(parsed.hostname):
        raise ValueError("Local HTTP configuration requires loopback origins")


def load_web_session_config() -> WebSessionConfig:
    environment = os.environ.get("IDENTITY_ENV", "")
    local_http = os.environ.get("IDENTITY_WEB_ALLOW_LOCAL_HTTP", "false")
    if local_http not in ("true", "false"):
        raise ValueError("Invalid local HTTP configuration")
    allow_local_http = local_http == "true"
    if allow_local_http and environment != "local":
        raise ValueError("Local HTTP is only permitted in the local environment")

    origins = os.environ.get("IDENTITY_WEB_ORIGINS", "").split(",")
    if len(origins) != 1 or not origins[0] or origins[0] != origins[0].strip():
        raise ValueError("Exactly one web frontend origin must be configured")
    for origin in origins:
        _validate_origin(origin, allow_local_http)

    secret = os.environ.get("IDENTITY_WEB_CSRF_SECRET", "").encode("utf-8")
    if len(secret) < 32:
        raise ValueError("Web CSRF secret must contain at least 32 bytes")
    return WebSessionConfig(frozenset(origins), secret, cookie_secure=not allow_local_http)
