"""
Generation Event Data Model

ONEX-compliant model for generation event data.
"""

from typing import Optional

from pydantic import BaseModel, Field


class ModelGenerationEventData(BaseModel):
    """Event data for generation workflows."""

    contract_path: str = Field(description="Path to contract file")
    output_path: Optional[str] = Field(
        default=None, description="Output directory path"
    )
    tool_name: Optional[str] = Field(
        default=None, description="Tool name for generation"
    )
    validation_mode: Optional[str] = Field(
        default="strict", description="Validation mode: strict or permissive"
    )
    include_tests: Optional[bool] = Field(
        default=True, description="Whether to generate tests"
    )
    include_docs: Optional[bool] = Field(
        default=True, description="Whether to generate documentation"
    )
