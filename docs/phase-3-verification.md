# Phase 3 multi-fixture verification — 2026-10-28

## Latest: Docker restored and new Groq fix verified

After the user restored Docker, Engine 29.5.2 and the existing sandbox image
were available. Real Docker integration suite: **8 passed, 1 skipped, 128 deselected
in 52.79s**. This confirms reproduction and deterministic candidate verification
for all three new fixtures, plus the existing checkout checks. The deterministic
test models are not claimed as Groq-generated patches.

A genuine API debug run for **shipping-threshold** then returned **HTTP 200**,
`provider=groq`, `status=verified`, `verified=true`, and one candidate attempt:

| Stage | Actual result | Exit code | Runner duration |
| --- | --- | --- | --- |
| Original baseline | 1 failed, 3 passed in 0.18s | 1 | 2.969s |
| Original failing test after patch | 1 passed in 0.10s | 0 | 2.969s |
| Full regression suite after patch | 4 passed in 0.11s | 0 | 2.906s |

Groq changed the shipping threshold comparison from `>` to `>=`. The patch was
validated and applied only to a disposable copy. Image ID:
`sha256:20326611afbc57b002cd32288de563fbc77e93e1f3f18e0ce1f13e7801c1ee32`.
Full actual evidence (exact diff/commands, stdout/stderr, exit codes, timestamps,
durations and image IDs) remains in ignored `.data/phase3-live-shipping.json`.

The first live shipping attempt reproduced the bug but Groq returned HTTP 400;
the API correctly returned HTTP 502 with `provider_error`, `verified=false` and
zero candidate attempts. That report is retained as
`.data/phase3-live-shipping-attempt1.json`. Its precise provider error code was
not captured, so the cause is not claimed. A small diagnostic improvement now
exposes only a fixed whitelist of provider error codes, never provider messages,
failed generations or credentials. Error bodies retain the same byte/time bounds.
Two new mock-transport tests cover safe/unsafe error codes; focused provider suite:
**14 passed in 0.33s**. No automatic model retries or sandbox relaxation were added.

**Final Docker-enabled full suite: 138 passed, 1 skipped in 52.19s**, with
warnings treated as errors. The separate live-Groq pytest case stayed skipped
to avoid another provider call after the real API success. All 12 approved
original source/test/manifest hashes match their pre-run snapshots; the original
checkout fixture remains unchanged. Container/candidate cleanup checks were empty.
Frontend typecheck/lint/build and browser selection checks passed in the earlier
implementation pass; no frontend source changed during this follow-up.

Follow-up commands from root:

```powershell
docker version --format '{{.Server.Version}}'
docker image inspect --format '{{.Id}}' patchpilot-sandbox:day2
.\.venv\Scripts\python.exe -c "import os,pytest; os.environ['PATCHPILOT_RUN_DOCKER_TESTS']='1'; os.environ['PATCHPILOT_RUN_GROQ_TESTS']='0'; raise SystemExit(pytest.main(['-q','-W','error','-m','docker','--maxfail=1']))"
.\.venv\Scripts\python.exe -m pytest -q -W error apps/api/tests/test_groq_provider.py
.\.venv\Scripts\python.exe -c "import os,pytest; os.environ['PATCHPILOT_RUN_DOCKER_TESTS']='1'; os.environ['PATCHPILOT_RUN_GROQ_TESTS']='0'; raise SystemExit(pytest.main(['-q','-W','error']))"
```

The live API request (Uvicorn started from `apps/api` on port 8000):

```powershell
$request = @{ fixture_id = 'shipping-threshold'; bug_description = 'A subtotal of exactly Decimal 50.00 must qualify for free shipping. Preserve the 4.99 fee below the threshold and rejection of negative subtotals.' } | ConvertTo-Json
$response = Invoke-WebRequest -Method Post -Uri http://127.0.0.1:8000/api/v1/debug-runs -ContentType 'application/json' -Body $request -SkipHttpErrorCheck
Set-Content -LiteralPath .data/phase3-live-shipping.json -Value $response.Content -Encoding utf8
```

