"""Lifecycle management for disposable multi-service Docker Compose environments."""

import json
import os
import secrets
import shutil
import tempfile
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from harness.client import wait_ready
from harness.compose import get_base_url, run_compose
from harness.context import E2EContext
from harness.security import redact_logs


@contextmanager
def setup_environment(
    source_root: Path, rollback_ref: str | None = None
) -> Generator[E2EContext, None, None]:
    project = f"identity-integration-{uuid.uuid4().hex[:12]}"
    env = os.environ.copy()
    events_secret = secrets.token_hex(32)
    purchases_secret = secrets.token_hex(32)
    password = secrets.token_urlsafe(24)
    csrf_secret = secrets.token_hex(32)

    env.update(
        {
            "IDENTITY_DB_HOST_PORT": "0",
            "IDENTITY_HOST_PORT": "0",
            "EVENTS_DB_HOST_PORT": "0",
            "EVENTS_SERVICE_HOST_PORT": "0",
            "COMPRAS_DB_HOST_PORT": "0",
            "COMPRAS_SERVICE_HOST_PORT": "0",
            "IDENTITY_WEB_CSRF_SECRET": csrf_secret,
            "IDENTITY_ADMIN_EMAIL": "admin@example.com",
            "IDENTITY_ADMIN_PASSWORD": password,
            "IDENTITY_EVENTS_SERVICE_TOKEN": events_secret,
            "IDENTITY_PURCHASES_SERVICE_TOKEN": purchases_secret,
            "IDENTITY_SERVICE_CREDENTIALS_JSON": json.dumps(
                {
                    "events": {
                        "token": events_secret,
                        "roles_read": True,
                        "sessions_read": True,
                    },
                    "purchases": {
                        "token": purchases_secret,
                        "roles_read": True,
                        "sessions_read": True,
                    },
                }
            ),
            "CONSUMER_ENV": "test",
            "IDENTITY_ALLOW_LOCAL_HTTP": "true",
            "IDENTITY_SERVICE_URL": "http://identity-service:8000",
        }
    )

    with tempfile.TemporaryDirectory(prefix="identity-integration-") as directory:
        root = Path(directory)
        for service in ("identity-service", "events-service", "compras-service"):
            shutil.copytree(
                source_root / "backend" / service,
                root / "backend" / service,
                ignore=shutil.ignore_patterns(
                    "__pycache__", ".pytest_cache", ".ruff_cache", ".venv"
                ),
            )
        shutil.copy2(source_root / "compose.yaml", root / "compose.yaml")

        for script in (root / "backend").rglob("*.sh"):
            script.write_bytes(script.read_bytes().replace(b"\r\n", b"\n"))

        ctx: E2EContext | None = None
        try:
            run_compose(
                root,
                project,
                env,
                "up",
                "-d",
                "--build",
                "--wait",
                "identity-service",
                "events-service",
                "compras-service",
            )

            identity_url = get_base_url(root, project, env, "identity-service")
            events_url = get_base_url(root, project, env, "events-service")
            purchases_url = get_base_url(root, project, env, "compras-service")

            wait_ready(events_url, "/eventos")

            from harness.client import request as http_request

            admin_login = http_request(
                identity_url,
                "POST",
                "/auth/login",
                {
                    "email": env["IDENTITY_ADMIN_EMAIL"],
                    "password": password,
                },
            )
            admin_token = admin_login["access_token"]

            ctx = E2EContext(
                root=root,
                project=project,
                env=env,
                identity_url=identity_url,
                events_url=events_url,
                purchases_url=purchases_url,
                admin_email=env["IDENTITY_ADMIN_EMAIL"],
                admin_password=password,
                admin_token=admin_token,
                events_secret=events_secret,
                purchases_secret=purchases_secret,
                csrf_secret=csrf_secret,
                rollback_ref=rollback_ref,
            )

            yield ctx

        except Exception:
            logs = (
                run_compose(
                    root,
                    project,
                    env,
                    "logs",
                    "--no-color",
                    "identity-service",
                    "events-service",
                    "compras-service",
                    capture=True,
                )
                or ""
            )
            secrets_to_redact = [
                password,
                events_secret,
                purchases_secret,
                csrf_secret,
            ]
            if ctx:
                secrets_to_redact.extend(ctx.get_all_secrets())
            redacted = redact_logs(logs, secrets_to_redact)
            print("\n--- CONTAINER LOGS ON FAILURE (REDACTED) ---")
            print(redacted)
            raise
        finally:
            run_compose(
                root,
                project,
                env,
                "down",
                "--volumes",
                "--remove-orphans",
            )
