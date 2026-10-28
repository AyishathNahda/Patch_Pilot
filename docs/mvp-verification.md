# Minimal debugging MVP verification — 2026-10-27

## Latest: real Groq → patch → Docker verification succeeded

The user configured the key locally. Only a boolean presence check was printed;
no credential or authorization header was displayed. The real development API
returned **HTTP 200**, `provider=groq`, `status=verified`, `verified=true`, and one
candidate attempt for the successful run.

- Original baseline: expected failing checkout suite, exit code 1.
- Patched original failing test: **1 passed in 0.08s**, exit code 0.
- Patched full regression suite: **4 passed in 0.11s**, exit code 0.
- All test execution occurred in the existing restricted Docker sandbox.
- Original fixture SHA256 stayed
  `d85d9c9aaaf7055db00547aa5a372b341c230274d0e75012962d482764bf3df2`.
- Post-run container listing and `.data/candidates` listing were empty.
- Final Docker-enabled suite: **80 passed, 1 skipped, 1 warning in 15.13s**.
- Default suite: **78 passed, 3 skipped, 1 warning in 1.57s**.
- Focused provider/workflow tests: **45 passed, 1 warning in 1.37s**.

The separate live-Groq pytest case was not enabled, avoiding another paid model
call after real API success. Its skip does not replace the actual API evidence.
The existing Starlette/AnyIO deprecation warning remains.

The actual complete report, including commands, timestamps, durations, image ID,
stdout/stderr, original model diff and applied canonical diff, is saved locally
in ignored `.data/live-groq-report.json`. Earlier rejected/provider-error reports
are also retained in `.data`. No raw report was exported to tracked docs.

### Implementation corrections found by real execution
Initial Groq candidates used bare `@@` hunks without numeric coordinates. The
validator rejected them with HTTP 422. Another attempt returned a safe generic
provider error (HTTP 502); no test success was inferred from it.

The prompt now explicitly requires numeric coordinates. Because the model still
produced coordinate-free hunks, a narrow conversion was added: approved file
headers, one hunk, bounded text, valid line prefixes, and exactly one full-line
old-text match are required. A standard diff is generated from that match and
then checked by the existing strict patcher. Missing/ambiguous context, extra
files and unsupported syntax remain rejected. Six new unit cases cover this
conversion. Provider errors now distinguish HTTP status, invalid JSON and schema
failure without revealing provider bodies or secrets. No sandbox restrictions
were relaxed.

The genuine model change applied to the disposable copy was:

```diff
-    subtotal = prices[0] + sum(prices[1:], Decimal("0"))
+    subtotal = sum(prices, Decimal("0"))
```

Files changed: `apps/api/app/debugging/provider.py`, `patches.py`, `models.py`,
`workflow.py`; `apps/api/tests/test_groq_provider.py`, `test_debugging.py`;
`README.md`, `docs/architecture.md`, and this record. No original fixture/test,
Docker configuration or dependency changes were needed.

### Actual verification commands

Uvicorn was started from `apps/api` and restarted after implementation changes:

```powershell
..\..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8765
```

The actual HTTP request, from root:

```powershell
$reportResponse = Invoke-WebRequest -Method Post -Uri http://127.0.0.1:8765/api/v1/debug-runs -ContentType 'application/json' -Body '{"fixture_id":"checkout-empty-cart","bug_description":"An empty shopping cart should return Decimal zero rather than raising IndexError. Preserve discounts and existing validation."}' -SkipHttpErrorCheck
$reportResponse.StatusCode
Set-Content -LiteralPath .data/live-groq-report.json -Value $reportResponse.Content -Encoding utf8
```

Final checks, from root:

```powershell
.\.venv\Scripts\python.exe -m pytest -q apps/api/tests/test_groq_provider.py
.\.venv\Scripts\python.exe -m pytest -q apps/api/tests/test_debugging.py apps/api/tests/test_groq_provider.py
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -c "import os,pytest; os.environ['PATCHPILOT_RUN_DOCKER_TESTS']='1'; raise SystemExit(pytest.main(['-q']))"
docker ps -a --filter label=patchpilot.reproduction=day2 --format '{{.Names}}'
Get-FileHash benchmarks/fixtures/checkout-empty-cart/checkout/__init__.py -Algorithm SHA256
Get-ChildItem .data/candidates -Force
```

Automatic approval review rejected combined credential-check/export and combined
cleanup/test commands before execution, giving only "blocked by policy". No
credential value was displayed. Raw evidence remains ignored; simple read-only
cleanup checks and tests using a process-local opt-in succeeded separately.
A report backup first used the wrong working directory and failed without
modifying files; it was then copied correctly from root. No commits/pushes or
deployments occurred. The historical sections below retain prior blocked results.

