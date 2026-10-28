"""Fixture/patch unit tests use text only; benchmark code runs ONLY in Docker."""

from dataclasses import replace
import difflib
import hashlib
import json
import shutil
from pathlib import PurePosixPath

from fastapi.testclient import TestClient
import pytest

from app.config import Settings
from app.main import create_app
from app.execution import routes
from app.debugging.models import Candidate, DebugRequest
from app.debugging.patches import PatchError, apply_candidate, canonicalize_diff
from app.debugging.workflow import debug_fixture
from patchpilot_sandbox import runner
from patchpilot_sandbox.fixtures import FIXTURES, TEST_COMMAND, get_fixture

NEW_IDS = ("shipping-threshold", "quantity-bool", "csv-quoted-fields")
ORIGINAL_ROOT = runner.ROOT


def fixed_source(fixture, source):
    if fixture.fixture_id == "shipping-threshold":
        return source.replace('subtotal > Decimal("50.00")', 'subtotal >= Decimal("50.00")')
    if fixture.fixture_id == "quantity-bool":
        return source.replace("if not isinstance(value, int)", "if isinstance(value, bool) or not isinstance(value, int)")
    if fixture.fixture_id == "csv-quoted-fields":
        return source.replace('\n\n\ndef parse_record', '\n\nimport csv\n\n\ndef parse_record').replace('record.split(",")', 'next(csv.reader([record]))')
    raise AssertionError("Test-only fixture fix not defined")


class DeterministicModel:
    """TEST ONLY, not evidence of a real AI-generated patch."""
    name = "deterministic-test-only"

    def propose(self, context):
        fixture = get_fixture(context["fixture_id"])
        source = context["sources"][fixture.source_path]
        reference = next((i, line) for i, line in enumerate(source.splitlines(), 1) if line.strip().startswith("def "))
        return Candidate(hypothesis="Test-only hypothesis for fixture-specific orchestration.",
                         references=[{"path": fixture.source_path, "line": reference[0], "quote": reference[1]}],
                         unified_diff="".join(difflib.unified_diff(source.splitlines(True), fixed_source(fixture, source).splitlines(True),
                                                                  fromfile="a/" + fixture.source_path, tofile="b/" + fixture.source_path)))


def fake_evidence(fixture, targeted=False, baseline=False):
    summary = f"{fixture.expected_failed} failed, {fixture.expected_passed} passed" if baseline else "1 passed" if targeted else f"{fixture.expected_passed + fixture.expected_failed} passed"
    stdout = (f"FAILED {fixture.failing_test} - {fixture.failure_marker}\n" if baseline else "") + summary + " in 0.01s\n"
    return runner.Evidence(fixture.fixture_id, [*TEST_COMMAND[:-1], fixture.failing_test] if targeted else list(TEST_COMMAND),
                           runner.IMAGE, "sha256:test-only", "2026-10-28T00:00:00+00:00", .01,
                           1 if baseline else 0, stdout, "", False, "tests_failed" if baseline else "tests_passed")


@pytest.fixture
def fixture_tree(tmp_path, monkeypatch):
    for fixture in FIXTURES.values():
        shutil.copytree(ORIGINAL_ROOT / "benchmarks" / "fixtures" / fixture.fixture_id,
                        tmp_path / "benchmarks" / "fixtures" / fixture.fixture_id)
    monkeypatch.setattr(runner, "ROOT", tmp_path)
    return tmp_path


