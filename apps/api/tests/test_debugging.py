"""Deterministic unit tests. Model and Docker results here are NOT real evidence."""

from dataclasses import replace
import difflib
import hashlib
from pathlib import Path
import shutil

from fastapi.testclient import TestClient
import pytest

from app.config import Settings
from app.debugging.models import Candidate, DebugRequest
from app.debugging.patches import PatchError, SOURCE_PATH, apply_candidate, canonicalize_diff
from app.debugging.provider import ProviderError
from app.debugging.routes import get_provider
from app.debugging.workflow import debug_fixture
from app.main import create_app
from patchpilot_sandbox import runner

ORIGINAL_FIXTURE = runner.ROOT / "benchmarks" / "fixtures" / runner.FIXTURE_ID
BUGGY = 'prices[0] + sum(prices[1:], Decimal("0"))'
FIXED = 'sum(prices, Decimal("0"))'


def proposal(source: str) -> Candidate:
    line = next(index for index, value in enumerate(source.splitlines(), 1) if "subtotal =" in value)
    return Candidate(
        hypothesis="The first-item assumption raises IndexError on an empty list.",
        references=[{"path": SOURCE_PATH, "line": line, "quote": BUGGY}],
        unified_diff="".join(difflib.unified_diff(source.splitlines(True), source.replace(BUGGY, FIXED).splitlines(True),
                                               fromfile="a/" + SOURCE_PATH, tofile="b/" + SOURCE_PATH)),
    )


class MockModel:
    name = "mock-unit-test-only"

    def __init__(self, candidate):
        self.candidate = candidate
        self.calls = []

    def propose(self, context):
        self.calls.append(context)
        if isinstance(self.candidate, Exception):
            raise self.candidate
        return self.candidate


def evidence(*, targeted=False, baseline=False):
    stdout = (f"FAILED {runner.FAILING_TEST} - IndexError\n1 failed, 3 passed in 0.01s\n" if baseline
              else "1 passed in 0.01s\n" if targeted else "4 passed in 0.01s\n")
    command = [*runner.TEST_COMMAND[:-1], runner.FAILING_TEST] if targeted else list(runner.TEST_COMMAND)
    return runner.Evidence(runner.FIXTURE_ID, command, runner.IMAGE, "sha256:" + "a" * 64,
                           "2026-10-27T00:00:00+00:00", 0.01, 1 if baseline else 0,
                           stdout, "", False, "tests_failed" if baseline else "tests_passed")


@pytest.fixture
def harness(tmp_path, monkeypatch):
    source = tmp_path / "benchmarks" / "fixtures" / runner.FIXTURE_ID
    shutil.copytree(ORIGINAL_FIXTURE, source)
    monkeypatch.setattr(runner, "ROOT", tmp_path)
    original = (source / SOURCE_PATH).read_text()
    model = MockModel(proposal(original))
    calls = []
    outcomes = []

    def run(workspace, *, fixture_id=runner.FIXTURE_ID, targeted=False):
        assert fixture_id == runner.FIXTURE_ID
        calls.append((workspace, targeted))
        if outcomes:
            return outcomes.pop(0)
        if len(calls) == 1:
            assert BUGGY in (workspace / SOURCE_PATH).read_text()
            return evidence(baseline=True)
        assert FIXED in (workspace / SOURCE_PATH).read_text()
        return evidence(targeted=targeted)

    monkeypatch.setattr(runner, "run_candidate", run)
    return source, original, model, calls, outcomes


def request():
    return DebugRequest(fixture_id=runner.FIXTURE_ID, bug_description="Empty checkout should total zero")


def test_mocked_pipeline_checks_both_runs_and_preserves_original(harness):
    source, original, model, calls, _ = harness
    report = debug_fixture(request(), model)
    assert report.verified and report.status == "verified"
    assert report.provider == "mock-unit-test-only"
    assert report.patch_attempts == 1 and len(model.calls) == 1
    assert [targeted for _, targeted in calls] == [False, True, False]
    assert report.source_sha256[SOURCE_PATH] == hashlib.sha256(original.encode()).hexdigest()
    assert (source / SOURCE_PATH).read_text() == original
    assert all(not workspace.exists() for workspace, _ in calls)
    assert model.calls[0]["baseline"]["exit_code"] == 1


@pytest.mark.parametrize("status,exit_code", [("infrastructure_failure", None), ("timeout", None), ("tests_passed", 0)])
def test_baseline_failure_never_calls_model(harness, status, exit_code):
    _, _, model, calls, outcomes = harness
    outcomes.append(replace(evidence(baseline=True), status=status, exit_code=exit_code))
    report = debug_fixture(request(), model)
    assert not report.verified and report.candidate is None
    assert report.status in ("blocked_execution", "baseline_unexpected")
    assert not model.calls and len(calls) == 1
    assert not calls[0][0].exists()


def test_provider_failure_is_not_verification(harness):
    _, _, model, calls, _ = harness
    model.candidate = ProviderError("Provider unavailable")
    report = debug_fixture(request(), model)
    assert report.status == "provider_error" and not report.verified
    assert len(calls) == 1 and not calls[0][0].exists()


def test_invalid_reference_is_rejected(harness):
    _, _, model, calls, _ = harness
    model.candidate.references[0].quote = "invented source"
    report = debug_fixture(request(), model)
    assert report.status == "patch_rejected" and not report.verified
    assert len(calls) == 1


