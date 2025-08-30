"""
CLI result model for ONEX CLI operations.

This model encapsulates the results of CLI parsing and execution
as part of NODEBASE-001 Phase 4 deconstruction.

Author: ONEX Framework Team
"""

from typing import List, Optional

from pydantic import BaseModel, Field

from .model_cli_error_details import ModelCliErrorDetails
from .model_cli_health_check_result import ModelCliHealthCheckResult
from .model_cli_introspection_data import ModelCliIntrospectionData
from .model_cli_output_data import ModelCliOutputData
from .model_cli_parsed_args import ModelCliParsedArgs
from .model_cli_tool_input_state import ModelCliToolInputState


class ModelCliResult(BaseModel):
    """
    Result model for CLI operations.

    Encapsulates the results of CLI argument parsing, flag handling,
    and command execution with comprehensive details.
    """

    exit_code: int = Field(
        ..., description="CLI exit code for the operation", ge=0, le=255
    )

    parsed_args: Optional[ModelCliParsedArgs] = Field(
        default=None, description="Strongly typed parsed CLI arguments"
    )

    flags_detected: List[str] = Field(
        default_factory=list, description="List of flags detected in arguments"
    )

    operation_type: str = Field(
        ..., description="Type of CLI operation (health_check|introspect|normal|help)"
    )

    success: bool = Field(..., description="Whether the CLI operation was successful")

    message: str = Field(
        default="", description="Human-readable message about the operation"
    )

    output_data: Optional[ModelCliOutputData] = Field(
        default=None, description="Strongly typed output data from the operation"
    )

    help_text: Optional[str] = Field(
        default=None, description="Generated help text if applicable"
    )

    tool_input_state: Optional[ModelCliToolInputState] = Field(
        default=None, description="Strongly typed tool input state if applicable"
    )

    execution_time_ms: Optional[float] = Field(
        default=None, description="Time taken for CLI operation in milliseconds", ge=0
    )

    error_details: Optional[ModelCliErrorDetails] = Field(
        default=None, description="Strongly typed error details if operation failed"
    )

    introspection_data: Optional[ModelCliIntrospectionData] = Field(
        default=None,
        description="Strongly typed introspection data if --introspect was used",
    )

    health_check_result: Optional[ModelCliHealthCheckResult] = Field(
        default=None,
        description="Strongly typed health check result if --health-check was used",
    )

    should_exit: bool = Field(
        default=True, description="Whether the CLI should exit after this operation"
    )

    class Config:
        """Pydantic configuration."""

        arbitrary_types_allowed = True
