"""Verify compras-service against real events-service in an isolated Compose project."""

import json
import os
import shutil
import subprocess
import tempfile
import time
import traceback
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

SOURCE_ROOT = Path(__file__).resolve().parents[3]
ROOT = SOURCE_ROOT
PROJECT = f"compras-check-{uuid.uuid4().hex[:12]}"
SERVICES = ["events-db", "compras-db", "events-service", "compras-service"]
ENV = os.environ.copy()
ENV.update({
    "EVENTS_DB_HOST_PORT": "0",
    "COMPRAS_DB_HOST_PORT": "0",
    "EVENTS_SERVICE_HOST_PORT": "0",
    "COMPRAS_SERVICE_HOST_PORT": "0",
})


def compose(*args, capture=False):
    result = subprocess.run(
        ["docker", "compose", "-p", PROJECT, "-f", "compose.yaml", *args],
        cwd=ROOT, env=ENV, check=True, text=True, capture_output=capture,
    )
    return result.stdout.strip() if capture else None


def base_url(service):
    port = compose("port", service, "8000", capture=True).rsplit(":", 1)[1]
    return f"http://127.0.0.1:{port}"


def wait_ready(base, path, timeout=120):
    deadline = time.monotonic() + timeout
    while True:
        try:
            with urlopen(base + path, timeout=5) as response:
                if response.status == 200:
                    return
        except OSError:
            pass
        if time.monotonic() > deadline:
            raise AssertionError(f"{base}{path} did not become ready")
        time.sleep(1)


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
            raise AssertionError(
                f"{method} {path}: expected {expected}, got {response.status}: "
                f"{body.decode()}"
            )
        return (json.loads(body) if body else None), response.headers


def parse_records(logs):
    records = []
    for line in logs.splitlines():
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(record, dict):
            records.append(record)
    return records


def find_record(records, **expected):
    record = next(
        (r for r in records if all(r.get(k) == v for k, v in expected.items())), None
    )
    assert record is not None, f"bitacora sin registro {expected}"
    assert isinstance(record["duration_ms"], (int, float))
    return record


def verify():
    compose("up", "-d", "--build", "--wait", *SERVICES)
    events = base_url("events-service")
    compras = base_url("compras-service")
    wait_ready(events, "/eventos")
    wait_ready(compras, f"/compras?cliente_id={uuid.uuid4()}")

    event, _ = request(events, "POST", "/eventos", {
        "owner_id": str(uuid.uuid4()),
        "nombre": "Evento de verificacion",
        "venue": "Estadio de prueba",
        "fecha": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
        "modalidades": [
            {
                "nombre": "General",
                "tipo": "general",
                "precio": "1500.00",
                "cupo": 100,
            },
            {
                "nombre": "Numerada",
                "tipo": "numerado",
                "sectores": [
                    {
                        "nombre": "Sector A",
                        "precio": "3000.00",
                        "asientos": [
                            {"fila": "1", "numero": 1},
                        ],
                    }
                ],
            },
        ],
    }, expected=201)
    assert event["activo"] is True
    general = next(m["id"] for m in event["modalidades"] if m["tipo"] == "general")
    numerada = next(m["id"] for m in event["modalidades"] if m["tipo"] == "numerado")

    cliente_id = str(uuid.uuid4())
    key = str(uuid.uuid4())
    payload = {
        "cliente_id": cliente_id,
        "evento_id": event["id"],
        "modalidad_id": general,
    }
    corr_alta = f"compose-alta-{uuid.uuid4().hex[:8]}"
    corr_reintento = f"compose-reintento-{uuid.uuid4().hex[:8]}"
    corr_listado = f"compose-listado-{uuid.uuid4().hex[:8]}"

    compra, _ = request(
        compras, "POST", "/compras", payload,
        {"Idempotency-Key": key, "X-Correlation-Id": corr_alta}, expected=201,
    )
    assert compra["evento_id"] == event["id"]
    assert compra["modalidad_id"] == general

    retry, _ = request(
        compras, "POST", "/compras", payload,
        {"Idempotency-Key": key, "X-Correlation-Id": corr_reintento}, expected=200,
    )
    assert retry["id"] == compra["id"]

    request(compras, "POST", "/compras", {**payload, "modalidad_id": numerada},
            {"Idempotency-Key": key}, expected=409)

    listado, _ = request(compras, "GET", f"/compras?cliente_id={cliente_id}",
                         headers={"X-Correlation-Id": corr_listado})
    assert [c["id"] for c in listado] == [compra["id"]]

    logs_args = ("logs", "--no-color", "--no-log-prefix")
    records = parse_records(compose(*logs_args, "compras-service", capture=True))
    find_record(records, correlation_id=corr_alta, method="POST",
                path="/compras", status_code=201)
    find_record(records, correlation_id=corr_reintento, method="POST",
                path="/compras", status_code=200)
    find_record(records, correlation_id=corr_listado, method="GET",
                path="/compras", status_code=200)

    events_logs = compose(*logs_args, "events-service", capture=True)
    assert corr_alta in events_logs, "events-service no registro la consulta"
    print(
        "Compose integration: alta 201, reintento 200, conflicto 409, "
        "listado 200 y bitacora verificados"
    )


def copy_sources(target):
    for service in ("events-service", "compras-service"):
        shutil.copytree(
            SOURCE_ROOT / "backend" / service, target / "backend" / service,
            ignore=shutil.ignore_patterns(
                "__pycache__", ".pytest_cache", ".ruff_cache"
            ),
        )
    shutil.copy2(SOURCE_ROOT / "compose.yaml", target / "compose.yaml")
    # Windows checkouts may store shell scripts with CRLF, breaking the entrypoint.
    for script in (target / "backend").rglob("*.sh"):
        script.write_bytes(script.read_bytes().replace(b"\r\n", b"\n"))


if __name__ == "__main__":
    with tempfile.TemporaryDirectory(prefix="compras-compose-") as directory:
        ROOT = Path(directory)
        copy_sources(ROOT)
        try:
            verify()
        except Exception:
            traceback.print_exc()
            raise
        finally:
            compose("down", "--volumes", "--remove-orphans")
