# Phase 2 dashboard verification — 2026-10-27

## Implemented
- `/`: real health check/refresh, approved fixture, available actions and the latest
  actual response held in this browser session. No fake metrics/history.
- `/debug`: fixture selector, required bounded bug description, example description,
  single active request, indeterminate loading, complete returned investigation report.
- `/reproduce`: separate tests-only action with real execution evidence.
- Shared responsive dark shell, sidebar/mobile navigation, status badges, escaped
  logs and source references, unified diff view/copy, original model diff, source hashes.
- Direct browser → FastAPI fetch client using types generated from the live
  `/openapi.json` and response-shape guards. Structured 422/502/503 reports remain
  visible. Shared envelopes, busy responses, timeouts and network errors are distinct.
- Only `NEXT_PUBLIC_API_BASE_URL` is used by the frontend. No Groq credentials,
  provider SDK, API proxy, backend algorithm changes or fabricated results.

## Actual checks and results

| Check | Result |
| --- | --- |
| Generate types from running FastAPI | Passed, `openapi-typescript` 7.13.0 |
| TypeScript (`npm.cmd run typecheck`) | Passed |
| ESLint (`npm.cmd run lint`) | Passed, zero lint warnings |
| Final production build | Passed; `/`, `/debug`, `/reproduce` prerendered |
| Production HTTP smoke check | Dashboard returned 200 |
| npm dependency audit during install | 0 vulnerabilities reported |
| Backend default (`-W error`) | 87 passed, 3 skipped in 2.57s |
| Backend Docker-enabled (`-W error`) | 89 passed, 1 skipped in 14.89s |
| Real browser reproduction POST | HTTP 200, exit 1, exactly 1 failed / 3 passed |
| Real browser Groq debug POST | HTTP 200, `provider=groq`, `verified=true` |
| Browser-triggered baseline | Exit 1; 1 failed, 3 passed in 0.20s |
| Browser-triggered patched failing test | Exit 0; 1 passed in 0.11s |
| Browser-triggered full regression | Exit 0; 4 passed in 0.11s |
| Cleanup | No temporary containers; original fixture hash unchanged |

The browser clicked the actual reproduction/debug forms; native fetch crossed
local CORS to the running API. Both loading messages and disabled submit buttons
were checked during real requests. The original source SHA256 stayed
`d85d9c9aaaf7055db00547aa5a372b341c230274d0e75012962d482764bf3df2`.

Actual responses are saved locally in ignored `.data/frontend-reproduction.json`
and `.data/frontend-debug-report.json`. Screenshots are in `.data/dashboard-desktop.png`,
`.data/dashboard-mobile.png`, `.data/frontend-debug-result.png`, and
`.data/frontend-debug-mobile.png`. No raw report was exported to public hosting.

The first browser smoke script successfully completed the real run, then failed
its mobile overflow assertion. The grid's minimum-width behavior was fixed.
Replaying the already captured genuine report confirmed document width 390px at
a 390px viewport, without another Groq call. Long commands/diffs remain inside
their own horizontal scroll areas. Desktop (1440px) and mobile layouts were viewed.

Separate **synthetic transport-only** browser tests checked Docker-unavailable
503, provider-error 502, rejected-patch 422, unverified 200, shared busy 429, and
network failure. They passed on the final production build with no browser runtime
exceptions or mobile body overflow. These simulated errors are not AI/execution
evidence and are not bundled into the application.

## Tooling decisions and limitations
No existing JavaScript manifest/lockfile existed, so npm was selected. Next.js
16.4.3, React 19.3.1 and Tailwind 4.3.3 are locked by `package-lock.json`. Existing
backend code and dependencies were untouched. A generated Next.js `apps/web/AGENTS.md`
was retained and its installed framework guidance reviewed.

ESLint 10 was tried but the current Next lint plugins reject its peer range.
The final compatible ESLint 9.39.5 tree passes lint; npm emits an upstream
deprecation notice for that development tool. Revisit it when the lint plugins
support ESLint 10. Initial optional-WASM install cleanup produced an EPERM warning
on Windows; install, typecheck, lint and builds still succeeded. No overrides or
legacy-peer-dependency flags remain in the project.

In-app browser and computer-use kernels could not initialize (`failed to write
kernel assets`). QA used the already installed Playwright runtime and existing
Chromium headless executable, without installing a browser or adding a browser
test framework to production dependencies. Local QA scripts are ignored under
`.data`; the initial browser launch needed its installed executable path corrected.

No persistence, history API, streaming/progress API, arbitrary repository input,
authentication or deployment is introduced. Browser reload clears session state.
Aborting/timing out a request does not cancel server execution. A live Groq test
was not repeated in the backend suite because the real browser run already proved
that path. Hosted frontend CI and a broad accessibility/browser matrix were not run.

## Commands executed
Backend (root):

```powershell
.\.venv\Scripts\python.exe -m pytest -q -W error
.\.venv\Scripts\python.exe -c "import os,pytest; os.environ['PATCHPILOT_RUN_DOCKER_TESTS']='1'; os.environ['PATCHPILOT_RUN_GROQ_TESTS']='0'; raise SystemExit(pytest.main(['-q','-W','error']))"
docker ps -a --filter label=patchpilot.reproduction=day2 --format '{{.Names}}'
Get-FileHash benchmarks/fixtures/checkout-empty-cart/checkout/__init__.py -Algorithm SHA256
```

API server from `apps/api`:

```powershell
..\..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Frontend from `apps/web`:

```powershell
npm.cmd install
npm.cmd run generate:api
npm.cmd run typecheck
npm.cmd run lint
npm.cmd run build
npm.cmd ls --depth=0
npm.cmd run start
# Development server was also exercised during the responsive fix:
npm.cmd run dev
```

Local browser QA from root:

```powershell
node .data/frontend-smoke.cjs
node .data/frontend-layout-check.cjs
node .data/frontend-errors.cjs
git diff --check
```

These scripts use the host's bundled Playwright and installed Chromium path; they
are local verification artifacts rather than portable project test commands.
The first script's final nonzero exit was the subsequently fixed mobile assertion.
The second/third scripts passed against the final production build. npm install
was rerun while choosing a compatible lint version; final type/lint/build passed.
`git diff --check` had no output, but the project is still untracked, so it does
not validate all new files. No commits, pushes or deployments occurred.

## Exact source changes
New under `apps/web`:

```text
.env.example
AGENTS.md                    (Next.js generated guidance)
package.json
package-lock.json
tsconfig.json
next-env.d.ts
postcss.config.mjs
eslint.config.mjs
src/app/layout.tsx
src/app/globals.css
src/app/page.tsx
src/app/debug/page.tsx
src/app/reproduce/page.tsx
src/components/icon.tsx
src/components/workspace.tsx
src/components/shell.tsx
src/components/run-workspace.tsx
src/components/results.tsx
src/lib/api.ts
src/lib/api-schema.d.ts       (generated from the real API)
```

Removed `apps/web/.gitkeep`. Updated root `AGENTS.md`, `README.md`, and
`docs/architecture.md`; added this record. `.data` also contains the ignored local
QA scripts, screenshots and actual reports described above. No API/sandbox source
files were changed.

See the root README's **Run the Phase 2 dashboard** section for exact two-terminal
startup instructions (`npm.cmd ci` for a fresh install). Next milestone: a small,
portable frontend test setup/CI and usability feedback before extending backend scope.
