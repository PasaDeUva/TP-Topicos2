"""HTTP request helper and readiness polling using standard library."""

import json
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def request(
    base: str,
    method: str,
    path: str,
    payload: dict | list | None = None,
    token: str | None = None,
    expected: int = 200,
    headers: dict | None = None,
):
    data = json.dumps(payload).encode() if payload is not None else None
    merged_headers = {"Content-Type": "application/json", **(headers or {})}
    if token:
        merged_headers["Authorization"] = f"Bearer {token}"
    req = Request(base + path, data=data, headers=merged_headers, method=method)
    try:
        response = urlopen(req, timeout=10)
    except HTTPError as exc:
        response = exc
    with response:
        body = response.read()
        if response.status != expected:
            raise AssertionError(
                f"{method} {path}: expected {expected}, got {response.status}. Response: {body.decode(errors='replace')}"
            )
        if "X-Correlation-Id" in merged_headers:
            assert response.headers["X-Correlation-Id"] == merged_headers["X-Correlation-Id"]
        return json.loads(body) if body else None


def wait_ready(base: str, path: str, expected: int = 200, timeout: int = 90):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            request(base, "GET", path, expected=expected)
            return
        except (OSError, URLError, AssertionError):
            time.sleep(1)
    raise AssertionError(f"Service did not become ready at {base}{path} within {timeout}s")
