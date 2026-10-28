"""Unit tests mock Docker orchestration, never execute fixture code on the host."""

from dataclasses import asdict
import io
import json
import subprocess
import os

from fastapi.testclient import TestClient
import pytest

from app.config import Settings
from app.main import create_app
from app.execution import routes
from patchpilot_sandbox import runner


@pytest.fixture
def docker(monkeypatch):
    calls = []
    outcomes = {}

    def invoke(arguments, timeout):
        calls.append((arguments, timeout))
        operation = arguments[0]
        if operation in outcomes:
            outcome = outcomes[operation]
            if isinstance(outcome, Exception):
                raise outcome
            return outcome
        if operation == "image":
            return runner.CommandResult(0, "sha256:" + "a" * 64, "")
        if operation == "inspect":
            return runner.CommandResult(0, json.dumps({
                "Status": "exited", "ExitCode": 1, "OOMKilled": False, "Error": "",
            }), "")
        if operation == "start":
            return runner.CommandResult(1, "unit-test placeholder output", "")
        return runner.CommandResult(0, "", "")

    monkeypatch.setattr(runner, "_invoke", invoke)
    return calls, outcomes


def test_failing_tests_are_evidence_not_http_error(docker):
    with TestClient(create_app(Settings(_env_file=None, environment="development"))) as client:
        response = client.post("/api/v1/reproductions", json={"fixture_id": runner.FIXTURE_ID})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "tests_failed"
    assert body["exit_code"] == 1
    assert body["container_image_id"] == "sha256:" + "a" * 64
    assert body["test_command"] == list(runner.TEST_COMMAND)
    assert body["duration_seconds"] >= 0
    assert docker[0][-1][0][0:2] == ["rm", "--force"]


@pytest.mark.parametrize("payload", [
    {"fixture_id": "unknown"}, {"fixture_id": "../../etc"}, {},
    {"fixture_id": runner.FIXTURE_ID, "command": "anything"},
])
def test_request_allowlist(payload, docker):
    with TestClient(create_app(Settings(_env_file=None, environment="development"))) as client:
        assert client.post("/api/v1/reproductions", json=payload).status_code == 422
    assert not docker[0]


def test_endpoint_disabled_in_production(docker):
    with TestClient(create_app(Settings(_env_file=None, environment="production"))) as client:
        assert client.post("/api/v1/reproductions", json={"fixture_id": runner.FIXTURE_ID}).status_code == 404
    assert not docker[0]


def test_passing_tests(docker):
    docker[1]["start"] = runner.CommandResult(0, "unit-test placeholder", "")
    docker[1]["inspect"] = runner.CommandResult(0, json.dumps({"Status": "exited", "ExitCode": 0}), "")
    evidence = runner.run_fixture(runner.FIXTURE_ID)
    assert evidence.status == "tests_passed"
    assert evidence.exit_code == 0


def test_execution_timeout_removes_container(docker):
    docker[1]["start"] = runner.CommandResult(-9, "partial", "", timed_out=True)
    evidence = runner.run_fixture(runner.FIXTURE_ID)
    assert evidence.status == "timeout"
    assert evidence.timed_out
    assert evidence.exit_code is None
    assert docker[0][-1][0][0:2] == ["rm", "--force"]


@pytest.mark.parametrize("result,status", [
    (runner.CommandResult(-9, "partial", "", timed_out=True), "timeout"),
    (runner.CommandResult(1, "bounded", "bounded", stdout_truncated=True, stderr_truncated=True), "tests_failed"),
])
def test_api_preserves_execution_flags(docker, result, status):
    docker[1]["start"] = result
    with TestClient(create_app(Settings(_env_file=None, environment="development"))) as client:
        response = client.post("/api/v1/reproductions", json={"fixture_id": runner.FIXTURE_ID})
    assert response.status_code == 200
    assert response.json()["status"] == status
    assert response.json()["timed_out"] == result.timed_out
    assert response.json()["stdout_truncated"] == result.stdout_truncated
    assert response.json()["stderr_truncated"] == result.stderr_truncated


@pytest.mark.parametrize("outcome", [FileNotFoundError(), runner.CommandResult(1, "", "daemon offline")])
def test_docker_unavailable_returns_503(docker, outcome):
    docker[1]["image"] = outcome
    with TestClient(create_app(Settings(_env_file=None, environment="development"))) as client:
        response = client.post("/api/v1/reproductions", json={"fixture_id": runner.FIXTURE_ID})
    assert response.status_code == 503
    assert response.json()["status"] == "infrastructure_failure"


