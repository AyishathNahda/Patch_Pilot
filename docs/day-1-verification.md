# Day 1 verification — 2026-10-27

> Publication note: machine-local paths are redacted. Use the current README for runnable setup commands.

## Results
- Runtime: Python 3.12.14 in a repository-local `.venv` (ignored by Git).
- Dependency installation: successful.
- `pytest`: **7 passed, 1 warning in 0.87s**.
- Warning: Starlette's test client references deprecated `anyio.abc.BlockingPortal`; the dependency recommends `anyio.from_thread.BlockingPortal`. This originates in a dependency, not application code. Revisit compatible dependency versions before CI; do not suppress it silently.
- `pip check`: **No broken requirements found.**
- Uvicorn: application startup completed; real HTTP `/health` returned **200** and `{"service":"patchpilot-api","status":"ok","version":"0.1.0"}`.
- Ctrl+C: application shutdown completed. The terminal wrapper reported exit code 1 after interruption; server logs show completed shutdown.
- `git diff --check`: no output. Because the foundation files are new/untracked, this command does not validate their whitespace.
- No commits, pushes, deployments, pull requests, or untrusted-code execution occurred.
- Python 3.11 was not available and was not tested. No browser/frontend or future infrastructure was tested.

## Commands executed
Commands below are PowerShell, shown with the working directory used. File creation used the patch tool. A desktop dependency-discovery tool identified the bundled Python runtime.

Repository root (`<repository-root>`), initial inspection:
```powershell
Get-Location
Get-ChildItem -Force
rg --files -g AGENTS.md -g pyproject.toml -g requirements.txt -g README.md
python --version
py -0p
git status --short
Get-Command uv -ErrorAction SilentlyContinue
Get-ChildItem .. -Filter AGENTS.md -Force
& '<local-python-3.12>' --version
```

Root, virtual environment and installation:
```powershell
& '<local-python-3.12>' -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r apps\api\requirements.txt
```

From `apps/api`, tests and server:
```powershell
..\..\.venv\Scripts\python.exe -m pytest -q
..\..\.venv\Scripts\python.exe -m pip check
..\..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8765
```

From the root, while Uvicorn was running:
```powershell
$healthResponse = Invoke-WebRequest http://127.0.0.1:8765/health
$healthResponse.StatusCode
$healthResponse.Content
git diff --check
git status --short
rg --files --hidden -g '!.git/**' -g '!.venv/**' -g '!**/__pycache__/**' -g '!**/.pytest_cache/**'
```

Uvicorn was stopped with Ctrl+C. An earlier attempt to run a PowerShell `Start-Process` background startup/check/cleanup script was rejected by tool policy before execution; the foreground command above replaced it. No background server was left running.

## Next step
Day 2 suggestion: add CI for Python 3.11 and 3.12 and review compatible dependency updates. Database, AI, frontend and sandbox work require separate milestones.