## Latest verification: real Docker passed, live AI pending

Docker Desktop is restored. The existing sandbox built successfully without code
changes. The original fixture genuinely produced **1 failed, 3 passed**, exit 1,
through the reproduction API. See `day-2-api-evidence.json` for actual evidence.

Both real Docker integration tests passed: original buggy checkout and a
**deterministic test-only candidate** run through baseline, targeted and full
regression verification. Thus the patched targeted test and all four regression
tests passed in actual containers for that deterministic candidate. This was
**not an LLM-generated patch**.

Final suite with `PATCHPILOT_RUN_DOCKER_TESTS=1`: **74 passed, 1 skipped,
1 warning in 14.18s**. The skipped test is live Groq plus Docker. The existing
Starlette/AnyIO warning remains. Containers were cleaned up, and the original
fixture hash is unchanged. No sandbox security controls were weakened.

`GROQ_API_KEY` remains absent from both the host environment and `apps/api/.env`.
Only key presence was inspected; no value was displayed. The user has been asked
to configure it in the ignored API `.env` file. No real model request, real
AI-generated diff, or AI-fix verification occurred. The prior blocked debug
report in `.data/latest-debug-report.json` is historical, not a new run.

To finish: set the real key locally, start the API from `apps/api`, and submit
one `/api/v1/debug-runs` request as in README. Save its complete report and confirm
baseline failure, targeted pass, regression pass, original hash and cleanup.
The historical diagnostic record follows.

## Observed status
- Final suite: **72 passed, 3 skipped, 1 warning in 1.54s**, Python 3.12.
- Focused new model/workflow tests initially: 37 passed in 1.22s.
- Focused workflow/provider/runner tests after boundary additions: 65 passed in 1.55s.
- `python -m pip check`: no broken requirements.
- Warning: existing Starlette/AnyIO `BlockingPortal` deprecation.
- Real Uvicorn: started, served requests, shut down after Ctrl+C.
- Real `/health`: healthy. Real reproduction: HTTP 503, infrastructure failure.
- Real `/api/v1/debug-runs`: HTTP 503, `verified=false`, zero patch attempts,
  no model call. Baseline image check failed after 5.172 seconds. The actual report
  is in ignored `.data/latest-debug-report.json`; the temporary candidate directory
  was removed, confirmed by an empty `.data/candidates` listing.
- Docker was **not restored**. The bug was **not reproduced in a real container**.
  No real AI patch was generated, tested or verified. No Groq key was available
  in the environment or `apps/api/.env`; only presence was checked, never values.
- Three integration tests were skipped: real buggy fixture, deterministic candidate
  with real Docker, and live Groq with real Docker. Unit tests mock these boundaries.
- No new dependency, commit, push, PR, deployment or system-settings change.

## Docker diagnostics and manual blocker
One bounded diagnostic pass found Docker CLI 29.5.2 and selected `desktop-linux`
context. Daemon and Desktop-status queries each timed out after 8 seconds; owned
diagnostic CLI processes were terminated. WSL 2.7.3.0 is installed; its default is
WSL2, with a stopped `docker-desktop` v2 distribution. `WslService`, `vmcompute`,
and `hns` run; `com.docker.service` is stopped/manual. Desktop/backend processes
exist but do not provide a functioning Linux engine. A stopped helper service
alone does not establish the cause.