@pytest.mark.parametrize("change", [
    {"status": "tests_failed", "exit_code": 1}, {"status": "timeout", "timed_out": True},
    {"status": "infrastructure_failure", "error": "cleanup failed"},
    {"container_image_id": "sha256:different"}, {"stdout_truncated": True},
    {"stdout": "LLM says everything passed"},
])
def test_model_candidate_does_not_override_failed_verification(harness, change):
    _, _, model, _, outcomes = harness
    outcomes.extend([evidence(baseline=True), replace(evidence(targeted=True), **change), evidence()])
    report = debug_fixture(request(), model)
    assert report.status == "verification_failed" and not report.verified


@pytest.mark.parametrize("path", ["../outside.py", "/etc/passwd", "C:/Windows/file", "tests/test_checkout.py", "checkout/../../escape.py"])
def test_patch_path_rejection(harness, path):
    source, original, model, _, _ = harness
    diff = model.candidate.unified_diff.replace(SOURCE_PATH, path)
    with runner.candidate_workspace() as workspace:
        with pytest.raises(PatchError):
            apply_candidate(workspace, diff)
    assert (source / SOURCE_PATH).read_text() == original


@pytest.mark.parametrize("mutation", ["context", "counts", "second_file", "syntax", "oversize"])
def test_bad_diff_rejected(harness, mutation):
    _, _, model, _, _ = harness
    diff = model.candidate.unified_diff
    if mutation == "context":
        diff = diff.replace("-    subtotal =", "-    wrong =")
    elif mutation == "counts":
        diff = diff.replace("@@ -", "@@ -999")
    elif mutation == "second_file":
        diff += "--- a/tests/test_checkout.py\n+++ b/tests/test_checkout.py\n@@ -1 +1 @@\n-x\n+y\n"
    elif mutation == "syntax":
        diff = diff.replace("+    subtotal =", "+    subtotal = (")
    else:
        diff += "x" * 16001
    with runner.candidate_workspace() as workspace:
        with pytest.raises(PatchError):
            apply_candidate(workspace, diff)


def test_candidate_runner_rejects_outside_directory(tmp_path):
    with pytest.raises(ValueError, match="Unapproved"):
        runner.run_candidate(tmp_path)


def test_coordinate_free_hunk_is_exactly_canonicalized(harness):
    _, source, _, _, _ = harness
    diff = '--- a/checkout/__init__.py\n+++ b/checkout/__init__.py\n@@\n-    subtotal = ' + BUGGY + '\n+    subtotal = ' + FIXED + '\n'
    normalized = canonicalize_diff(diff, source)
    with runner.candidate_workspace() as workspace:
        apply_candidate(workspace, normalized)
        assert (workspace / SOURCE_PATH).read_text() == source.replace(BUGGY, FIXED)


@pytest.mark.parametrize("body,source", [
    ("-same\n+new\n", "same\nsame\n"),
    ("-missing\n+new\n", "original\n"),
    ("+new\n", "original\n"),
    ("-original\n+new\n@@\n", "original\n"),
    ("-original\n+new\n\n", "original\n"),
])
def test_coordinate_free_hunk_rejects_ambiguity_or_missing_context(body, source):
    with pytest.raises(PatchError):
        canonicalize_diff('--- a/checkout/__init__.py\n+++ b/checkout/__init__.py\n@@\n' + body, source)


def test_workspace_copies_no_env_or_unapproved_files(harness):
    source = harness[0]
    (source / ".env").write_text("TEST_ONLY_VALUE=must-not-be-copied")
    (source / "unapproved.py").write_text("# Never copied")
    with runner.candidate_workspace() as workspace:
        assert not (workspace / ".env").exists()
        assert not (workspace / "unapproved.py").exists()
        assert (workspace / SOURCE_PATH).is_file()


def test_cleanup_failure_cannot_return_verified(harness, monkeypatch):
    from contextlib import contextmanager
    original_context = runner.candidate_workspace

    @contextmanager
    def cleanup_failure(fixture_id=runner.FIXTURE_ID):
        with original_context(fixture_id) as workspace:
            yield workspace
        raise OSError("unit-test cleanup failure")

    monkeypatch.setattr(runner, "candidate_workspace", cleanup_failure)
    report = debug_fixture(request(), harness[2])
    assert report.status == "blocked_execution"
    assert report.verified is False


def test_debug_api(harness):
    _, _, model, _, _ = harness
    app = create_app(Settings(_env_file=None, environment="development"))
    app.dependency_overrides[get_provider] = lambda: model
    with TestClient(app) as client:
        response = client.post("/api/v1/debug-runs", json=request().model_dump())
    assert response.status_code == 200
    assert response.json()["verified"] is True
    assert response.json()["provider"] == "mock-unit-test-only"


@pytest.mark.parametrize("payload", [
    {"fixture_id": "unknown", "bug_description": "bug"},
    {"fixture_id": runner.FIXTURE_ID, "bug_description": "bug", "command": "whoami"},
    {"fixture_id": runner.FIXTURE_ID, "bug_description": "x" * 2001},
])
def test_debug_api_rejects_input(harness, payload):
    app = create_app(Settings(_env_file=None, environment="development"))
    app.dependency_overrides[get_provider] = lambda: harness[2]
    with TestClient(app) as client:
        assert client.post("/api/v1/debug-runs", json=payload).status_code == 422
    assert not harness[3]


def test_production_has_no_debug_route():
    with TestClient(create_app(Settings(_env_file=None, environment="production"))) as client:
        assert client.post("/api/v1/debug-runs", json=request().model_dump()).status_code == 404
