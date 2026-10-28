"""Browser CORS boundaries and public OpenAPI error shapes."""

from fastapi.testclient import TestClient
from pydantic import ValidationError
import pytest

from app.config import Settings
from app.main import create_app


@pytest.mark.parametrize("origin", ["http://localhost:3000", "http://127.0.0.1:3000"])
def test_frontend_preflight_and_error_headers(origin):
    with TestClient(create_app(Settings(_env_file=None))) as client:
        response = client.options("/api/v1/debug-runs", headers={
            "Origin": origin, "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        })
        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == origin
        assert "access-control-allow-credentials" not in response.headers
        invalid = client.post("/api/v1/debug-runs", json={}, headers={"Origin": origin})
        assert invalid.status_code == 422
        assert invalid.headers["access-control-allow-origin"] == origin
        assert invalid.json()["error"]["code"] == "validation_error"


def test_unapproved_origin_and_method():
    with TestClient(create_app(Settings(_env_file=None))) as client:
        for origin, method in [("https://unapproved.example", "POST"), ("http://localhost:3000", "DELETE")]:
            response = client.options("/api/v1/debug-runs", headers={
                "Origin": origin, "Access-Control-Request-Method": method,
            })
            assert response.status_code == 400
        response = client.get("/health", headers={"Origin": "https://unapproved.example"})
        assert "access-control-allow-origin" not in response.headers


def test_custom_origins_from_environment(monkeypatch):
    monkeypatch.setenv("PATCHPILOT_CORS_ORIGINS", '["http://localhost:3001"]')
    with TestClient(create_app(Settings(_env_file=None))) as client:
        assert client.get("/health", headers={"Origin": "http://localhost:3001"}).headers["access-control-allow-origin"] == "http://localhost:3001"
        assert "access-control-allow-origin" not in client.get("/health", headers={"Origin": "http://localhost:3000"}).headers


@pytest.mark.parametrize("origin", ["*", "http://localhost:3000/path", "http://user:password@localhost:3000", "http://localhost:99999"])
def test_invalid_cors_config(origin):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, cors_origins=[origin])


def test_openapi_documents_actual_error_shapes():
    schema = create_app(Settings(_env_file=None, environment="development")).openapi()
    paths = schema["paths"]
    def response(path, status):
        return paths[path]["post"]["responses"][str(status)]["content"]["application/json"]["schema"]
    assert response("/api/v1/reproductions", 503)["$ref"].endswith("/Evidence")
    assert response("/api/v1/reproductions", 422)["$ref"].endswith("/ErrorResponse")
    assert response("/api/v1/debug-runs", 502)["$ref"].endswith("/DebugReport")
    assert {item["$ref"].rsplit("/", 1)[-1] for item in response("/api/v1/debug-runs", 422)["anyOf"]} == {"DebugReport", "ErrorResponse"}
