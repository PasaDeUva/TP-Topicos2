"""Docker Compose helpers for running isolated multi-service projects."""

import json
import subprocess
from pathlib import Path


def run_compose(root: Path, project: str, env: dict, *args, capture: bool = False) -> str | None:
    result = subprocess.run(
        ["docker", "compose", "-p", project, "-f", "compose.yaml", *args],
        cwd=root,
        env=env,
        check=True,
        text=True,
        capture_output=capture,
    )
    return result.stdout.strip() if capture else None


def get_base_url(root: Path, project: str, env: dict, service: str, port: str = "8000") -> str:
    output = run_compose(root, project, env, "port", service, port, capture=True)
    if not output:
        raise RuntimeError(f"Unable to resolve port for {service}:{port}")
    host_port = output.rsplit(":", 1)[1]
    return f"http://127.0.0.1:{host_port}"


def fetch_service_logs(root: Path, project: str, env: dict, *services) -> str:
    return run_compose(root, project, env, "logs", "--no-color", "--no-log-prefix", *services, capture=True) or ""


def parse_json_logs(raw_logs: str) -> list[dict]:
    records = []
    for line in raw_logs.splitlines():
        try:
            record = json.loads(line)
            if isinstance(record, dict):
                records.append(record)
        except json.JSONDecodeError:
            continue
    return records
