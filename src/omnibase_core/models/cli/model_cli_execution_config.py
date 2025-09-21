"""
CLI Execution Configuration Model.

Configuration settings and parameters for CLI command execution.
Part of the ModelCliExecution restructuring to reduce excessive string fields.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from ...enums.enum_output_format import EnumOutputFormat
from .model_cli_execution_input_data import ModelCliExecutionInputData


class ModelCliExecutionConfig(BaseModel):
    """
    CLI execution configuration settings.

    Contains all configuration options, settings, and parameters
    for CLI command execution without cluttering core execution info.
    """

    # Execution context
    working_directory: Path | None = Field(
        default=None,
        description="Working directory for execution",
    )
    environment_vars: dict[str, str] = Field(
        default_factory=dict,
        description="Environment variables",
    )

    # Execution settings
    is_dry_run: bool = Field(default=False, description="Whether this is a dry run")
    is_test_execution: bool = Field(
        default=False,
        description="Whether this is a test execution",
    )
    is_debug_enabled: bool = Field(
        default=False,
        description="Whether debug mode is enabled",
    )
    is_trace_enabled: bool = Field(
        default=False,
        description="Whether tracing is enabled",
    )
    is_verbose: bool = Field(
        default=False,
        description="Whether verbose mode is enabled",
    )

    # Input/output configuration
    input_data: dict[str, ModelCliExecutionInputData] = Field(
        default_factory=dict,
        description="Input data for execution",
    )
    output_format: EnumOutputFormat = Field(
        default=EnumOutputFormat.TEXT, description="Expected output format"
    )
    capture_output: bool = Field(default=True, description="Whether to capture output")

    def add_input_data(self, key: str, input_data: ModelCliExecutionInputData) -> None:
        """Add input data."""
        self.input_data[key] = input_data

    def get_input_data(
        self, key: str, default: ModelCliExecutionInputData | None = None
    ) -> ModelCliExecutionInputData | None:
        """Get input data."""
        return self.input_data.get(key, default)

    def add_environment_var(self, key: str, value: str) -> None:
        """Add environment variable."""
        self.environment_vars[key] = value

    def get_environment_var(self, key: str, default: str | None = None) -> str | None:
        """Get environment variable."""
        return self.environment_vars.get(key, default)

    def is_debug_mode(self) -> bool:
        """Check if any debug mode is enabled."""
        return self.is_debug_enabled or self.is_trace_enabled or self.is_verbose

    @classmethod
    def create_production(cls) -> ModelCliExecutionConfig:
        """Create production configuration."""
        return cls(
            is_dry_run=False,
            is_test_execution=False,
            is_debug_enabled=False,
            is_trace_enabled=False,
            is_verbose=False,
        )

    @classmethod
    def create_debug(cls) -> ModelCliExecutionConfig:
        """Create debug configuration."""
        return cls(
            is_debug_enabled=True,
            is_trace_enabled=True,
            is_verbose=True,
        )

    @classmethod
    def create_test(cls) -> ModelCliExecutionConfig:
        """Create test configuration."""
        return cls(
            is_test_execution=True,
            is_debug_enabled=True,
            is_verbose=True,
        )


# Export for use
__all__ = ["ModelCliExecutionConfig"]