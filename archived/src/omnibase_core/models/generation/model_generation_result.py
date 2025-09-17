"""
Generation Result Model

ONEX-compliant model for generation operation results.
"""

from pydantic import BaseModel, Field


class ModelGenerationResult(BaseModel):
    """Result of generation operations."""

    success: bool = Field(description="Whether generation succeeded")
    output_path: str = Field(description="Path to generated files")
    files_generated: list[str] = Field(
        default_factory=list,
        description="List of generated files",
    )
    errors: list[str] = Field(
        default_factory=list,
        description="List of generation errors",
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="List of generation warnings",
    )
    execution_time: float | None = Field(
        default=None,
        description="Execution time in seconds",
    )
