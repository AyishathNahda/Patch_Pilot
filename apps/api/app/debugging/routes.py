"""Local-only entry point; no client-provided model, patch, paths or commands."""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from app.config import Settings
from app.debugging.models import DebugReport, DebugRequest
from app.debugging.provider import GroqProvider, ModelProvider
from app.debugging.workflow import debug_fixture
from app.execution.routes import _execution_lock
from app.schemas import ErrorResponse

router = APIRouter(prefix="/api/v1", tags=["local development"])


def get_provider(request: Request) -> ModelProvider:
    config: Settings = request.app.state.settings
    return GroqProvider(config.groq_api_key, config.groq_model)


@router.post("/debug-runs", response_model=DebugReport, description=(
    "Local development only. One curated fixture, one model proposal, Docker-only verification."
), responses={
    422: {"model": DebugReport | ErrorResponse, "description": "Patch rejected or invalid request"},
    429: {"model": ErrorResponse, "description": "Another execution is active"},
    502: {"model": DebugReport, "description": "Model provider failure"},
    503: {"model": DebugReport, "description": "Execution unavailable"},
})
def debug_run(request: DebugRequest, provider: ModelProvider = Depends(get_provider)):
    if not _execution_lock.acquire(blocking=False):
        return JSONResponse(status_code=429, content={"error": {
            "code": "reproduction_busy", "message": "An execution is already running",
        }})
    try:
        report = debug_fixture(request, provider)
        status = {"blocked_execution": 503, "provider_error": 502, "patch_rejected": 422}.get(report.status, 200)
        return JSONResponse(status_code=status, content=report.model_dump(mode="json"))
    finally:
        _execution_lock.release()
