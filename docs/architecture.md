# PatchPilot architecture

## Implemented backend foundation
The FastAPI service exposes `GET /health`, validates environment configuration,
emits JSON application logs, and returns consistent error envelopes. The health
endpoint reports process liveness; it does not verify dependencies or debugging capabilities.

The application factory allows tests to supply settings explicitly. Standard-library logging avoids an extra dependency. The version lives in `app/__init__.py` and is shared by OpenAPI and the health response. Uvicorn retains its own server/access log formatting.

Development mode also exposes `POST /api/v1/reproductions`. A Pydantic Literal
allowlist accepts only the IDs in the reviewed fixture registry; extra input fields are forbidden.
The sync route runs in FastAPI's thread pool with one active execution per API
process. No fixture modules are imported into the host process.

`apps/api/app/execution/routes.py` handles HTTP; the editable Python package in
`services/sandbox-runner` owns Docker CLI orchestration. Keeping this as a local
library avoids an unnecessary new network service. Its source-relative fixture
path requires the monorepo checkout and editable installation for this milestone.
The JSON fixture manifest documents expectations but cannot authorize commands.

## Phase 3 fixture registry
`services/sandbox-runner/patchpilot_sandbox/fixtures.py` is the shared immutable
allowlist for four fixtures. Entries fix the approved source/test files, targeted
test node, expected failure marker/counts, descriptions and examples. The request
Literal and registry are checked for agreement by tests. Discovery at
`GET /api/v1/fixtures` exposes display metadata in every environment without
filesystem scanning or execution. The dashboard loads that endpoint rather than
embedding fixture IDs, source filenames, descriptions or expected counts.

Each debug run selects the registered source path and test plan, binds candidate
copies to their fixture identity, and refuses foreign references or cross-fixture
patches. Verification checks fixture IDs, exact commands, image identity, complete
evidence and per-fixture test counts. Original fixtures remain buggy. Registry
entries, not manifests or user input, authorize files/commands. Docker isolation
and resource restrictions are unchanged. See `adding-fixtures.md` for admission
steps and `phase-3-verification.md` for actual observed results.

```text
Local client -> development-only API -> allowlisted runner -> Docker container
                                                        <- real test output
```

The runner resolves the trusted built image to an immutable ID, creates a locked
down container, attaches with a timeout, inspects exit state, and forcibly removes
the container on success, error or timeout. It distinguishes pytest exits 0/1
from container failures and pytest setup/internal errors. Output capture drains
both streams concurrently, retains bounded evidence, and marks truncation.
The response records execution facts rather than inferring a root cause or
claiming a patch.

## Minimal debugging pipeline
`apps/api/app/debugging` adds a provider Protocol, a Groq HTTP adapter, validated
candidate/report models, a strict single-source-file diff parser, and one-attempt
orchestration. The development-only `/api/v1/debug-runs` route shares the existing
execution lock. It copies only approved fixture files into a disposable directory,
runs a baseline there, validates source references and the diff, then runs the
targeted test and full regression suite in the existing restricted sandbox.
The original fixture is preserved. Source hashes and each execution result are
returned; model output cannot set verification status. One HTTP model call has
a 30-second total deadline; there are no retries or autonomous shell tools.
Real Docker reproduction and deterministic patch verification have passed.
Live Groq-generated patch verification has also passed through the API; see
`mvp-verification.md`. A narrowly scoped adapter canonicalizes single coordinate-free
model hunks only with an exact unique source match, then invokes the unchanged
strict patch application checks. Reports preserve both raw and applied diffs.

## Frontend boundary and CI
The implemented Next.js App Router dashboard lives in `apps/web`. Shared client
context preserves only the latest result in memory across navigation. A native
fetch client uses generated OpenAPI TypeScript types, checks response shapes,
retains structured non-2xx evidence and handles network/request deadlines. It
calls FastAPI directly from the browser through configured local CORS. Only the
public API base URL is embedded in the bundle; provider credentials remain in
the backend. The dashboard has no mock results, persisted history, polling or
invented stage progression. Diff/log text is rendered as escaped text, not HTML.

The API now exposes explicit response/error schemas in OpenAPI; `api.md` is the
frontend contract. CORS permits configured exact origins (local port 3000 by
default), GET/POST and Content-Type, without credentials. It does not replace
authentication. Execution remains synchronous and development-only; the dashboard
must handle busy/error states and only show returned execution evidence.
GitHub Actions runs warning-clean unit tests on Python 3.11/3.12 and real Docker
tests on Ubuntu without Groq credentials. The candidate directory is readable by
the non-root container UID on Linux; its mount remains read-only and only the
existing approved files are copied. The debugging and verification algorithms
and Docker resource/network restrictions are unchanged.

Security flags and Windows commands are described in the root README. They use
Docker's documented [container options](https://docs.docker.com/reference/cli/docker/container/run/)
and [container state inspection](https://docs.docker.com/reference/cli/docker/container/inspect/).
Cleanup is attempted with bounded commands, but cannot be guaranteed if the
daemon is unreachable. Such failures are surfaced explicitly. This design is
only suitable for the reviewed local fixture; Docker control privileges remain
on the API host until execution is moved to a separate trust boundary.

## Planned system
```text
Browser (Next.js) -> FastAPI -> PostgreSQL (jobs, evidence, patches)
                        |
                   Redis / Celery -> Investigation agent -> LLM provider
                                         |
                                  Sandbox runner -> isolated Docker execution
```

The current web app submits the approved fixture and bug descriptions and displays actual diffs and execution reports. General repository references, persistence and job metadata remain future work. Celery workers will eventually run long investigations outside request handlers. The current provider interface uses validated structured JSON and Groq; general tool-calling investigation remains future work.

Execution and verification will remain separate from AI reasoning. The sandbox runner will execute approved test commands against isolated repository snapshots and capture exit codes, output, timeouts, and patch diffs. A generated patch is only a candidate until real verification evidence supports it. Reports must distinguish baseline failures, candidate results, regression results, and checks that could not run.

## Security boundaries and future decisions
- Never run repository code, install repository dependencies, or import repository modules on the API server.
- Repository contents and model output are untrusted inputs, not instructions to the platform.
- Execution environments must receive no API/provider/database credentials and must have strict CPU, memory, process, output, and execution-time limits.
- Before supporting untrusted repositories, define network restrictions, filesystem boundaries, cleanup, and container escape risk mitigation. Docker alone is not a complete hostile-code security boundary.
- Only explicitly reviewed fixtures are supported, using Python/pytest. Authentication, persistence, background processing, stronger isolation and general repository support remain future milestones.

## Folder ownership
`apps/api` owns HTTP configuration and routes; `apps/web` owns presentation; `services/sandbox-runner` owns execution; `benchmarks` contains curated reproducible cases; `infra` will contain deployment configuration; `docs` records design and security decisions; `.github/workflows` holds CI.

This is a modular monorepo, not a commitment to independently deployed microservices. Keep interfaces small and introduce infrastructure only when a milestone requires it.
