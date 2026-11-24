"""Exercise Identity, Events and Purchases in a disposable Compose project."""

import argparse
import json
import os
import re
import secrets
import shutil
import subprocess
import tempfile
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

SOURCE = Path(__file__).resolve().parents[1]
PROJECT = f"identity-integration-{uuid.uuid4().hex[:12]}"
ROOT = SOURCE
ENV = os.environ.copy()
EVENTS_SECRET = secrets.token_hex(32)
PURCHASES_SECRET = secrets.token_hex(32)
PASSWORD = secrets.token_urlsafe(24)
ENV.update(
    {
        "IDENTITY_DB_HOST_PORT": "0",
        "IDENTITY_HOST_PORT": "0",
        "EVENTS_DB_HOST_PORT": "0",
        "EVENTS_SERVICE_HOST_PORT": "0",
        "COMPRAS_DB_HOST_PORT": "0",
        "COMPRAS_SERVICE_HOST_PORT": "0",
        "IDENTITY_WEB_CSRF_SECRET": secrets.token_hex(32),
        "IDENTITY_ADMIN_EMAIL": "admin@example.com",
        "IDENTITY_ADMIN_PASSWORD": PASSWORD,
        "IDENTITY_EVENTS_SERVICE_TOKEN": EVENTS_SECRET,
        "IDENTITY_PURCHASES_SERVICE_TOKEN": PURCHASES_SECRET,
        "IDENTITY_SERVICE_CREDENTIALS_JSON": json.dumps(
            {
                "events": {
                    "token": EVENTS_SECRET,
                    "roles_read": True,
                    "sessions_read": True,
                },
                "purchases": {
                    "token": PURCHASES_SECRET,
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


def compose(*args, capture=False):
    result = subprocess.run(
        ["docker", "compose", "-p", PROJECT, "-f", "compose.yaml", *args],
        cwd=ROOT,
        env=ENV,
        check=True,
        text=True,
        capture_output=capture,
    )
    return result.stdout.strip() if capture else None


def base_url(service):
    port = compose("port", service, "8000", capture=True).rsplit(":", 1)[1]
    return f"http://127.0.0.1:{port}"


def request(base, method, path, payload=None, token=None, expected=200, headers=None):
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {"Content-Type": "application/json", **(headers or {})}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = Request(base + path, data=data, headers=headers, method=method)
    try:
        response = urlopen(req, timeout=10)
    except HTTPError as exc:
        response = exc
    with response:
        body = response.read()
        if response.status != expected:
            raise AssertionError(
                f"{method} {path}: expected {expected}, got {response.status}"
            )
        if "X-Correlation-Id" in headers:
            assert response.headers["X-Correlation-Id"] == headers["X-Correlation-Id"]
        return json.loads(body) if body else None


def wait_ready(base, path, expected=200):
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        try:
            request(base, "GET", path, expected=expected)
            return
        except (OSError, URLError, AssertionError):
            time.sleep(1)
    raise AssertionError(f"Service did not become ready: {path}")


def verify(rollback_files=None):
    compose(
        "up",
        "-d",
        "--build",
        "--wait",
        "identity-service",
        "events-service",
        "compras-service",
    )
    identity, events, purchases = (
        base_url(name)
        for name in ("identity-service", "events-service", "compras-service")
    )
    wait_ready(events, "/eventos")
    admin = request(
        identity,
        "POST",
        "/auth/login",
        {
            "email": ENV["IDENTITY_ADMIN_EMAIL"],
            "password": PASSWORD,
        },
    )["access_token"]

    def register(email, role):
        account = request(
            identity,
            "POST",
            "/auth/register",
            {
                "email": email,
                "password": PASSWORD,
                "role": role,
            },
            expected=201,
        )
        tokens = request(
            identity,
            "POST",
            "/auth/login",
            {
                "email": email,
                "password": PASSWORD,
            },
        )
        return account["account_id"], tokens

    organizer, organizer_tokens = register("organizer@example.com", "organizador")
    other_organizer, other_tokens = register("other@example.com", "organizador")
    customer, customer_tokens = register("customer@example.com", "cliente")
    _, other_customer = register("customer2@example.com", "cliente")
    for account in (organizer, other_organizer):
        request(
            identity,
            "PATCH",
            f"/admin/organizers/{account}/status",
            {
                "status": "habilitado",
            },
            token=admin,
        )
    event_payload = {
        "nombre": "Integration event",
        "venue": "Test venue",
        "fecha": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
        "modalidades": [
            {
                "nombre": "General",
                "tipo": "general",
                "precio": "1500.00",
                "cupo": 100,
            },
            {
                "nombre": "Platea Numerada",
                "tipo": "numerado",
                "sectores": [
                    {
                        "nombre": "Sector A",
                        "precio": "3000.00",
                        "asientos": [
                            {"fila": "1", "numero": 1},
                            {"fila": "1", "numero": 2},
                        ],
                    }
                ],
            },
        ],
    }
    org_token = organizer_tokens["access_token"]
    event_correlation = str(uuid.uuid4())
    event = request(
        events,
        "POST",
        "/eventos",
        event_payload,
        token=org_token,
        headers={"X-Correlation-Id": event_correlation},
        expected=201,
    )
    assert event["owner_id"] == organizer
    request(
        events,
        "PUT",
        f"/eventos/{event['id']}",
        event_payload,
        token=other_tokens["access_token"],
        expected=404,
    )
    request(
        events,
        "DELETE",
        f"/eventos/{event['id']}",
        token=other_tokens["access_token"],
        expected=404,
    )
    event = request(
        events, "PUT", f"/eventos/{event['id']}", event_payload, token=org_token
    )
    body = {"evento_id": event["id"], "modalidad_id": event["modalidades"][0]["id"]}
    key = {"Idempotency-Key": "integration-key"}
    purchase_correlation = str(uuid.uuid4())
    purchase = request(
        purchases,
        "POST",
        "/compras",
        body,
        token=customer_tokens["access_token"],
        headers={**key, "X-Correlation-Id": purchase_correlation},
        expected=201,
    )
    assert purchase["cliente_id"] == customer
    assert purchase["estado"] == "confirmada"
    assert "reserva_id" in purchase
    assert purchase["asiento_id"] is None

    # Test de integración: Compra en modalidad numerada con asiento
    modalidad_num = next(m for m in event["modalidades"] if m["tipo"] == "numerado")
    asiento_target = modalidad_num["sectores"][0]["asientos"][0]["id"]
    purchase_num = request(
        purchases,
        "POST",
        "/compras",
        {
            "evento_id": event["id"],
            "modalidad_id": modalidad_num["id"],
            "asiento_id": asiento_target,
        },
        token=customer_tokens["access_token"],
        headers={"Idempotency-Key": "integration-num-key"},
        expected=201,
    )
    assert purchase_num["asiento_id"] == asiento_target
    assert purchase_num["estado"] == "confirmada"

    # Conflicto al intentar comprar el mismo asiento nuevamente (409)
    request(
        purchases,
        "POST",
        "/compras",
        {
            "evento_id": event["id"],
            "modalidad_id": modalidad_num["id"],
            "asiento_id": asiento_target,
        },
        token=customer_tokens["access_token"],
        headers={"Idempotency-Key": "integration-num-key-2"},
        expected=409,
    )
    for service, correlation, method, path, status in (
        ("events-service", event_correlation, "POST", "/eventos", 201),
        ("events-service", purchase_correlation, "GET", f"/eventos/{event['id']}", 200),
        ("compras-service", purchase_correlation, "POST", "/compras", 201),
    ):
        output = compose("logs", "--no-color", "--no-log-prefix", service, capture=True)
        records = []
        for line in output.splitlines():
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        assert any(
            isinstance(record, dict)
            and record.get("correlation_id") == correlation
            and record.get("method") == method
            and record.get("path") == path
            and record.get("status_code") == status
            and isinstance(record.get("duration_ms"), (int, float))
            for record in records
        )
    assert (
        request(
            purchases,
            "POST",
            "/compras",
            body,
            token=customer_tokens["access_token"],
            headers=key,
        )["id"]
        == purchase["id"]
    )
    request(
        purchases,
        "POST",
        "/compras",
        {**body, "evento_id": str(uuid.uuid4())},
        token=customer_tokens["access_token"],
        headers=key,
        expected=409,
    )
    compras_ids = [
        c["id"]
        for c in request(
            purchases, "GET", "/compras", token=customer_tokens["access_token"]
        )
    ]
    assert purchase["id"] in compras_ids
    assert purchase_num["id"] in compras_ids
    request(
        purchases,
        "GET",
        f"/compras/{purchase['id']}",
        token=other_customer["access_token"],
        expected=404,
    )
    temporary = request(
        events, "POST", "/eventos", event_payload, token=org_token, expected=201
    )
    deleted = request(events, "DELETE", f"/eventos/{temporary['id']}", token=org_token)
    assert deleted["activo"] is False
    ENV["IDENTITY_PURCHASES_SERVICE_TOKEN"] = secrets.token_hex(32)
    compose("up", "-d", "--no-deps", "--force-recreate", "--wait", "compras-service")
    purchases = base_url("compras-service")
    wait_ready(purchases, "/compras", expected=401)
    request(
        purchases, "GET", "/compras", token=other_customer["access_token"], expected=503
    )
    ENV["IDENTITY_PURCHASES_SERVICE_TOKEN"] = PURCHASES_SECRET
    compose("up", "-d", "--no-deps", "--force-recreate", "--wait", "compras-service")
    purchases = base_url("compras-service")
    wait_ready(purchases, "/compras", expected=401)
    request(
        identity,
        "POST",
        "/auth/logout",
        {"refresh_token": customer_tokens["refresh_token"]},
        expected=204,
    )
    request(
        purchases,
        "GET",
        "/compras",
        token=customer_tokens["access_token"],
        expected=401,
    )
    request(
        identity,
        "PATCH",
        f"/admin/organizers/{organizer}/status",
        {"status": "deshabilitado"},
        token=admin,
    )
    request(events, "DELETE", f"/eventos/{event['id']}", token=org_token, expected=403)
    compose("stop", "identity-service")
    request(events, "DELETE", f"/eventos/{event['id']}", token=org_token, expected=503)
    request(
        purchases, "GET", "/compras", token=other_customer["access_token"], expected=503
    )
    logs = compose(
        "logs",
        "--no-color",
        "identity-service",
        "events-service",
        "compras-service",
        capture=True,
    )
    for secret in (
        PASSWORD,
        EVENTS_SECRET,
        PURCHASES_SECRET,
        org_token,
        customer_tokens["access_token"],
        customer_tokens["refresh_token"],
    ):
        assert secret not in logs
    if rollback_files is not None:
        request(events, "POST", "/eventos", event_payload, expected=401)
        request(purchases, "POST", "/compras", body, headers=key, expected=401)
        for path, source in rollback_files.items():
            (ROOT / path).write_bytes(source)
        compose("restart", "events-service", "compras-service")
        events = base_url("events-service")
        purchases = base_url("compras-service")
        wait_ready(events, "/eventos")
        wait_ready(purchases, f"/compras?cliente_id={customer}")
        old_event = request(
            events,
            "POST",
            "/eventos",
            {**event_payload, "owner_id": organizer},
            expected=201,
        )
        old_body = {
            "cliente_id": customer,
            "evento_id": old_event["id"],
            "modalidad_id": old_event["modalidades"][0]["id"],
        }
        request(
            purchases,
            "POST",
            "/compras",
            old_body,
            headers={"Idempotency-Key": "rollback-key"},
            expected=201,
        )
        print("Rollback to the supplied revision permits anonymous writes")
    print("Isolated Identity, Events and Purchases integration passed")


def load_rollback_files(ref):
    if ref.startswith("-"):
        raise ValueError("Invalid rollback revision")
    files = {}
    for service in ("events-service", "compras-service"):
        for filename in ("routers.py", "schemas.py"):
            path = f"backend/{service}/app/{filename}"
            try:
                result = subprocess.run(
                    ["git", "show", f"{ref}:{path}"],
                    cwd=SOURCE,
                    check=True,
                    capture_output=True,
                )
            except (OSError, subprocess.CalledProcessError):
                raise ValueError(
                    "Rollback revision or required files are unavailable locally"
                ) from None
            files[path] = result.stdout
    return files


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--rollback-ref",
        help="also test rollback using a locally available Git revision",
    )
    args = parser.parse_args()
    try:
        rollback_files = (
            load_rollback_files(args.rollback_ref) if args.rollback_ref else None
        )
    except ValueError as exc:
        parser.error(str(exc))
    with tempfile.TemporaryDirectory(prefix="identity-integration-") as directory:
        ROOT = Path(directory)
        for service in ("identity-service", "events-service", "compras-service"):
            shutil.copytree(
                SOURCE / "backend" / service,
                ROOT / "backend" / service,
                ignore=shutil.ignore_patterns(
                    "__pycache__", ".pytest_cache", ".ruff_cache"
                ),
            )
        shutil.copy2(SOURCE / "compose.yaml", ROOT / "compose.yaml")
        for script in (ROOT / "backend").rglob("*.sh"):
            script.write_bytes(script.read_bytes().replace(b"\r\n", b"\n"))
        try:
            verify(rollback_files)
        except Exception:
            logs = compose(
                "logs",
                "--no-color",
                "identity-service",
                "events-service",
                "compras-service",
                capture=True,
            )
            for secret in (
                PASSWORD,
                EVENTS_SECRET,
                PURCHASES_SECRET,
                ENV["IDENTITY_WEB_CSRF_SECRET"],
            ):
                logs = logs.replace(secret, "[redacted]")
            logs = re.sub(
                r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+", "[redacted]", logs
            )
            print(logs)
            raise
        finally:
            compose("down", "--volumes", "--remove-orphans")
