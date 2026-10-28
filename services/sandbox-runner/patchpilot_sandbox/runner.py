"""A deliberately narrow Docker CLI runner for explicitly reviewed fixtures."""

from dataclasses import dataclass
from contextlib import contextmanager
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import shutil
import tempfile
from threading import Thread
from time import monotonic
from typing import Literal
from uuid import uuid4
from .fixtures import DEFAULT_FIXTURE, TEST_COMMAND, get_fixture

FIXTURE_ID = DEFAULT_FIXTURE  # Backward-compatible default for local callers/tests.
FAILING_TEST = get_fixture(FIXTURE_ID).failing_test
IMAGE = "patchpilot-sandbox:day2"
OUTPUT_LIMIT = 64 * 1024  # Per stream, bytes; readers keep draining after the cap.
EXECUTION_TIMEOUT = 20
CONTROL_TIMEOUT = 5
ROOT = Path(__file__).resolve().parents[3]


@dataclass
class CommandResult:
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool = False
    stdout_truncated: bool = False
    stderr_truncated: bool = False


@dataclass
class Evidence:
    fixture_id: str
    test_command: list[str]
    image_reference: str
    container_image_id: str | None
    started_at: str
    duration_seconds: float
    exit_code: int | None
    stdout: str
    stderr: str
    timed_out: bool
    status: Literal["tests_passed", "tests_failed", "timeout", "infrastructure_failure"]
    stdout_truncated: bool = False
    stderr_truncated: bool = False
    error: str | None = None


def _invoke(arguments: list[str], timeout: float) -> CommandResult:
    """Drain both pipes concurrently, retaining at most OUTPUT_LIMIT bytes each."""
    process = subprocess.Popen(
        ["docker", *arguments], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        stdin=subprocess.DEVNULL, shell=False,
    )
    buffers = [bytearray(), bytearray()]
    truncated = [False, False]

    def drain(stream, index: int) -> None:
        try:
            while chunk := stream.read(4096):
                remaining = OUTPUT_LIMIT - len(buffers[index])
                buffers[index].extend(chunk[:remaining])
                if len(chunk) > remaining:
                    truncated[index] = True
        finally:
            stream.close()

    readers = [Thread(target=drain, args=(stream, index), daemon=True)
               for index, stream in enumerate((process.stdout, process.stderr))]
    for reader in readers:
        reader.start()
    timed_out = False
    try:
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        process.kill()  # Kills the CLI; the caller also forcibly removes the container.
        process.wait(timeout=CONTROL_TIMEOUT)
    for reader in readers:
        reader.join(timeout=CONTROL_TIMEOUT)
    return CommandResult(
        process.returncode, buffers[0].decode("utf-8", errors="replace"),
        buffers[1].decode("utf-8", errors="replace"), timed_out, *truncated,
    )


def run_fixture(fixture_id: str) -> Evidence:
    # No request-supplied paths, images, commands, environment or Docker flags.
    fixture = get_fixture(fixture_id)
    return _run_fixture(fixture.fixture_id, ROOT / "benchmarks" / "fixtures" / fixture.fixture_id, TEST_COMMAND)


@contextmanager
def candidate_workspace(fixture_id: str = FIXTURE_ID):
    """Make a disposable copy of only the reviewed fixture, never platform secrets."""
    fixture = get_fixture(fixture_id)
    source = ROOT / "benchmarks" / "fixtures" / fixture.fixture_id
    parent = ROOT / ".data" / "candidates"
    parent.mkdir(parents=True, exist_ok=True)
    if parent.resolve() != parent:
        raise ValueError("Candidate storage must not contain links")
    with tempfile.TemporaryDirectory(prefix="candidate-", dir=parent) as temporary:
        destination = Path(temporary)
        # POSIX temporary directories default to 0700; the container's UID 65532
        # must be able to read this reviewed, read-only mounted fixture copy.
        destination.chmod(0o755)
        # Explicit file list excludes .env, caches and all unrelated host files.
        for relative in fixture.files:
            original = source / relative
            if original.resolve() != original or not original.is_file():
                raise ValueError("Fixture file is missing or linked")
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(original, target)
        yield destination


def run_candidate(workspace: Path, *, fixture_id: str = FIXTURE_ID, targeted: bool = False) -> Evidence:
    """Internal API: only disposable copies beneath our private candidate directory."""
    fixture = get_fixture(fixture_id)
    parent = ROOT / ".data" / "candidates"
    if (workspace.parent != parent or workspace.resolve() != workspace
            or not workspace.name.startswith("candidate-")):
        raise ValueError("Unapproved candidate directory")
    manifest = workspace / "manifest.json"
    if manifest.resolve() != manifest:
        raise ValueError("Candidate fixture identity mismatch")
    metadata = json.loads(manifest.read_text(encoding="utf-8"))
    if not isinstance(metadata, dict) or metadata.get("fixture_id") != fixture.fixture_id:
        raise ValueError("Candidate fixture identity mismatch")
    command = (*TEST_COMMAND[:-1], fixture.failing_test) if targeted else TEST_COMMAND
    return _run_fixture(fixture.fixture_id, workspace, command)


