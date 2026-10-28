"""LLM claims are distinct from observed execution evidence."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from patchpilot_sandbox.runner import Evidence
from patchpilot_sandbox.fixtures import FixtureId


class SourceReference(BaseModel):
    model_config = ConfigDict(extra="forbid")
    path: str = Field(min_length=1, max_length=120)
    line: int = Field(ge=1, le=1000)
    quote: str = Field(min_length=1, max_length=500)


class Candidate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    hypothesis: str = Field(min_length=1, max_length=2000)
    references: list[SourceReference] = Field(min_length=1, max_length=8)
    unified_diff: str = Field(min_length=1, max_length=16000)


class DebugRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    fixture_id: FixtureId
    bug_description: str = Field(min_length=1, max_length=2000)


class DebugReport(BaseModel):
    fixture_id: str
    status: Literal["blocked_execution", "baseline_unexpected", "provider_error", "patch_rejected", "verification_failed", "verified"]
    verified: bool = False
    provider: str
    candidate: Candidate | None = None
    model_unified_diff: str | None = None
    baseline: Evidence | None = None
    failing_test: Evidence | None = None
    regression: Evidence | None = None
    source_sha256: dict[str, str] = Field(default_factory=dict)
    patch_attempts: int = 0
    error: str | None = None
