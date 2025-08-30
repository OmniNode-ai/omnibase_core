"""
CLI configuration model for ONEX CLI service operations.

This model defines configuration options for CLI service behavior
as part of NODEBASE-001 Phase 4 deconstruction.

Author: ONEX Framework Team
"""

from pydantic import BaseModel, Field


class ModelCliConfig(BaseModel):
    """
    Configuration model for CLI service operations.

    Controls CLI parsing behavior, flag handling, and error management.
    """

    enable_health_check_flag: bool = Field(
        default=True,
        description="Enable --health-check flag handling",
    )

    enable_introspect_flag: bool = Field(
        default=True,
        description="Enable --introspect flag handling",
    )

    enable_help_flag: bool = Field(
        default=True,
        description="Enable --help flag handling",
    )

    enable_version_flag: bool = Field(
        default=True,
        description="Enable --version flag handling",
    )

    custom_flags: list[str] = Field(
        default_factory=list,
        description="List of additional custom flags to recognize",
    )

    enable_argument_validation: bool = Field(
        default=True,
        description="Enable CLI argument validation",
    )

    enable_error_handling: bool = Field(
        default=True,
        description="Enable comprehensive CLI error handling",
    )

    enable_help_generation: bool = Field(
        default=True,
        description="Enable automatic help text generation",
    )

    enable_input_state_conversion: bool = Field(
        default=True,
        description="Enable automatic input state conversion from CLI args",
    )

    default_exit_code_success: int = Field(
        default=0,
        description="Default exit code for successful operations",
        ge=0,
        le=255,
    )

    default_exit_code_error: int = Field(
        default=1,
        description="Default exit code for error operations",
        ge=0,
        le=255,
    )

    enable_performance_timing: bool = Field(
        default=True,
        description="Enable performance timing for CLI operations",
    )

    max_help_text_length: int = Field(
        default=2000,
        description="Maximum length for generated help text",
        gt=0,
    )

    exit_code_mappings: dict[str, int] = Field(
        default_factory=dict,
        description="Custom exit code mappings for specific errors",
    )

    enable_debug_output: bool = Field(
        default=False,
        description="Enable debug output for CLI operations",
    )

    enable_json_output: bool = Field(
        default=False,
        description="Enable JSON output format for CLI results",
    )

    output_format: str = Field(
        default="text",
        description="Default output format (text|json|yaml)",
    )

    class Config:
        """Pydantic configuration."""

        arbitrary_types_allowed = True
