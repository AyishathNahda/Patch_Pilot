# Frontend readiness verification — 2026-10-27

## Changes
The dependency warning originated in Starlette 0.46.2's import-time annotation
`anyio.abc.BlockingPortal`. AnyIO 4.15's lazy aliases emit a deprecation warning
there. Pinning the preceding patch release, AnyIO 4.14.2, restores compatibility
without changing FastAPI/Starlette or suppressing warnings. `pip check` passes.

Added explicit local-browser CORS settings and tests, shared OpenAPI error models,
accurate execution/report error response documentation, an API reference and CI.
On Linux the temporary candidate directory now has mode 0755 so UID 65532 can
read it; its fixture mount remains read-only. No model, patch validation,
verification or sandbox security restrictions changed.

## Actual local results (Python 3.12, Windows)
- Focused CORS/OpenAPI tests: **9 passed in 0.77s**, warnings treated as errors.
- Default full suite: **87 passed, 3 skipped in 2.32s**, no warnings.
- Docker-enabled full suite: **89 passed, 1 skipped in 16.32s**, no warnings.
- `pip check`: **No broken requirements found.**
- Temporary Docker container listing: empty.
- Original fixture hash remains
  `d85d9c9aaaf7055db00547aa5a372b341c230274d0e75012962d482764bf3df2`.
- The live Groq integration case was deliberately skipped. The earlier genuine
  AI success remains recorded in `mvp-verification.md`; no new model request was
  required for this infrastructure/contract milestone.
- GitHub Actions and Python 3.11 have not been run here. The workflow will validate
  both Python versions and Linux behavior after an approved push. Workflow design
  follows the official checkout/setup-python actions; remote success is not claimed.

## Commands executed from root
```powershell
.\.venv\Scripts\python.exe -m pip install -r apps/api/requirements.txt
.\.venv\Scripts\python.exe -m pytest -q -W error apps/api/tests/test_frontend_contract.py
.\.venv\Scripts\python.exe -m pytest -q -W error
.\.venv\Scripts\python.exe -c "import os,pytest; os.environ['PATCHPILOT_RUN_DOCKER_TESTS']='1'; os.environ['PATCHPILOT_RUN_GROQ_TESTS']='0'; raise SystemExit(pytest.main(['-q','-W','error']))"
.\.venv\Scripts\python.exe -m pip check
docker ps -a --filter label=patchpilot.reproduction=day2 --format '{{.Names}}'
Get-FileHash benchmarks/fixtures/checkout-empty-cart/checkout/__init__.py -Algorithm SHA256
git diff --check
```

`git diff --check` had no output; existing project files are still untracked, so
that command does not validate their whitespace. No commits, pushes, deployments,
credential reads or live provider calls were performed in this milestone.

## Exact files changed
- `.github/workflows/backend.yml` (new)
- `apps/api/requirements.txt`
- `apps/api/.env.example`
- `apps/api/app/config.py`
- `apps/api/app/main.py`
- `apps/api/app/schemas.py` (new)
- `apps/api/app/execution/routes.py`
- `apps/api/app/debugging/routes.py`
- `apps/api/tests/test_frontend_contract.py` (new)
- `apps/api/tests/test_reproductions.py`
- `services/sandbox-runner/patchpilot_sandbox/runner.py`
- `README.md`
- `docs/api.md` (new)
- `docs/architecture.md`
- `docs/frontend-readiness-verification.md` (new)

## Next milestone
Build a Next.js dashboard using the documented OpenAPI contract, one typed fetch
client, an explicit busy state, an evidence timeline derived from returned results,
a diff viewer and a verification summary. Keep credentials on the backend and do
not imply streaming or persisted run history: those endpoints do not exist yet.
