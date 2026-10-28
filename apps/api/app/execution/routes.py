"""Local-development-only, synchronous fixture reproduction."""

from threading import Lock
from patchpilot_sandbox.fixtures import FixtureId

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from dataclasses import asdict
from patchpilot_sandbox.runner import Evidence, run_fixture
from app.schemas import ErrorResponse

router = APIRouter(prefix="/api/v1", tags=["local development"])
_execution_lock = Lock()


class ReproductionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    fixture_id: FixtureId


@router.post("/reproductions", response_model=Evidence, description=(
    "Local development only. Runs one curated fixture synchronously; no arbitrary repositories."
), responses={503: {"model": Evidence, "description": "Docker, image, container or cleanup failure"},
              429: {"model": ErrorResponse, "description": "One reproduction is already running"}})
def reproduce(request: ReproductionRequest):
    # A sync route runs in FastAPI's thread pool, leaving the event loop responsive.
    if not _execution_lock.acquire(blocking=False):
        return JSONResponse(status_code=429, content={"error": {
            "code": "reproduction_busy", "message": "A reproduction is already running",
        }})
    try:
        evidence = run_fixture(request.fixture_id)
        if evidence.status == "infrastructure_failure":
            return JSONResponse(status_code=503, content=asdict(evidence))
        return evidence
    finally:
        _execution_lock.release()
