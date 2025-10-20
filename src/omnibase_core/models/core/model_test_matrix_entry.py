from typing import Any

from pydantic import Field

"""
Test matrix entry model.
"""

from uuid import UUID

from pydantic import BaseModel


class ModelTestMatrixEntry(BaseModel):
    """Test matrix entry for comprehensive testing."""

    id: UUID
    description: str
    context: str
    expected_result: str
    tags: list[str] = Field(default_factory=list)
    covers: list[str] = Field(default_factory=list)
