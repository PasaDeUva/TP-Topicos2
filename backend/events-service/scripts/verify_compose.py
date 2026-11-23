"""Verify events-service against real containers in an isolated Compose project."""

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
PROJECT = f"events-check-{uuid.uuid4().hex[:12]}"
SERVICES = ["events-db", "events-service"]
ENV = os.environ.copy()
ENV.update({
    "EVENTS_DB_HOST_PORT": "0",
    "EVENTS_SERVICE_HOST_PORT": "0",
})


def compose(*args, capture=False):
    result = subprocess.run(
        ["docker", "compose", "-p", PROJECT, "-f", "compose.yaml", *args],
        cwd=ROOT, env=ENV, check=True, text=True, capture_output=capture,
    )
    return result.stdout.strip() if capture else None


def base_url():
    port = compose("port", "events-service", "8000", capture=True).rsplit(":", 1)[1]
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
        return json.loads(body) if body else None


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
    events = base_url()
    wait_ready(events, "/eventos")

    corr_alta = f"compose-alta-{uuid.uuid4().hex[:8]}"
    corr_consulta = f"compose-consulta-{uuid.uuid4().hex[:8]}"
    corr_listado = f"compose-listado-{uuid.uuid4().hex[:8]}"

    evento = request(events, "POST", "/eventos", {
        "owner_id": str(uuid.uuid4()),
        "nombre": "Evento de verificacion",
        "venue": "Estadio de prueba",
        "fecha": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
        "modalidades": [
            {
                "nombre": "General",
                "tipo": "general",
                "precio": "1000.00",
                "cupo": 100,
            }
        ],
    }, headers={"X-Correlation-Id": corr_alta}, expected=201)
    assert evento["activo"] is True
    assert [m["tipo"] for m in evento["modalidades"]] == ["general"]

    consulta = request(events, "GET", f"/eventos/{evento['id']}",
                       headers={"X-Correlation-Id": corr_consulta})
    assert consulta["nombre"] == evento["nombre"]

    request(events, "GET", f"/eventos/{uuid.uuid4()}", expected=404)

    listado = request(events, "GET", "/eventos",
                      headers={"X-Correlation-Id": corr_listado})
    assert evento["id"] in [e["id"] for e in listado]

    logs = compose("logs", "--no-color", "--no-log-prefix", "events-service",
                   capture=True)
    records = parse_records(logs)
    find_record(records, correlation_id=corr_alta, method="POST",
                path="/eventos", status_code=201)
    find_record(records, correlation_id=corr_consulta, method="GET",
                path=f"/eventos/{evento['id']}", status_code=200)
    find_record(records, correlation_id=corr_listado, method="GET",
                path="/eventos", status_code=200)
    print(
        "Compose integration: alta 201, consulta 200, 404, listado 200 "
        "y bitacora verificados"
    )


def copy_sources(target):
    shutil.copytree(
        SOURCE_ROOT / "backend" / "events-service",
        target / "backend" / "events-service",
        ignore=shutil.ignore_patterns(
            "__pycache__", ".pytest_cache", ".ruff_cache"
        ),
    )
    shutil.copy2(SOURCE_ROOT / "compose.yaml", target / "compose.yaml")
    # Windows checkouts may store shell scripts with CRLF, breaking the entrypoint.
    for script in (target / "backend").rglob("*.sh"):
        script.write_bytes(script.read_bytes().replace(b"\r\n", b"\n"))


if __name__ == "__main__":
    with tempfile.TemporaryDirectory(prefix="events-compose-") as directory:
        ROOT = Path(directory)
        copy_sources(ROOT)
        try:
            verify()
        except Exception:
            traceback.print_exc()
            raise
        finally:
            compose("down", "--volumes", "--remove-orphans")
