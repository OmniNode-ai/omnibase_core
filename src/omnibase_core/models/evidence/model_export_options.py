"""Export options for evidence rendering.

This module provides configuration options for customizing evidence export
output across different formats (JSON, Markdown, CLI, HTML).

Thread Safety:
    ModelExportOptions is immutable (frozen=True) after creation,
    making it thread-safe for concurrent read access.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelExportOptions(BaseModel):
    """Options for export customization.

    Controls what data is included and how it's formatted in exports.

    Thread Safety:
        This model is immutable (frozen=True) and thread-safe.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    include_raw_data: bool = Field(
        default=False,
        description="Include raw comparison data in output",
    )
    include_timestamps: bool = Field(
        default=True,
        description="Include generation timestamps in output",
    )
    max_examples: int = Field(
        default=5,
        ge=0,
        le=100,
        description="Maximum number of example violations to include",
    )
    verbose: bool = Field(
        default=False,
        description="Include additional detail in output",
    )
    color_enabled: bool = Field(
        default=True,
        description="Enable ANSI colors in CLI output",
    )
    indent_size: int = Field(
        default=2,
        ge=0,
        le=8,
        description="Indentation size for JSON/structured output",
    )


__all__ = ["ModelExportOptions"]
