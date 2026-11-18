"""Verify the real Identity container in an isolated Compose project."""

import json
import os
import shutil
import subprocess
import tempfile
import time
import traceback
import uuid
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

SOURCE_ROOT = Path(__file__).resolve().parents[3]
ROOT = SOURCE_ROOT
PROJECT = f"identity-check-{uuid.uuid4().hex[:12]}"
ENV = os.environ.copy()
ENV.update({
    "IDENTITY_HOST_PORT": "0",
    "IDENTITY_DB_HOST_PORT": "0",
    "IDENTITY_ADMIN_EMAIL": "admin@example.com",
    "IDENTITY_ADMIN_PASSWORD": "test-admin-password",
    "IDENTITY_EVENTS_SERVICE_TOKEN": "test-events-token",
    "IDENTITY_PURCHASES_SERVICE_TOKEN": "test-purchases-token",
    "IDENTITY_SERVICE_CREDENTIALS_JSON": "",
    "IDENTITY_JWT_ISSUER": "identity-integration",
    "IDENTITY_JWT_AUDIENCE": "platform-integration",
})


def compose(*args, capture=False):
    result = subprocess.run(
        ["docker", "compose", "-p", PROJECT, "-f", "compose.yaml", *args],
        cwd=ROOT, env=ENV, check=True, text=True, capture_output=capture,
    )
    return result.stdout.strip() if capture else None


def request(base, method, path, payload=None, headers=None, expected=200):
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {"Content-Type": "application/json", **(headers or {})}
    req = Request(base + path, data=data, method=method, headers=headers)
    try:
        response = urlopen(req, timeout=15)
    except HTTPError as exc:
        response = exc
    with response:
        body = response.read()
        if response.status != expected:
            raise AssertionError(f"{method} {path}: expected {expected}, got {response.status}")
        return (json.loads(body) if body else None), response.headers


def fingerprint():
    return compose("exec", "-T", "identity-service", "sha256sum", "/keys/public/public.pem", capture=True).split()[0]


def administrator_count():
    value = compose("exec", "-T", "identity-dev-db", "psql", "-U", "identity", "-d", "identity_db", "-Atc", "SELECT count(*) FROM role_assignments WHERE role = 'administrador'", capture=True)
    return int(value)


def verify():
    compose("up", "-d", "--build", "--wait", "identity-service")
    compose("exec", "-T", "identity-service", "python", "-c", "import sys; assert sys.dont_write_bytecode")
    compose("run", "--rm", "identity-test-db-init")
    compose("run", "--rm", "identity-test-db-init")
    databases = compose("exec", "-T", "identity-dev-db", "psql", "-U", "identity", "-d", "postgres", "-Atc", "SELECT datname FROM pg_database WHERE datname IN ('identity_db', 'identity_test') ORDER BY datname", capture=True).splitlines()
    assert databases == ["identity_db", "identity_test"]
    port = compose("port", "identity-service", "8000", capture=True).rsplit(":", 1)[1]
    base = f"http://127.0.0.1:{port}"
    original_key = fingerprint()
    assert administrator_count() == 1
    password = "test-user-password"
    registered, _ = request(base, "POST", "/auth/register", {"email": "organizer@example.com", "password": password, "role": "organizador"}, expected=201)
    account_id = registered["account_id"]
    assert registered["roles"] == [{"role": "organizador", "status": "pendiente"}]
    probe = ROOT / "backend" / "identity-service" / "app" / f"reload_probe_{uuid.uuid4().hex}.py"
    probe.write_text("# reload probe\n", encoding="utf-8")
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        logs = compose("logs", "--no-color", "--no-log-prefix", "identity-service", capture=True)
        if probe.name in logs and "Reloading" in logs:
            break
        time.sleep(0.5)
    else:
        raise AssertionError("Identity did not reload after a source change")
    compose("up", "-d", "--wait", "identity-service")
    user, _ = request(base, "POST", "/auth/login", {"email": "organizer@example.com", "password": password})
    renewed, _ = request(base, "POST", "/auth/refresh", {"refresh_token": user["refresh_token"]})
    assert renewed["refresh_token"] != user["refresh_token"]
    admin, _ = request(base, "POST", "/auth/login", {"email": ENV["IDENTITY_ADMIN_EMAIL"], "password": ENV["IDENTITY_ADMIN_PASSWORD"]})
    request(base, "PATCH", f"/admin/organizers/{account_id}/status", {"status": "habilitado"}, {"Authorization": f"Bearer {admin['access_token']}"})
    roles, _ = request(base, "GET", f"/internal/accounts/{account_id}/roles", headers={"X-Service-Id": "events", "X-Service-Token": ENV["IDENTITY_EVENTS_SERVICE_TOKEN"]})
    assert roles["account_id"] == account_id
    assert roles["roles"] == [{"role": "organizador", "status": "habilitado"}]
    request(base, "POST", "/auth/logout", {"refresh_token": renewed["refresh_token"]}, expected=204)
    request(base, "POST", "/auth/refresh", {"refresh_token": renewed["refresh_token"]}, expected=401)
    compose("restart", "identity-service")
    compose("up", "-d", "--wait", "identity-service")
    port = compose("port", "identity-service", "8000", capture=True).rsplit(":", 1)[1]
    base = f"http://127.0.0.1:{port}"
    assert fingerprint() == original_key
    assert administrator_count() == 1
    request(base, "POST", "/auth/login", {"email": ENV["IDENTITY_ADMIN_EMAIL"], "password": ENV["IDENTITY_ADMIN_PASSWORD"]})
    compose("stop", "identity-dev-db")
    _, headers = request(base, "POST", "/auth/login", {"email": "organizer@example.com", "password": password}, {"X-Correlation-Id": "integration-error"}, expected=500)
    assert headers["X-Correlation-Id"] == "integration-error"
    logs = compose("logs", "--no-color", "--no-log-prefix", "identity-service", capture=True)
    records = []
    for line in logs.splitlines():
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(record, dict):
            records.append(record)
    error = next(record for record in records if record.get("correlation_id") == "integration-error")
    assert error["status_code"] == 500 and error["path"] == "/auth/login"
    assert {"method", "path", "status_code", "duration_ms", "correlation_id"} <= error.keys()
    assert password not in logs and ENV["IDENTITY_ADMIN_PASSWORD"] not in logs
    assert user["refresh_token"] not in logs and renewed["refresh_token"] not in logs
    assert not list((ROOT / "backend" / "identity-service").rglob("__pycache__"))
    print("Compose integration: isolated databases, reload, bootstrap, HTTP flow, restart and structured logs passed")


if __name__ == "__main__":
    with tempfile.TemporaryDirectory(prefix="identity-compose-") as directory:
        ROOT = Path(directory)
        shutil.copy2(SOURCE_ROOT / "compose.yaml", ROOT / "compose.yaml")
        target = ROOT / "backend" / "identity-service"
        shutil.copytree(
            SOURCE_ROOT / "backend" / "identity-service", target,
            ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", ".ruff_cache"),
        )
        try:
            verify()
        except Exception:
            traceback.print_exc()
            raise
        finally:
            compose("down", "--volumes", "--remove-orphans")
