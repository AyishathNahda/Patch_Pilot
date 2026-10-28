# Day 2 verification — 2026-10-27

> Publication note: machine-local paths are redacted. Use the current README for runnable setup commands.

## Latest verification: Docker restored

Docker Desktop is now working (Engine 29.5.2, Linux/amd64). The sandbox image built
successfully. Real Docker integration tests: **2 passed, 1 skipped, 72 deselected,
1 warning in 13.47s**. Full suite with Docker enabled: **74 passed, 1 skipped,
1 warning in 14.18s**. The skipped test requires live Groq credentials.

Real `POST /api/v1/reproductions` returned HTTP 200, `tests_failed`, exit code 1,
`IndexError`, and exactly **1 failed, 3 passed in 0.18s**. Total runner duration:
3.172 seconds. Full evidence is retained locally in ignored `day-2-api-evidence.json`, including the
image ID, exact command, timestamps, stdout, empty stderr, and truncation flags.
No timeout or truncation occurred. Container cleanup checks returned no leftovers.
The original fixture SHA256 remains
`d85d9c9aaaf7055db00547aa5a372b341c230274d0e75012962d482764bf3df2`.

**Day 2 real reproduction is now verified.** The earlier blocked results below
are historical. No application/security changes were needed for this verification.

Commands executed from root:

```powershell
docker version
docker build --tag patchpilot-sandbox:day2 services\sandbox-runner
$env:PATCHPILOT_RUN_DOCKER_TESTS = '1'
.\.venv\Scripts\python.exe -m pytest -q -m docker
.\.venv\Scripts\python.exe -m pytest -q
Remove-Item Env:PATCHPILOT_RUN_DOCKER_TESTS
docker ps -a --filter label=patchpilot.reproduction=day2 --format '{{.Names}}'
```

Each test invocation's actual exit code was captured before clearing the opt-in
environment flag and propagated by the shell wrapper. Uvicorn was started from
`apps/api` with `..\..\.venv\Scripts\python.exe -m uvicorn app.main:app --host
127.0.0.1 --port 8765`. A real HTTP request was captured using:

```powershell
$response = Invoke-WebRequest -Method Post -Uri http://127.0.0.1:8765/api/v1/reproductions -ContentType 'application/json' -Body '{"fixture_id":"checkout-empty-cart"}'
$response.StatusCode
$response.Content
Set-Content -LiteralPath docs/day-2-api-evidence.json -Value $response.Content -Encoding utf8
Get-FileHash benchmarks/fixtures/checkout-empty-cart/checkout/__init__.py -Algorithm SHA256
```

## Actual result

**Implementation complete; real fixture reproduction is blocked by Docker Desktop startup failure.**
No fixture test code was run on the host. No AI functionality, database, queue,
frontend, commits, pushes or deployment was introduced.

| Check | Observed result |
| --- | --- |
| Existing Day 1 tests alone | 7 passed, 1 warning in 0.68s |
| Final default suite (Python 3.12.14) | 32 passed, 1 skipped, 1 warning in 0.85s |
| Opt-in Docker integration attempt | 1 failed, 29 deselected, 1 warning in 5.88s |
| Dependency compatibility | `No broken requirements found.` |
| Real Uvicorn startup | Application startup completed |
| Real POST reproduction | HTTP 503, `infrastructure_failure`, duration 5.203 seconds |
| Real GET health | Service `patchpilot-api`, status `ok`, version `0.1.0` |
| Uvicorn shutdown | Application shutdown completed after Ctrl+C |
| Real fixture failure/pass counts | **Not verified: no working Docker engine/image** |

The integration attempt was made before three additional unit cases were added;
its 29 deselected cases reflect that earlier suite. It failed because the runner
could not inspect the sandbox image, not because the checkout test executed.
The integration assertion intentionally fails on infrastructure errors. Its
PowerShell `try/finally` wrapper returned shell exit 0, but pytest reported a
failure; the test must not be treated as passed.

All 32 default tests are host-side API/orchestration tests with Docker mocked
where needed. Seven preserve Day 1 behavior; 25 additional cases cover allowlists,
passing/failing results, timeout, Docker errors, invalid inspection data, OOM,
cleanup attempts/failure, busy handling, security flags and bounded capture.
Their placeholder stdout strings are **not** fixture evidence.

The one warning remains Starlette's deprecated `anyio.abc.BlockingPortal` alias.
It has not been suppressed. Python 3.11 has not been tested.

## Docker blocker and real API evidence

Initial `docker version` printed client version 29.5.2, context `desktop-linux`,
then failed because `dockerDesktopLinuxEngine` was not available. Starting Docker
Desktop through its CLI did not recover it. Its backend log reported:

```text
starting services: initializing Inference manager
The file cannot be accessed by the system.
(listener: The filename, directory name, or volume label syntax is incorrect.)
```

Docker Desktop also reported that it encountered an unexpected error and needed
to close. No factory reset, settings change, or Docker data deletion was performed.
The owned hanging CLI processes and build plugin were stopped; the verification
API server was stopped. A build was attempted, timed out, and produced no verified
image. There was therefore no basis to claim a real empty-cart test failure.

The actual HTTP response is retained locally in ignored `docs/day-2-api-evidence.json` (not included in the public repository).
It has no image ID or exit code because no test container was started. Its timeout
flag is false because that field describes **test execution** timeout; the image
availability check timed out as an infrastructure failure instead.

The benchmark is designed to produce `IndexError` in
`tests/test_checkout.py::test_empty_cart_returns_zero`, with three passing tests.
Those are expectations from the manifest and source, not observed test results.