def test_container_security_flags(docker):
    runner.run_fixture(runner.FIXTURE_ID)
    args, timeout = next(call for call in docker[0] if call[0][0] == "create")
    for flag, value in {
        "--network": "none", "--user": "65532:65532", "--cap-drop": "ALL",
        "--security-opt": "no-new-privileges=true", "--cpus": "1",
        "--memory": "256m", "--memory-swap": "256m", "--pids-limit": "64",
        "--log-driver": "none",
    }.items():
        assert args[args.index(flag) + 1] == value
    assert "--read-only" in args
    assert args.count("--mount") == 1
    assert args[args.index("--mount") + 1].endswith("target=/workspace,readonly")
    assert "--env-file" not in args
    assert args[-len(runner.TEST_COMMAND):] == ["sha256:" + "a" * 64, *runner.TEST_COMMAND[1:]]
    assert timeout == runner.CONTROL_TIMEOUT


def test_candidate_copy_target_command_and_cleanup(docker):
    with runner.candidate_workspace() as workspace:
        if os.name != "nt":
            assert workspace.stat().st_mode & 0o777 == 0o755
        assert (workspace / "checkout" / "__init__.py").is_file()
        runner.run_candidate(workspace, targeted=True)
        args = next(call[0] for call in docker[0] if call[0][0] == "create")
        assert args[-1] == runner.FAILING_TEST
        assert f"source={workspace}," in args[args.index("--mount") + 1]
        assert "--read-only" in args
    assert not workspace.exists()


@pytest.mark.parametrize("operation,outcome", [
    ("create", runner.CommandResult(125, "", "container creation failed")),
    ("create", runner.CommandResult(-9, "", "", timed_out=True)),
    ("start", OSError("private detail")),
    ("inspect", runner.CommandResult(0, "bad json", "")),
    ("inspect", runner.CommandResult(0, "[]", "")),
    ("inspect", runner.CommandResult(0, '{"Status":"exited","ExitCode":137,"OOMKilled":true}', "")),
    ("inspect", runner.CommandResult(0, '{"Status":"exited","ExitCode":5}', "")),
    ("rm", runner.CommandResult(1, "", "daemon unavailable")),
])
def test_infrastructure_failures_and_cleanup(docker, operation, outcome):
    docker[1][operation] = outcome
    evidence = runner.run_fixture(runner.FIXTURE_ID)
    assert evidence.status == "infrastructure_failure"
    assert evidence.error
    assert "private detail" not in json.dumps(asdict(evidence))
    assert docker[0][-1][0][0:2] == ["rm", "--force"]


def test_unknown_fixture_never_invokes_docker(docker):
    with pytest.raises(ValueError):
        runner.run_fixture("unknown")
    assert not docker[0]


def test_busy_endpoint(docker):
    routes._execution_lock.acquire()
    try:
        with TestClient(create_app(Settings(_env_file=None, environment="development"))) as client:
            response = client.post("/api/v1/reproductions", json={"fixture_id": runner.FIXTURE_ID})
        assert response.status_code == 429
        assert not docker[0]
    finally:
        routes._execution_lock.release()


@pytest.mark.parametrize("timeout", [False, True])
def test_bounded_capture_and_cli_timeout(monkeypatch, timeout):
    class Process:
        def __init__(self):
            self.stdout = io.BytesIO(b"x" * (runner.OUTPUT_LIMIT + 5000))
            self.stderr = io.BytesIO(b"y" * (runner.OUTPUT_LIMIT + 2000))
            self.returncode = 0
            self.killed = False

        def wait(self, timeout):
            if timeout == 20 and not self.killed and should_timeout:
                raise subprocess.TimeoutExpired("docker", timeout)
            return self.returncode

        def kill(self):
            self.killed = True
            self.returncode = -9

    should_timeout = timeout
    process = Process()

    def popen(arguments, **kwargs):
        assert arguments == ["docker", "start", "--attach", "test-container"]
        assert kwargs["shell"] is False
        return process

    monkeypatch.setattr(runner.subprocess, "Popen", popen)
    result = runner._invoke(["start", "--attach", "test-container"], 20)
    assert len(result.stdout.encode()) == runner.OUTPUT_LIMIT
    assert len(result.stderr.encode()) == runner.OUTPUT_LIMIT
    assert result.stdout_truncated and result.stderr_truncated
    assert result.timed_out == timeout
    assert process.killed == timeout
