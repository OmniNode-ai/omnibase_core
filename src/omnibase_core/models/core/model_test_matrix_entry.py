from typing import Any

from pydantic import Field

"""
Test matrix entry model.
"""

from pydantic import BaseModel, Field


class ModelTestMatrixEntry(BaseModel):
    """Test matrix entry for comprehensive testing."""

    id: str
    description: str
    context: str
    expected_result: str
    tags: list[str] = Field(default_factory=list)
    covers: list[str] = Field(default_factory=list)
