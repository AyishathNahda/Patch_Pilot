"""HTTP transport is mocked; no Groq API calls or real credentials."""

import json

import httpx
from pydantic import SecretStr
import pytest

from app.config import Settings
from app.debugging.models import Candidate
from app.debugging.provider import GroqProvider, ProviderError

MOCK_CANDIDATE = {"hypothesis": "Unit-test placeholder", "references": [
    {"path": "checkout/__init__.py", "line": 1, "quote": "placeholder"}], "unified_diff": "placeholder"}


def test_key_environment_is_masked(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-only-key")
    config = Settings(_env_file=None)
    assert config.groq_api_key.get_secret_value() == "test-only-key"
    assert "test-only-key" not in repr(config)


def test_missing_key_never_calls_network():
    with pytest.raises(ProviderError, match="not configured"):
        GroqProvider(None, "test-model").propose({})


@pytest.mark.parametrize("fixture_id", ["shipping-threshold", "quantity-bool", "csv-quoted-fields"])
def test_provider_targets_selected_fixture(monkeypatch, fixture_id):
    from patchpilot_sandbox.fixtures import get_fixture
    fixture = get_fixture(fixture_id)
    real_client = httpx.AsyncClient
    def handler(request):
        body = json.loads(request.content)
        assert f"Only modify {fixture.source_path}" in body["messages"][0]["content"]
        return httpx.Response(200, json={"choices": [{"finish_reason": "stop", "message": {
            "content": json.dumps({**MOCK_CANDIDATE, "references": [{"path": fixture.source_path, "line": 1, "quote": "test-only"}]})}}]})
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: real_client(transport=httpx.MockTransport(handler), **kwargs))
    candidate = GroqProvider(SecretStr("test-only-key"), "test-model").propose({"fixture_id": fixture_id})
    assert candidate.references[0].path == fixture.source_path


@pytest.mark.parametrize("mode", ["valid", "invalid_json", "bad_schema", "large", "http_error", "json_error", "unsafe_error_code", "unfinished", "timeout"])
def test_groq_transport(monkeypatch, mode):
    real_client = httpx.AsyncClient

    def handler(request):
        assert request.url == "https://api.groq.com/openai/v1/chat/completions"
        assert request.headers["authorization"] == "Bearer test-only-key"
        body = json.loads(request.content)
        assert body["model"] == "test-model"
        assert body["response_format"] == {"type": "json_object"}
        assert body["max_completion_tokens"] == 2048
        assert "A bare @@ is invalid" in body["messages"][0]["content"]
        assert "tools" not in body
        if mode == "timeout":
            raise httpx.ReadTimeout("do not expose test-only-key")
        if mode == "http_error":
            return httpx.Response(401, text="do not expose test-only-key")
        if mode in ("json_error", "unsafe_error_code"):
            return httpx.Response(400, json={"error": {
                "code": "json_validate_failed" if mode == "json_error" else "test-only-key",
                "message": "do not expose test-only-key", "failed_generation": "private provider output",
            }})
        if mode == "large":
            return httpx.Response(200, content=b"x" * 65537)
        content = json.dumps(MOCK_CANDIDATE)
        if mode == "invalid_json":
            content = "not json"
        elif mode == "bad_schema":
            content = '{"verified":true}'
        return httpx.Response(200, json={"choices": [{"finish_reason": "length" if mode == "unfinished" else "stop",
                                                     "message": {"content": content}}]})

    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: real_client(transport=httpx.MockTransport(handler), **kwargs))
    provider = GroqProvider(SecretStr("test-only-key"), "test-model")
    if mode == "valid":
        assert isinstance(provider.propose({"sources": {}}), Candidate)
    else:
        with pytest.raises(ProviderError) as exc:
            provider.propose({})
        assert "test-only-key" not in str(exc.value)
        assert "private provider output" not in str(exc.value)
        if mode == "json_error":
            assert "json_validate_failed" in str(exc.value)