Docker Desktop 4.75.0's backend log identifies the blocker: inference-manager
initialization cannot remove/open `%LOCALAPPDATA%\Docker\run\dockerInference`.
That entry exists as an Archive/ReparsePoint, not a directory. A stale socket is
a likely explanation, matching [Docker issue 448](https://github.com/docker/desktop-feedback/issues/448),
but removal/restart has not been tested here.

The user explicitly approved quitting Desktop, removing **only that socket** and
restarting. Automatic approval review rejected the combined command as "blocked
by policy" before execution. No part of the repair command ran. No factory reset,
WSL uninstall, Docker-data deletion, prune or settings modification was performed.

Manual next step: quit Docker Desktop from its tray menu. In PowerShell run:

```powershell
Remove-Item -LiteralPath "$env:LOCALAPPDATA\Docker\run\dockerInference" -Force
```

Open Docker Desktop again and run `docker version`; both client and server must
respond. If the removal reports access denied, perform that exact one-file command
in an Administrator PowerShell window after quitting Desktop. No system restart
has been established as necessary. If removal still fails, retain the error and
use [Docker diagnostics](https://docs.docker.com/desktop/troubleshoot-and-support/troubleshoot/)
rather than deleting anything else.

## Implementation and files
New:
- `apps/api/app/debugging/__init__.py`
- `apps/api/app/debugging/models.py`: validated hypothesis, source references, request and report.
- `apps/api/app/debugging/provider.py`: provider Protocol, bounded Groq JSON request; no mock in production.
- `apps/api/app/debugging/patches.py`: exact unified hunks for one source file; syntax-only AST validation.
- `apps/api/app/debugging/workflow.py`: snapshot, baseline, one proposal, patch, targeted/full Docker checks.
- `apps/api/app/debugging/routes.py`: local-only HTTP integration and shared execution lock.
- `apps/api/tests/test_debugging.py`, `apps/api/tests/test_groq_provider.py`.
- This verification record.

Modified:
- `services/sandbox-runner/patchpilot_sandbox/runner.py`: approved disposable copies,
  targeted test command, reuse of existing container restrictions.
- `apps/api/app/config.py`, `apps/api/app/main.py`, `apps/api/.env.example`:
  secret settings, provider model and development-only route registration.
- `apps/api/tests/test_reproductions.py`, `apps/api/tests/test_docker_integration.py`:
  candidate sandbox boundaries and opt-in real execution tests.
- `README.md`, `docs/architecture.md`: minimal workflow and run instructions.

The original fixture and its tests were not modified. Source/test snapshots have
hashes in the debug report. A patch cannot modify tests, choose commands or mount
paths. Verification requires the expected failing baseline, targeted `1 passed`,
full `4 passed`, successful exit codes, the same image ID and complete execution
evidence. Cleanup failure clears verification. Model output alone cannot verify.

## Commands used and how to rerun
Read `AGENTS.md`, `README.md`, `docs/day-2-verification.md`, the runner and API code
before editing. Diagnostic commands, each CLI/WSL query bounded to 8 seconds:

```powershell
docker --version
docker context ls
docker version
docker desktop status
wsl --status
wsl --list --verbose
wsl --version
Get-Service -Name 'com.docker.service','WslService','LxssManager','vmcompute','hns' -ErrorAction SilentlyContinue
Get-Process -Name 'Docker Desktop','com.docker.backend','vmmemWSL' -ErrorAction SilentlyContinue
Get-Content "$env:LOCALAPPDATA\Docker\log\host\com.docker.backend.exe.log" -Tail 20
Get-Item "$env:LOCALAPPDATA\Docker\run\dockerInference" -Force
```

Root test commands actually run:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pytest -q apps/api/tests/test_debugging.py apps/api/tests/test_groq_provider.py
.\.venv\Scripts\python.exe -m pytest -q apps/api/tests/test_debugging.py apps/api/tests/test_groq_provider.py apps/api/tests/test_reproductions.py
.\.venv\Scripts\python.exe -m pip check
```

Actual HTTP smoke test used Uvicorn on port 8765, then PowerShell 7:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir apps/api --host 127.0.0.1 --port 8765
# In another root shell:
$debugResponse = Invoke-WebRequest -Method Post -Uri http://127.0.0.1:8765/api/v1/debug-runs -ContentType 'application/json' -Body '{"fixture_id":"checkout-empty-cart","bug_description":"Empty cart should return zero"}' -SkipHttpErrorCheck
$debugResponse.StatusCode
$debugResponse.Content
Set-Content -LiteralPath .data/latest-debug-report.json -Value $debugResponse.Content -Encoding utf8
$reproResponse = Invoke-WebRequest -Method Post -Uri http://127.0.0.1:8765/api/v1/reproductions -ContentType 'application/json' -Body '{"fixture_id":"checkout-empty-cart"}' -SkipHttpErrorCheck
$reproResponse.StatusCode
$reproResponse.Content
Invoke-RestMethod http://127.0.0.1:8765/health
Get-ChildItem .data/candidates -Force
```

The HTTP check occurred before the final provider configuration/deadline refinements;
the full unit suite passed after them. No live provider call occurred. Uvicorn's
terminal wrapper returned 1 on Ctrl+C, with successful application shutdown logs.

After manually restoring Docker, follow README commands to build the sandbox and
enable `PATCHPILOT_RUN_DOCKER_TESTS=1`. Set the real key in ignored `apps/api/.env`
and also enable `PATCHPILOT_RUN_GROQ_TESTS=1` for the live test. Then start the API
from `apps/api` and call `/api/v1/debug-runs`. Inspect container cleanup with:

```powershell
docker ps -a --filter label=patchpilot.reproduction=day2
```

Next milestone: obtain real baseline, real AI candidate and passing Docker
verification evidence before adding more features. General repositories, arbitrary
tools, frontend, persistence and queues remain outside this MVP.
