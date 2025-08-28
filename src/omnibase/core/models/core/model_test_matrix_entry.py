"""
Test matrix entry model.
"""

from typing import List

from pydantic import BaseModel, Field


class ModelTestMatrixEntry(BaseModel):
    """Test matrix entry for comprehensive testing."""

    id: str
    description: str
    context: str
    expected_result: str
    tags: List[str] = Field(default_factory=list)
    covers: List[str] = Field(default_factory=list)