def test_discovery_is_read_only_and_explicit(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Discovery must never execute Docker")
    monkeypatch.setattr(runner, "_invoke", forbidden)
    with TestClient(create_app(Settings(_env_file=None, environment="production"))) as client:
        response = client.get("/api/v1/fixtures")
        assert response.status_code == 200
        items = response.json()["fixtures"]
        assert {item["fixture_id"] for item in items} == set(FIXTURES)
        for item in items:
            fixture = get_fixture(item["fixture_id"])
            assert item["expected_passed"] == fixture.expected_passed
            assert set(item) == {"fixture_id", "name", "category", "description", "example_bug_description", "language", "test_framework", "expected_failed", "expected_passed"}
        assert client.post("/api/v1/fixtures", json={"fixture_id": "unapproved"}).status_code == 405
    with pytest.raises(TypeError):
        FIXTURES["unapproved"] = next(iter(FIXTURES.values()))


def test_openapi_fixture_ids_match_registry():
    schema = create_app(Settings(_env_file=None, environment="development")).openapi()
    for model in ("FixtureInfo", "DebugRequest", "ReproductionRequest"):
        assert set(schema["components"]["schemas"][model]["properties"]["fixture_id"]["enum"]) == set(FIXTURES)


@pytest.mark.parametrize("fixture_id", list(FIXTURES))
def test_approved_reproduction_request(fixture_id, monkeypatch):
    fixture = get_fixture(fixture_id)
    calls = []
    def run(selected):
        calls.append(selected)
        return fake_evidence(fixture, baseline=True)
    monkeypatch.setattr(routes, "run_fixture", run)
    with TestClient(create_app(Settings(_env_file=None, environment="development"))) as client:
        response = client.post("/api/v1/reproductions", json={"fixture_id": fixture_id})
    assert response.status_code == 200 and response.json()["fixture_id"] == fixture_id
    assert calls == [fixture_id]
    assert DebugRequest(fixture_id=fixture_id, bug_description="test").fixture_id == fixture_id


@pytest.mark.parametrize("fixture_id", list(FIXTURES))
def test_manifest_matches_reviewed_registry(fixture_id):
    fixture = get_fixture(fixture_id)
    manifest = json.loads((ORIGINAL_ROOT / "benchmarks" / "fixtures" / fixture_id / "manifest.json").read_text())
    assert manifest["expected_failing_test"] == fixture.failing_test
    assert manifest["allowed_test_command"] == list(TEST_COMMAND)
    assert manifest["expected_passed"] == fixture.expected_passed
    assert manifest["expected_failed"] == fixture.expected_failed


@pytest.mark.parametrize("fixture_id", list(FIXTURES))
def test_registry_paths_and_test_plan_are_safe(fixture_id):
    fixture = get_fixture(fixture_id)
    assert fixture.expected_failed == 1 and fixture.expected_passed >= 2
    assert fixture.source_path != fixture.test_path and not fixture.source_path.startswith("tests/")
    assert fixture.test_path.startswith("tests/") and fixture.failing_test.startswith(fixture.test_path + "::")
    for path in fixture.files:
        parsed = PurePosixPath(path)
        assert not parsed.is_absolute() and ".." not in parsed.parts
        assert "\\" not in path and ":" not in path


@pytest.mark.parametrize("fixture_id", NEW_IDS)
def test_mocked_multi_fixture_pipeline(fixture_tree, monkeypatch, fixture_id):
    fixture = get_fixture(fixture_id)
    source = fixture_tree / "benchmarks" / "fixtures" / fixture_id / fixture.source_path
    original_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    calls = []
    def run(workspace, *, fixture_id, targeted=False):
        assert fixture_id == fixture.fixture_id
        calls.append(workspace)
        return fake_evidence(fixture, targeted, baseline=len(calls) == 1)
    monkeypatch.setattr(runner, "run_candidate", run)
    report = debug_fixture(DebugRequest(fixture_id=fixture_id, bug_description=fixture.example_bug_description), DeterministicModel())
    assert report.verified, report.error
    assert report.baseline.fixture_id == fixture_id
    assert report.failing_test.test_command[-1] == fixture.failing_test
    assert report.regression.stdout.startswith(f"{fixture.expected_passed + 1} passed")
    assert hashlib.sha256(source.read_bytes()).hexdigest() == original_hash
    assert all(not workspace.exists() for workspace in calls)


@pytest.mark.parametrize("fixture_id", NEW_IDS)
@pytest.mark.parametrize("target", ["checkout/__init__.py", "tests/unapproved.py", "../escape.py", "/tmp/escape.py"])
def test_cross_fixture_and_traversal_patches_rejected(fixture_tree, fixture_id, target):
    fixture = get_fixture(fixture_id)
    with runner.candidate_workspace(fixture_id) as workspace:
        source = (workspace / fixture.source_path).read_text()
        model = DeterministicModel().propose({"fixture_id": fixture_id, "sources": {fixture.source_path: source}})
        bad_diff = model.unified_diff.replace(fixture.source_path, target)
        with pytest.raises(PatchError):
            apply_candidate(workspace, bad_diff, fixture.source_path)
        assert (workspace / fixture.source_path).read_text() == source


def test_wrong_fixture_identity_is_rejected_before_docker(fixture_tree, monkeypatch):
    monkeypatch.setattr(runner, "_invoke", lambda *args: pytest.fail("Must not reach Docker"))
    with runner.candidate_workspace("shipping-threshold") as workspace:
        with pytest.raises(ValueError, match="identity"):
            runner.run_candidate(workspace, fixture_id="quantity-bool")


@pytest.mark.parametrize("fixture_id", NEW_IDS)
def test_coordinate_free_patch_for_selected_fixture(fixture_tree, fixture_id):
    fixture = get_fixture(fixture_id)
    with runner.candidate_workspace(fixture_id) as workspace:
        source = (workspace / fixture.source_path).read_text()
        fixed = fixed_source(fixture, source)
        diff = (f"--- a/{fixture.source_path}\n+++ b/{fixture.source_path}\n@@\n"
                + "".join("-" + line for line in source.splitlines(True))
                + "".join("+" + line for line in fixed.splitlines(True)))
        normalized = canonicalize_diff(diff, source, fixture.source_path)
        apply_candidate(workspace, normalized, fixture.source_path)
        assert (workspace / fixture.source_path).read_text() == fixed


def test_manifest_command_does_not_authorize_execution(fixture_tree, monkeypatch):
    calls = []
    def invoke(args, timeout):
        calls.append(args)
        if args[0] == "image":
            return runner.CommandResult(0, "sha256:test-only", "")
        if args[0] == "start":
            return runner.CommandResult(-9, "", "", timed_out=True)
        return runner.CommandResult(0, "", "")
    monkeypatch.setattr(runner, "_invoke", invoke)
    with runner.candidate_workspace("csv-quoted-fields") as workspace:
        manifest = workspace / "manifest.json"
        data = json.loads(manifest.read_text())
        data["allowed_test_command"] = ["sh", "-c", "unapproved"]
        manifest.write_text(json.dumps(data))
        runner.run_candidate(workspace, fixture_id="csv-quoted-fields", targeted=True)
    create = next(args for args in calls if args[0] == "create")
    assert create[-1] == get_fixture("csv-quoted-fields").failing_test
    assert "unapproved" not in create
    assert calls[-1][0:2] == ["rm", "--force"]


@pytest.mark.parametrize("change", [{"status": "tests_failed", "exit_code": 1}, {"fixture_id": "checkout-empty-cart"}, {"stdout": "4 passed in 0.1s\n"}])
def test_regression_failure_or_wrong_fixture_cannot_verify(fixture_tree, monkeypatch, change):
    fixture = get_fixture("quantity-bool")
    outcomes = iter([fake_evidence(fixture, baseline=True), fake_evidence(fixture, targeted=True), replace(fake_evidence(fixture), **change)])
    monkeypatch.setattr(runner, "run_candidate", lambda *args, **kwargs: next(outcomes))
    report = debug_fixture(DebugRequest(fixture_id=fixture.fixture_id, bug_description="reject bool"), DeterministicModel())
    assert not report.verified and report.status == "verification_failed"


def test_foreign_reference_is_rejected(fixture_tree, monkeypatch):
    fixture = get_fixture("shipping-threshold")
    monkeypatch.setattr(runner, "run_candidate", lambda *args, **kwargs: fake_evidence(fixture, baseline=True))
    class ForeignReference(DeterministicModel):
        def propose(self, context):
            candidate = super().propose(context)
            candidate.references[0].path = "inventory/__init__.py"
            return candidate
    report = debug_fixture(DebugRequest(fixture_id=fixture.fixture_id, bug_description="threshold"), ForeignReference())
    assert report.status == "patch_rejected" and not report.verified