The initial report was backed up with `Copy-Item` before the deliberate retry.
Original hashes are recorded in ignored `.data/phase3-original-hashes.json` and
compared with hashlib. No key value or authorization header was displayed.
Only `apps/api/app/debugging/provider.py`, `apps/api/tests/test_groq_provider.py`,
this record and the README changed in this follow-up, plus ignored local evidence.
No commits, pushes or deployments occurred. The earlier blocked attempts below
are retained as historical results, not the current state.

## Delivered
Added three deliberate, standard-library-only Python benchmarks alongside the
unchanged original checkout fixture:

| Fixture ID | Category | Bug | Expected original suite |
| --- | --- | --- | --- |
| `shipping-threshold` | Business logic | Strict `>` excludes free shipping at exactly Decimal 50.00 | 1 failed, 3 passed |
| `quantity-bool` | Input validation | `isinstance(True, int)` accepts a boolean quantity | 1 failed, 5 passed |
| `csv-quoted-fields` | Parsing | Naive comma splitting breaks quoted commas/escaped quotes | 1 failed, 3 passed |

These benchmark expectations have now been confirmed by real Docker integration
tests. Every benchmark has source, deterministic failing node, regression tests,
README and manifest. Original source stays buggy; no benchmark test ran on the host.

## Contract and execution changes
`GET /api/v1/fixtures` is read-only and returns `FixtureList`:
`{"fixtures": [FixtureInfo, ...]}`. A `FixtureInfo` includes `fixture_id`, `name`,
`category`, `description`, `example_bug_description`, `language`, `test_framework`,
`expected_failed`, and `expected_passed`. The ID is a four-value Literal in OpenAPI.
Metadata is available even outside development; execution endpoints remain local
development features. No host paths, commands, credentials or directory scanning
are exposed. See `api.md` for field types and all current IDs.

The frozen shared registry fixes approved source/test files, failure markers,
targeted node and expected counts. Requests/manifests cannot authorize commands.
Candidate copies are bound to the fixture identity. Reference and patch checks
reject other fixtures' files, tests, absolute paths and traversal. Verification
now additionally checks response fixture IDs and exact test commands alongside
existing image, output, exit-code and per-fixture count checks.

The dashboard fetches discovery, renders all returned options/examples, sends the
selected ID for both actions, retains selection across navigation, hides stale
results for another fixture, and derives the diff filename from the actual diff.
Discovery failure disables execution and offers a retry. No new frontend or
backend dependency was added. Docker/network/user/resource restrictions are unchanged.

## Initial checks (before Docker was restored)
- Final default backend suite: **128 passed, 9 skipped in 3.12s**, `-W error`, no warnings.
- Original 87 normal tests remain passing; 41 additional unit cases pass.
- Coverage includes read-only discovery, OpenAPI/registry agreement, all four
  accepted IDs, expected manifest counts, contextual references/patches,
  coordinate-free hunks, regression failures, wrong fixture identity, command
  tampering and isolation cleanup. Unit Docker/model responses are clearly mocked.
- Frontend generated API types from the actual running OpenAPI schema.
- `npm.cmd run typecheck`, `npm.cmd run lint`, `npm.cmd run build`: passed.
- `python -m pip check`: no broken requirements.
- Browser production smoke checks passed: live discovery, four options and their
  matching examples, selected-ID requests, navigation state and 390px mobile width.
- Real browser shipping debug request: **HTTP 503, `blocked_execution`, `verified=false`**.
  Its baseline has no test exit code because Docker could not execute anything.
  A real quantity reproduction request also reached the backend with the selected ID.
- Selected real Docker integration attempt: **1 failed, 134 deselected in 1.10s**.
  `test_real_new_fixture_reproduction_api[shipping-threshold]` expected HTTP 200
  but got **503**. The maxfail=1 run stopped there; this is an infrastructure
  failure, not evidence of the deliberate shipping test failing in Docker.
- Nine optional integration cases are in the default suite: the existing three,
  plus three new reproduction and three deterministic candidate-verification cases.
  Their presence/skip is not evidence of real execution success.
