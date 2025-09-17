"""
Generation Event Data Model

ONEX-compliant model for generation event data.
"""

from pydantic import BaseModel, Field


class ModelGenerationEventData(BaseModel):
    """Event data for generation workflows."""

    contract_path: str = Field(description="Path to contract file")
    output_path: str | None = Field(
        default=None,
        description="Output directory path",
    )
    tool_name: str | None = Field(
        default=None,
        description="Tool name for generation",
    )
    validation_mode: str | None = Field(
        default="strict",
        description="Validation mode: strict or permissive",
    )
    include_tests: bool | None = Field(
        default=True,
        description="Whether to generate tests",
    )
    include_docs: bool | None = Field(
        default=True,
        description="Whether to generate documentation",
    )