## Commands executed

Unless specified otherwise, commands ran in
`<repository-root>`. File writes used the patch tool.

Inspection:

```powershell
Get-Content -LiteralPath '<local-task-notes>'
Get-Content AGENTS.md
git status --short
Get-Content apps/api/app/main.py,apps/api/app/config.py,apps/api/tests/test_api.py,apps/api/pytest.ini,README.md,docs/architecture.md
rg --files --hidden -g '!.git/**' -g '!.venv/**' -g '!**/__pycache__/**'
docker version
Get-Item 'C:\Program Files\Docker\Docker\Docker Desktop.exe' -ErrorAction SilentlyContinue
.\.venv\Scripts\python.exe --version
docker desktop start
docker version
docker pull python:3.12.14-slim-bookworm
```

Installation:

```powershell
.\.venv\Scripts\python.exe -m pip install -e services\sandbox-runner
```

From `apps/api`:

```powershell
..\..\.venv\Scripts\python.exe -m pytest -q tests/test_api.py
..\..\.venv\Scripts\python.exe -m pytest -q
```

The second command initially reported 29 passed/1 skipped. From root:

```powershell
$env:PATCHPILOT_RUN_DOCKER_TESTS = '1'
try { .\.venv\Scripts\python.exe -m pytest -q -m docker } finally { Remove-Item Env:PATCHPILOT_RUN_DOCKER_TESTS }
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir apps/api --host 127.0.0.1 --port 8765
```

In a second root shell while Uvicorn was running:

```powershell
$response = Invoke-WebRequest -Method Post -Uri http://127.0.0.1:8765/api/v1/reproductions -ContentType 'application/json' -Body '{"fixture_id":"checkout-empty-cart"}' -SkipHttpErrorCheck
$response.StatusCode
$response.Content
Set-Content -LiteralPath docs/day-2-api-evidence.json -Value $response.Content -Encoding utf8
Invoke-RestMethod http://127.0.0.1:8765/health
```

`-SkipHttpErrorCheck` is PowerShell 7 syntax, used only to capture the real 503.
The normal README reproduction example uses `Invoke-RestMethod` and works in
Windows PowerShell; it will raise an HTTP error when Docker is unavailable.
Uvicorn was stopped using Ctrl+C; the terminal wrapper returned 1 for interruption
while logs confirmed shutdown.

Docker diagnostics and cleanup of the specific owned commands:

```powershell
Get-Process -Name 'Docker Desktop','com.docker.backend','wsl' -ErrorAction SilentlyContinue | Select-Object ProcessName,Id,CPU
Get-Content "$env:LOCALAPPDATA\Docker\log\host\com.docker.backend.exe.log" -Tail 12 -ErrorAction SilentlyContinue
Get-CimInstance Win32_Process -Filter "name='docker.exe'" | Select-Object ProcessId,CommandLine
Stop-Process -Id 24404,29024
Stop-Process -Id 26476
```

Those IDs were inspected immediately before stopping the owned `desktop start`,
`version` and `pull` commands. **Do not reuse those IDs in another session.**

Bounded build attempt (root; diagnostic wrapper returns 0 on timeout, not a
successful build result):

```powershell
.\.venv\Scripts\python.exe -c "import subprocess; result = None
try:
 result = subprocess.run(['docker', 'build', '--tag', 'patchpilot-sandbox:day2', 'services/sandbox-runner'], capture_output=True, text=True, timeout=10)
 print('exit_code:', result.returncode); print(result.stdout); print(result.stderr)
except subprocess.TimeoutExpired:
 print('Docker build exceeded 10-second availability check; CLI terminated. No successful image build verified.')"
Get-CimInstance Win32_Process -Filter "name='docker-buildx.exe'" | Select-Object ProcessId,CommandLine
Stop-Process -Id 33176
```

The Docker build plugin inherited output pipes and remained blocked after the
parent CLI timeout; its inspected, owned process was stopped explicitly. This
was a build-time tool problem, not a sandbox run. Builds are manual setup and
are never initiated by the API.

Final checks from root:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pip check
git diff --check
git status --short
rg --files --hidden -g '!.git/**' -g '!.venv/**' -g '!**/__pycache__/**' -g '!**/.pytest_cache/**' -g '!**/*.egg-info/**'
```

The root suite was run after additional cases: first 31 passed/1 skipped, then
32 passed/1 skipped after adding invalid-container-state coverage. `git diff
--check` produced no output, but files are still untracked, so that is not a
whitespace check of the new foundation.

## Changed files and next steps

- Added checkout fixture: application, four tests, manifest and README.
- Added sandbox Dockerfile, Docker ignore rules, local package metadata, package
  initializer and runner.
- Added API execution package/routes and registered it in development mode.
- Added unit and opt-in integration tests; updated API pytest markers and added
  safe root discovery excluding benchmark tests.
- Updated root README, AGENTS and architecture documentation; added this record
  and the actual API error evidence JSON.
- Existing health/configuration/logging/error implementations and Day 1 tests
  remain intact. API runtime dependencies did not need additions beyond the local
  standard-library-only runner package.

Next: restore a working Docker Desktop Linux engine, build the trusted image,
run the opt-in integration command from the README, then call the reproduction
endpoint. Confirm `1 failed, 3 passed`, the expected node ID and `IndexError`,
and no leftover containers. These checks must succeed before marking the real
reproduction workflow verified. Do not fix the deliberate benchmark bug yet.
