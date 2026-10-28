import json
import logging

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.config import Settings
from app.logging_config import JsonFormatter
from app.main import create_app


def test_health() -> None:
    with TestClient(create_app(Settings(_env_file=None))) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "service": "patchpilot-api", "status": "ok", "version": "0.1.0",
    }


def test_health_uses_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PATCHPILOT_SERVICE_NAME", "custom-api")
    with TestClient(create_app(Settings(_env_file=None))) as client:
        assert client.get("/health").json()["service"] == "custom-api"


def test_invalid_configuration_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, log_level="INVALID")


def test_not_found() -> None:
    with TestClient(create_app(Settings(_env_file=None))) as client:
        response = client.get("/missing")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "http_error"


def test_unexpected_error_does_not_expose_details() -> None:
    application = create_app(Settings(_env_file=None))

    @application.get("/test-error")
    async def fail() -> None:
        raise RuntimeError("private implementation detail")

    with TestClient(application, raise_server_exceptions=False) as client:
        response = client.get("/test-error")
    assert response.status_code == 500
    assert response.json() == {"error": {
        "code": "internal_error", "message": "Internal server error",
    }}


def test_validation_error_does_not_echo_input() -> None:
    application = create_app(Settings(_env_file=None))

    @application.get("/test-validation")
    async def validate(count: int) -> dict[str, int]:
        return {"count": count}

    with TestClient(application) as client:
        response = client.get("/test-validation", params={"count": "private-input"})
    assert response.status_code == 422
    assert response.json() == {"error": {
        "code": "validation_error", "message": "Request validation failed",
    }}


def test_logs_are_json() -> None:
    record = logging.LogRecord("patchpilot", logging.INFO, "", 0, "API started", (), None)
    entry = json.loads(JsonFormatter().format(record))
    assert entry["message"] == "API started"
    assert entry["level"] == "INFO"
    assert entry["timestamp"].endswith("+00:00")
