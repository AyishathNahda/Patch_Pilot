"""Read-only public metadata; registry remains the sole execution authority."""

from fastapi import APIRouter
from pydantic import BaseModel
from patchpilot_sandbox.fixtures import FIXTURES, FixtureId

router = APIRouter(prefix="/api/v1", tags=["fixtures"])


class FixtureInfo(BaseModel):
    fixture_id: FixtureId
    name: str
    category: str
    description: str
    example_bug_description: str
    language: str = "python"
    test_framework: str = "pytest"
    expected_failed: int
    expected_passed: int


class FixtureList(BaseModel):
    fixtures: list[FixtureInfo]


@router.get("/fixtures", response_model=FixtureList)
def list_fixtures() -> FixtureList:
    return FixtureList(fixtures=[FixtureInfo(
        fixture_id=item.fixture_id, name=item.name, category=item.category,
        description=item.description, example_bug_description=item.example_bug_description,
        expected_failed=item.expected_failed, expected_passed=item.expected_passed,
    ) for item in FIXTURES.values()])
