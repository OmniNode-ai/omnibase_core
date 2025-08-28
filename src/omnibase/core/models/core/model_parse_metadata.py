"""
Parse Metadata Model

Metadata tracking for argument parsing operations including performance
metrics, source information, and parsing context.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ModelParseMetadata(BaseModel):
    """
    Metadata for argument parsing operations.

    This model tracks parsing performance, source information,
    and context for debugging and optimization purposes.
    """

    parse_start_time: datetime = Field(
        default_factory=datetime.utcnow, description="When parsing started"
    )

    parse_end_time: Optional[datetime] = Field(
        None, description="When parsing completed"
    )

    parse_duration_ms: Optional[int] = Field(
        None, description="Parsing duration in milliseconds", ge=0
    )

    source_command: str = Field(..., description="Original command that was parsed")

    parser_version: str = Field(
        default="1.0.0", description="Version of the parser used"
    )

    argument_count: int = Field(
        default=0, description="Total number of arguments parsed", ge=0
    )

    flag_count: int = Field(
        default=0, description="Number of flag arguments (--flag)", ge=0
    )

    positional_count: int = Field(
        default=0, description="Number of positional arguments", ge=0
    )

    validation_errors_count: int = Field(
        default=0, description="Number of validation errors encountered", ge=0
    )

    warnings_count: int = Field(
        default=0, description="Number of warnings generated", ge=0
    )

    parsing_strategy: str = Field(
        default="contract_driven",
        description="Strategy used for parsing (contract_driven, generic, etc.)",
    )

    contract_source: Optional[str] = Field(
        None, description="Source of the contract used for parsing"
    )

    command_definition_id: Optional[str] = Field(
        None, description="ID of the command definition used"
    )

    raw_args: List[str] = Field(
        default_factory=list, description="Original raw argument strings"
    )

    environment_variables: Dict[str, str] = Field(
        default_factory=dict,
        description="Relevant environment variables during parsing",
    )

    parsing_context: Dict[str, Any] = Field(
        default_factory=dict, description="Additional parsing context"
    )

    debug_info: Dict[str, Any] = Field(
        default_factory=dict, description="Debug information for troubleshooting"
    )

    def mark_complete(self) -> None:
        """Mark parsing as complete and calculate duration."""
        self.parse_end_time = datetime.utcnow()
        if self.parse_start_time:
            duration = self.parse_end_time - self.parse_start_time
            self.parse_duration_ms = int(duration.total_seconds() * 1000)

    def add_debug_info(self, key: str, value: Any) -> None:
        """Add debug information."""
        self.debug_info[key] = value

    def add_context(self, key: str, value: Any) -> None:
        """Add parsing context information."""
        self.parsing_context[key] = value

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary for monitoring."""
        return {
            "parse_duration_ms": self.parse_duration_ms,
            "argument_count": self.argument_count,
            "validation_errors": self.validation_errors_count,
            "warnings": self.warnings_count,
            "parsing_strategy": self.parsing_strategy,
            "success": self.validation_errors_count == 0,
        }

    def is_successful(self) -> bool:
        """Check if parsing was successful (no validation errors)."""
        return self.validation_errors_count == 0

    def has_warnings(self) -> bool:
        """Check if parsing generated warnings."""
        return self.warnings_count > 0

    def get_argument_breakdown(self) -> Dict[str, int]:
        """Get breakdown of argument types."""
        return {
            "total": self.argument_count,
            "flags": self.flag_count,
            "positional": self.positional_count,
            "other": max(
                0, self.argument_count - self.flag_count - self.positional_count
            ),
        }

    @classmethod
    def create_for_command(
        cls,
        source_command: str,
        raw_args: List[str],
        command_definition_id: Optional[str] = None,
        contract_source: Optional[str] = None,
    ) -> "ModelParseMetadata":
        """Create metadata for a command parsing operation."""
        return cls(
            source_command=source_command,
            raw_args=raw_args,
            command_definition_id=command_definition_id,
            contract_source=contract_source,
            argument_count=len(raw_args),
        )
