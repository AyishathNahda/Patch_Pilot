"""One baseline, one model proposal, one targeted test and one full regression run."""

from dataclasses import asdict
import hashlib
import re

from patchpilot_sandbox import runner
from patchpilot_sandbox.fixtures import get_fixture

from app.debugging.models import Candidate, DebugReport, DebugRequest
from app.debugging.patches import PatchError, apply_candidate, canonicalize_diff
from app.debugging.provider import ModelProvider, ProviderError


def _complete(evidence: runner.Evidence) -> bool:
    return (not evidence.timed_out and not evidence.stdout_truncated
            and not evidence.stderr_truncated and evidence.container_image_id is not None
            and evidence.error is None)


def _summary(output: str, expected: str) -> bool:
    return re.search(r"(?m)^" + re.escape(expected) + r" in [^\r\n]+$", output) is not None


def _validate_references(candidate: Candidate, sources: dict[str, str]) -> None:
    for reference in candidate.references:
        if reference.path not in sources:
            raise PatchError("Model reference is outside the selected fixture")
        lines = sources[reference.path].splitlines()
        if reference.line > len(lines) or reference.quote not in lines[reference.line - 1]:
            raise PatchError("Model reference does not match an actual source line")


def debug_fixture(request: DebugRequest, provider: ModelProvider) -> DebugReport:
    fixture = get_fixture(request.fixture_id)
    report = DebugReport(fixture_id=request.fixture_id, status="blocked_execution", provider=provider.name)
    # Snapshot first: baseline and patch operate on the same disposable tree.
    try:
        with runner.candidate_workspace(fixture.fixture_id) as workspace:
            sources = {path: (workspace / path).read_text(encoding="utf-8")
                       for path in (fixture.source_path, fixture.test_path)}
            if any(len(source.encode()) > 16000 for source in sources.values()):
                raise PatchError("Fixture source exceeds context limit")
            report.source_sha256 = {path: hashlib.sha256(text.encode()).hexdigest()
                                    for path, text in sources.items()}
            report.baseline = runner.run_candidate(workspace, fixture_id=fixture.fixture_id)
            baseline = report.baseline
            if baseline.status in ("infrastructure_failure", "timeout"):
                report.error = "Baseline execution unavailable; no model request or patch attempted."
                return report
            if not (baseline.status == "tests_failed" and baseline.exit_code == 1
                    and baseline.fixture_id == fixture.fixture_id and baseline.test_command == list(runner.TEST_COMMAND)
                    and _complete(baseline) and _summary(baseline.stdout, f"{fixture.expected_failed} failed, {fixture.expected_passed} passed")
                    and fixture.failing_test in baseline.stdout and fixture.failure_marker in baseline.stdout):
                report.status = "baseline_unexpected"
                report.error = "Expected fixture baseline was not observed."
                return report
            context = {"fixture_id": fixture.fixture_id, "intended_behavior": fixture.description,
                       "bug_description": request.bug_description,
                       "sources": sources, "baseline": asdict(baseline)}
            report.candidate = provider.propose(context)
            report.model_unified_diff = report.candidate.unified_diff
            report.patch_attempts = 1
            _validate_references(report.candidate, sources)
            report.candidate.unified_diff = canonicalize_diff(report.model_unified_diff, sources[fixture.source_path], fixture.source_path)
            apply_candidate(workspace, report.candidate.unified_diff, fixture.source_path)
            # The patcher may only modify the application file; tests stay unchanged.
            if (workspace / fixture.test_path).read_text(encoding="utf-8") != sources[fixture.test_path]:
                raise PatchError("Regression tests changed")
            report.failing_test = runner.run_candidate(workspace, fixture_id=fixture.fixture_id, targeted=True)
            report.regression = runner.run_candidate(workspace, fixture_id=fixture.fixture_id)
            targeted, regression = report.failing_test, report.regression
            report.verified = (all(
                evidence.status == "tests_passed" and evidence.exit_code == 0
                and evidence.fixture_id == fixture.fixture_id
                and _complete(evidence) and evidence.container_image_id == baseline.container_image_id
                for evidence in (targeted, regression)
            ) and targeted.test_command == [*runner.TEST_COMMAND[:-1], fixture.failing_test]
                and regression.test_command == list(runner.TEST_COMMAND)
                and _summary(targeted.stdout, "1 passed")
                and _summary(regression.stdout, f"{fixture.expected_passed + fixture.expected_failed} passed"))
            report.status = "verified" if report.verified else "verification_failed"
            if not report.verified:
                report.error = "Candidate did not pass both required sandbox test runs."
    except ProviderError as exc:
        report.status, report.error = "provider_error", str(exc)
    except PatchError as exc:
        report.status, report.error = "patch_rejected", str(exc)
    except (OSError, ValueError):
        # Includes disposable-workspace cleanup failures; never preserve verified=True.
        report.status, report.error = "blocked_execution", "Workspace preparation or cleanup failed."
        report.verified = False
    return report
