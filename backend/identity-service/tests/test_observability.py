import json
from uuid import UUID

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.database import get_session
from app.main import app
from app.observability import request_log


def test_health_generates_correlation_id_and_structured_log(capsys):
    with TestClient(app) as client:
        response = client.get("/health")
    record = json.loads(capsys.readouterr().out.strip())
    assert response.status_code == 200
    assert UUID(response.headers["X-Correlation-Id"]).version == 4
    assert record["correlation_id"] == response.headers["X-Correlation-Id"]
    assert record["method"] == "GET"
    assert record["path"] == "/health"
    assert record["status_code"] == 200
    assert record["duration_ms"] >= 0


def test_validation_error_propagates_id_without_logging_secrets(capsys):
    app.dependency_overrides[get_session] = lambda: None
    try:
        with TestClient(app) as client:
            response = client.post(
                "/auth/login?token=query-secret",
                headers={"X-Correlation-Id": "request-123", "Authorization": "Bearer header-secret"},
                json={"password": "body-secret"},
            )
    finally:
        app.dependency_overrides.pop(get_session, None)
    output = capsys.readouterr().out.strip()
    record = json.loads(output)
    assert response.status_code == 400
    assert response.headers["X-Correlation-Id"] == "request-123"
    assert record["path"] == "/auth/login"
    assert record["status_code"] == 400
    assert record["correlation_id"] == "request-123"
    assert all(secret not in output for secret in ("query-secret", "header-secret", "body-secret"))


def test_unhandled_error_has_log_and_correlation_without_exception_details(capsys):
    test_app = FastAPI()
    test_app.middleware("http")(request_log)

    @test_app.get("/failure")
    def failure():
        raise RuntimeError("exception-secret")

    with TestClient(test_app) as client:
        response = client.get("/failure", headers={"X-Correlation-Id": "failure-123"})
    output = capsys.readouterr().out.strip()
    record = json.loads(output)
    assert response.status_code == 500
    assert response.headers["X-Correlation-Id"] == "failure-123"
    assert response.json() == {"code": "internal_error", "message": "Internal server error"}
    assert record["status_code"] == 500
    assert record["correlation_id"] == "failure-123"
    assert "exception-secret" not in output
