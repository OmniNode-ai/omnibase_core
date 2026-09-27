# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Test matrix entry model.
"""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ModelTestMatrixEntry(BaseModel):
    """Test matrix entry for comprehensive testing."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    description: str
    context: str
    expected_result: str
    tags: list[str] = Field(default_factory=list)
    covers: list[str] = Field(default_factory=list)
