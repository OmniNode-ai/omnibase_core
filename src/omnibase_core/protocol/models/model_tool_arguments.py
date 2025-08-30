"""Tool arguments model for protocol tool."""

from pydantic import BaseModel, Field


class ModelToolArguments(BaseModel):
    """Arguments for tool execution."""

    apply: bool = Field(
        default=False,
        description="Whether to apply changes or run in dry-run mode",
    )
    verbose: bool = Field(default=False, description="Enable verbose output")
    quiet: bool = Field(default=False, description="Enable quiet mode")
    config_path: str | None = Field(None, description="Path to configuration file")
    output_format: str | None = Field(None, description="Output format")
    target_path: str | None = Field(None, description="Target path for operations")

    # Additional tool-specific parameters
    parameters: list[str] = Field(
        default_factory=list,
        description="Additional command line parameters",
    )

    class Config:
        """Pydantic configuration."""

        extra = "forbid"