def _run_fixture(fixture_id: str, fixture: Path, command: tuple[str, ...]) -> Evidence:
    started = monotonic()
    evidence = Evidence(
        fixture_id, list(command), IMAGE, None,
        datetime.now(timezone.utc).isoformat(), 0, None, "", "", False,
        "infrastructure_failure",
    )
    name = f"patchpilot-repro-{uuid4().hex}"
    attempted_create = False
    try:
        image = _invoke(["image", "inspect", "--format", "{{.Id}}", IMAGE], CONTROL_TIMEOUT)
        if image.timed_out or image.exit_code != 0 or not image.stdout.strip().startswith("sha256:"):
            evidence.error = "Sandbox image unavailable; build it locally and check Docker."
            return evidence
        evidence.container_image_id = image.stdout.strip()
        # Refuse symlinks/junctions that could expose files outside the reviewed tree.
        if not fixture.is_dir() or fixture.is_symlink() or any(
            path.is_symlink() or not path.resolve().is_relative_to(fixture.resolve())
            for path in fixture.rglob("*")
        ) or fixture.resolve() != fixture:
            evidence.error = "Approved fixture directory is missing or contains links."
            return evidence
        attempted_create = True
        created = _invoke([
            "create", "--name", name, "--label", "patchpilot.reproduction=day2",
            "--network", "none", "--user", "65532:65532", "--cap-drop", "ALL",
            "--security-opt", "no-new-privileges=true", "--cpus", "1",
            "--memory", "256m", "--memory-swap", "256m", "--pids-limit", "64",
            "--read-only", "--tmpfs", "/tmp:rw,noexec,nosuid,nodev,size=32m,mode=1777",
            "--shm-size", "16m", "--log-driver", "none", "--workdir", "/workspace",
            "--mount", f"type=bind,source={fixture},target=/workspace,readonly",
            "--env", "PYTHONDONTWRITEBYTECODE=1", "--env", "PYTEST_DISABLE_PLUGIN_AUTOLOAD=1",
            "--env", "HOME=/tmp", "--entrypoint", "python",
            evidence.container_image_id, *command[1:],
        ], CONTROL_TIMEOUT)
        if created.timed_out or created.exit_code != 0:
            evidence.error = "Docker could not create the sandbox."
            return evidence
        result = _invoke(["start", "--attach", name], EXECUTION_TIMEOUT)
        evidence.stdout, evidence.stderr = result.stdout, result.stderr
        evidence.stdout_truncated = result.stdout_truncated
        evidence.stderr_truncated = result.stderr_truncated
        if result.timed_out:
            evidence.timed_out, evidence.status = True, "timeout"
            return evidence
        inspected = _invoke(["inspect", "--format", "{{json .State}}", name], CONTROL_TIMEOUT)
        if inspected.timed_out or inspected.exit_code != 0:
            evidence.error = "Cannot verify container exit state."
            return evidence
        state = json.loads(inspected.stdout)
        if not isinstance(state, dict) or type(state.get("ExitCode")) is not int:
            evidence.error = "Docker returned an invalid container state."
            return evidence
        evidence.exit_code = state["ExitCode"]
        if (state.get("Status") != "exited" or state.get("OOMKilled") or state.get("Error")
                or result.exit_code != evidence.exit_code):
            evidence.error = "Container did not complete normally."
        elif evidence.exit_code == 0:
            evidence.status = "tests_passed"
        elif evidence.exit_code == 1:
            evidence.status = "tests_failed"
        else:
            # pytest codes 2-5 mean interruption, internal/usage error or no tests.
            evidence.error = "Test process did not produce a normal test outcome."
    except (OSError, subprocess.SubprocessError, ValueError, KeyError, TypeError):
        evidence.status = "infrastructure_failure"
        evidence.error = "Docker unavailable or returned invalid execution evidence."
    finally:
        if attempted_create:
            try:
                removed = _invoke(["rm", "--force", name], CONTROL_TIMEOUT)
                # A timed-out create may never have created a container.
                missing = "No such container" in removed.stderr
                if removed.timed_out or (removed.exit_code != 0 and not missing):
                    evidence.status = "infrastructure_failure"
                    evidence.error = "Container cleanup failed; check Docker before retrying."
            except (OSError, subprocess.SubprocessError):
                evidence.status = "infrastructure_failure"
                evidence.error = "Container cleanup could not be confirmed; check Docker."
        evidence.duration_seconds = round(monotonic() - started, 3)
    return evidence
