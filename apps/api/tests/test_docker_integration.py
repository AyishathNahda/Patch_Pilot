"""Opt-in REAL execution; never invoke this benchmark directly with host pytest."""

import json
import os
import difflib
import hashlib

import pytest

from patchpilot_sandbox.runner import FIXTURE_ID, ROOT, run_fixture
from patchpilot_sandbox import runner
from app.debugging.models import Candidate, DebugRequest
from app.debugging.workflow import debug_fixture
from app.debugging.provider import GroqProvider
from app.config import Settings
from patchpilot_sandbox.fixtures import get_fixture
from test_multi_fixtures import DeterministicModel, NEW_IDS
from fastapi.testclient import TestClient
from app.main import create_app


@pytest.mark.docker
@pytest.mark.skipif(os.getenv("PATCHPILOT_RUN_DOCKER_TESTS") != "1", reason="Set PATCHPILOT_RUN_DOCKER_TESTS=1 to run real Docker")
def test_real_buggy_checkout():
    manifest = json.loads((ROOT / "benchmarks" / "fixtures" / FIXTURE_ID / "manifest.json").read_text())
    evidence = run_fixture(FIXTURE_ID)
    assert evidence.status == "tests_failed", evidence
    assert evidence.exit_code == 1
    assert manifest["expected_failing_test"] in evidence.stdout
    assert "IndexError" in evidence.stdout
    assert "1 failed, 3 passed" in evidence.stdout
    assert evidence.test_command == manifest["allowed_test_command"]
    assert not evidence.timed_out
    assert not evidence.stdout_truncated


def assert_no_temporary_containers():
    result = runner._invoke(["ps", "--all", "--filter", "label=patchpilot.reproduction=day2",
                             "--format", "{{.Names}}"], runner.CONTROL_TIMEOUT)
    assert not result.timed_out and result.exit_code == 0, result
    assert not result.stdout.strip(), result.stdout


@pytest.mark.docker
@pytest.mark.skipif(os.getenv("PATCHPILOT_RUN_DOCKER_TESTS") != "1", reason="Real Docker test is opt-in")
def test_real_docker_verifies_deterministic_candidate():
    """Real execution with a TEST-ONLY model stub, not a real AI-generated patch."""
    source_path = ROOT / "benchmarks" / "fixtures" / FIXTURE_ID / "checkout" / "__init__.py"
    original_hash = hashlib.sha256(source_path.read_bytes()).hexdigest()

    class TestModel:
        name = "deterministic-integration-test-only"

        def propose(self, context):
            source = context["sources"]["checkout/__init__.py"]
            old = 'prices[0] + sum(prices[1:], Decimal("0"))'
            new = 'sum(prices, Decimal("0"))'
            line = next(i for i, value in enumerate(source.splitlines(), 1) if old in value)
            return Candidate(hypothesis="First-item indexing fails on an empty cart.",
                             references=[{"path": "checkout/__init__.py", "line": line, "quote": old}],
                             unified_diff="".join(difflib.unified_diff(
                                 source.splitlines(True), source.replace(old, new).splitlines(True),
                                 fromfile="a/checkout/__init__.py", tofile="b/checkout/__init__.py")))

    report = debug_fixture(DebugRequest(fixture_id=FIXTURE_ID, bug_description="Empty cart should return zero"), TestModel())
    assert report.verified, report.model_dump()
    assert "1 failed, 3 passed" in report.baseline.stdout
    assert "1 passed" in report.failing_test.stdout
    assert "4 passed" in report.regression.stdout
    assert hashlib.sha256(source_path.read_bytes()).hexdigest() == original_hash
    assert_no_temporary_containers()


@pytest.mark.docker
@pytest.mark.skipif(os.getenv("PATCHPILOT_RUN_DOCKER_TESTS") != "1" or os.getenv("PATCHPILOT_RUN_GROQ_TESTS") != "1",
                    reason="Real Groq plus Docker test requires both opt-in flags")
def test_live_groq_patch_in_real_docker():
    config = Settings(_env_file=ROOT / "apps" / "api" / ".env")
    assert config.groq_api_key and config.groq_api_key.get_secret_value(), "GROQ_API_KEY required"
    report = debug_fixture(DebugRequest(fixture_id=FIXTURE_ID, bug_description="Empty cart should return Decimal zero"),
                           GroqProvider(config.groq_api_key, config.groq_model))
    assert report.verified, report.model_dump()
    assert report.provider == "groq"
    assert_no_temporary_containers()


@pytest.mark.docker
@pytest.mark.skipif(os.getenv("PATCHPILOT_RUN_DOCKER_TESTS") != "1", reason="Real Docker test is opt-in")
@pytest.mark.parametrize("fixture_id", NEW_IDS)
def test_real_new_fixture_reproduction_api(fixture_id):
    fixture = get_fixture(fixture_id)
    with TestClient(create_app(Settings(_env_file=None, environment="development"))) as client:
        response = client.post("/api/v1/reproductions", json={"fixture_id": fixture_id})
    assert response.status_code == 200
    evidence = response.json()
    assert evidence["status"] == "tests_failed" and evidence["exit_code"] == 1, evidence
    assert fixture.failing_test in evidence["stdout"]
    assert fixture.failure_marker in evidence["stdout"]
    assert f"1 failed, {fixture.expected_passed} passed" in evidence["stdout"]
    assert not evidence["stdout_truncated"]
    assert_no_temporary_containers()


@pytest.mark.docker
@pytest.mark.skipif(os.getenv("PATCHPILOT_RUN_DOCKER_TESTS") != "1", reason="Real Docker test is opt-in")
@pytest.mark.parametrize("fixture_id", NEW_IDS)
def test_real_new_fixture_deterministic_patch_verification(fixture_id):
    """Real Docker with a test-only model, never claimed as real Groq evidence."""
    fixture = get_fixture(fixture_id)
    paths = [ROOT / "benchmarks" / "fixtures" / fixture_id / relative for relative in fixture.files]
    before = [hashlib.sha256(path.read_bytes()).hexdigest() for path in paths]
    report = debug_fixture(DebugRequest(fixture_id=fixture_id, bug_description=fixture.example_bug_description), DeterministicModel())
    assert report.verified, report.model_dump()
    assert report.failing_test.exit_code == report.regression.exit_code == 0
    assert [hashlib.sha256(path.read_bytes()).hexdigest() for path in paths] == before
    assert_no_temporary_containers()
