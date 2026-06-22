# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Contract-side workflow metadata model (OMN-12835).

Descriptive metadata for a contract-declared workflow definition.

Strict typing is enforced: No Any types allowed in implementation.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelContractWorkflowMetadata(BaseModel):
    """Descriptive metadata for a contract-declared workflow definition."""

    workflow_name: str = Field(
        description="Human-readable workflow name",
    )

    description: str | None = Field(
        default=None,
        description="Optional workflow description",
    )

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )
