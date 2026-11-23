import ipaddress
import math
import os
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey


@dataclass(frozen=True)
class IdentityConfig:
    identity_url: str
    public_key: str
    issuer: str
    audience: str
    service_id: str
    service_token: str = field(repr=False)
    timeout_seconds: float = 0.8


def _allowed_local_host(host: str) -> bool:
    if host in ("localhost", "identity-service"):
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def load_identity_config() -> IdentityConfig:
    try:
        url = os.environ["IDENTITY_URL"]
        parsed = urlsplit(url)
        port = parsed.port
        environment = os.environ.get("APP_ENV", "production")
        allow_http = os.environ.get("IDENTITY_ALLOW_LOCAL_HTTP", "false")
        if allow_http not in ("true", "false") or (
            allow_http == "true" and environment not in ("local", "test")
        ):
            raise ValueError("Invalid local transport configuration")
        if (
            url != url.strip()
            or parsed.scheme not in ("http", "https")
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.path not in ("", "/")
            or parsed.query
            or parsed.fragment
            or (port is not None and not 1 <= port <= 65535)
        ):
            raise ValueError("Invalid Identity URL")
        if parsed.scheme == "http" and not (
            environment in ("local", "test")
            and allow_http == "true"
            and _allowed_local_host(parsed.hostname)
        ):
            raise ValueError("Identity requires HTTPS")
        public_key = Path(os.environ["IDENTITY_PUBLIC_KEY_PATH"]).read_text(
            encoding="utf-8"
        )
        if not isinstance(
            serialization.load_pem_public_key(public_key.encode()), RSAPublicKey
        ):
            raise ValueError("Identity key must be RSA")
        issuer = os.environ["IDENTITY_ISSUER"]
        audience = os.environ["IDENTITY_AUDIENCE"]
        token = os.environ["IDENTITY_SERVICE_TOKEN"]
        timeout = float(os.environ.get("IDENTITY_TIMEOUT_SECONDS", "0.8"))
        if (
            not issuer.strip() or not audience.strip() or not token
            or not token.isascii() or not token.isprintable()
            or any(char.isspace() for char in token)
            or not math.isfinite(timeout) or timeout <= 0
        ):
            raise ValueError("Invalid Identity settings")
        return IdentityConfig(
            url.rstrip("/"), public_key, issuer, audience, "events", token, timeout
        )
    except (KeyError, OSError, TypeError, ValueError):
        raise ValueError("Identity configuration unavailable") from None