- Original checkout source hash is unchanged:
  `d85d9c9aaaf7055db00547aa5a372b341c230274d0e75012962d482764bf3df2`.
  No original checkout files were edited.

## Earlier Docker/Groq blocker (resolved)
The Groq key is configured; only its presence was checked. Docker's Linux engine
was unavailable. One `docker desktop start` attempt failed with the recurring
inference-manager error at `%LOCALAPPDATA%\Docker\run\dockerInference`:
"The file cannot be accessed by the system." No Docker data/settings, WSL
distributions or images were removed. The owned hanging startup CLI was stopped.
The user was asked to restore Docker using the previously successful manual repair.

**At that earlier point, no new fixture had been fixed by Groq and verified in Docker.**
The baseline guard prevented model calls while execution was
unavailable. Prior Phase 2 checkout verification is historical, not reused as
new-fixture evidence. Candidate/refactoring unit tests use test-only deterministic
responses and must not be described as live AI results.

To finish live verification after Docker is restored: build/confirm the existing
image, run the Docker-marked suite, then submit a debug request for e.g.
`shipping-threshold`. Retain the actual report with baseline failure, candidate
diff, targeted/full passing results, image ID and exit codes. Confirm cleanup
and unchanged original hashes before claiming verification.

## Commands executed
From root:

```powershell
.\.venv\Scripts\python.exe -m pytest -q -W error
.\.venv\Scripts\python.exe -m pip check
docker version --format '{{.Server.Version}}'
docker desktop start
.\.venv\Scripts\python.exe -c "import os,pytest; os.environ['PATCHPILOT_RUN_DOCKER_TESTS']='1'; os.environ['PATCHPILOT_RUN_GROQ_TESTS']='0'; raise SystemExit(pytest.main(['-q','-W','error','-m','docker','-k','real_new_fixture_reproduction_api','--maxfail=1']))"
node .data/phase3-browser.cjs
Get-FileHash benchmarks/fixtures/checkout-empty-cart/checkout/__init__.py -Algorithm SHA256
```

From `apps/web`:

```powershell
npm.cmd run generate:api
npm.cmd run typecheck
npm.cmd run lint
npm.cmd run build
npm.cmd run start
```

From `apps/api`:

```powershell
..\..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The local browser script uses the host's existing Playwright/Chromium installation;
it is an ignored QA artifact, not a portable repository test dependency. Actual
blocked response and screenshot are in ignored `.data/phase3-browser-debug.json`
and `.data/phase3-debug.png`. Logs were inspected for the Docker startup error;
credential values and provider authorization headers were never printed.
An initial documentation patch failed context validation without changing files;
it was reapplied with the correct context. No commits, pushes or deployments occurred.

## Source files changed
- New: four files (source, test, README, manifest) under each of
  `benchmarks/fixtures/shipping-threshold`, `quantity-bool`, `csv-quoted-fields`.
- New: `services/sandbox-runner/patchpilot_sandbox/fixtures.py`.
- Updated: `services/sandbox-runner/patchpilot_sandbox/runner.py`.
- New: `apps/api/app/execution/fixtures.py` and `apps/api/tests/test_multi_fixtures.py`.
- Updated: `apps/api/app/main.py`, `execution/routes.py`, `debugging/models.py`,
  `debugging/patches.py`, `debugging/provider.py`, `debugging/workflow.py`.
- Updated tests: `test_debugging.py`, `test_groq_provider.py`, `test_docker_integration.py`.
- Updated frontend: `src/lib/api.ts`, generated `api-schema.d.ts`,
  `src/components/workspace.tsx`, `run-workspace.tsx`, `results.tsx`, `shell.tsx`,
  and `src/app/page.tsx`.
- Updated root `AGENTS.md`, `README.md`, `docs/api.md`, `docs/architecture.md`.
- New: `docs/adding-fixtures.md` and this verification record.

The earlier next step (restore Docker and complete live checks) is now done. The
review process for future approved fixtures is documented in `adding-fixtures.md`.
General repositories, authentication, history and deployment remain out of scope.
