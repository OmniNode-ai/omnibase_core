"""
Example output model with strong typing.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ModelExampleOutput(BaseModel):
    """
    Structured output data for examples.

    Replaces dict[str, Any] with strongly typed output structure.
    """

    # Output identification
    output_id: UUID | None = Field(
        default=None,
        description="Unique identifier for this output"
    )

    # Core output data
    data: dict[str, Any] = Field(
        default_factory=dict,
        description="The actual output data"
    )

    # Output metadata
    format: str | None = Field(
        default=None,
        description="Format of the output data (json, xml, text, etc.)"
    )

    encoding: str | None = Field(
        default=None,
        description="Encoding of the output data"
    )

    content_type: str | None = Field(
        default=None,
        description="MIME type or content type of the output"
    )

    # Output structure information
    schema_version: str | None = Field(
        default=None,
        description="Version of the output schema"
    )

    # Status and success information
    success: bool = Field(
        default=True,
        description="Whether the operation was successful"
    )

    status_code: int | None = Field(
        default=None,
        description="Status code for the operation"
    )

    status_message: str | None = Field(
        default=None,
        description="Human-readable status message"
    )

    # Error information
    errors: list[str] | None = Field(
        default=None,
        description="List of error messages if any"
    )

    warnings: list[str] | None = Field(
        default=None,
        description="List of warning messages if any"
    )

    # Performance metrics
    execution_time_ms: float | None = Field(
        default=None,
        description="Execution time in milliseconds"
    )

    memory_usage_mb: float | None = Field(
        default=None,
        description="Memory usage in megabytes"
    )

    # Processing information
    processed_at: datetime | None = Field(
        default=None,
        description="When the output was processed"
    )

    processing_details: dict[str, Any] | None = Field(
        default=None,
        description="Additional processing details"
    )

    # Output context
    context: dict[str, Any] | None = Field(
        default=None,
        description="Additional context information for the output"
    )

    # Validation information
    validated: bool = Field(
        default=False,
        description="Whether the output has been validated"
    )

    validation_results: dict[str, Any] | None = Field(
        default=None,
        description="Results of output validation"
    )

    def get_data_field(self, key: str, default: Any = None) -> Any:
        """Get a field from the output data."""
        return self.data.get(key, default)

    def set_data_field(self, key: str, value: Any) -> None:
        """Set a field in the output data."""
        self.data[key] = value

    def has_data_field(self, key: str) -> bool:
        """Check if a field exists in the output data."""
        return key in self.data

    def add_error(self, error: str) -> None:
        """Add an error message."""
        if self.errors is None:
            self.errors = []
        self.errors.append(error)
        self.success = False

    def add_warning(self, warning: str) -> None:
        """Add a warning message."""
        if self.warnings is None:
            self.warnings = []
        self.warnings.append(warning)

    def has_errors(self) -> bool:
        """Check if there are any errors."""
        return self.errors is not None and len(self.errors) > 0

    def has_warnings(self) -> bool:
        """Check if there are any warnings."""
        return self.warnings is not None and len(self.warnings) > 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return self.model_dump(exclude_none=True)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ModelExampleOutput":
        """Create from dictionary with validation."""
        if not isinstance(data, dict):
            raise ValueError(f"Expected dictionary, got {type(data)}")

        return cls(**data)

    @classmethod
    def create_simple(cls, data: dict[str, Any], success: bool = True) -> "ModelExampleOutput":
        """Create a simple output with just data."""
        return cls(data=data, success=success)

    @classmethod
    def create_error(cls, error: str, status_code: int | None = None) -> "ModelExampleOutput":
        """Create an error output."""
        return cls(
            success=False,
            errors=[error],
            status_code=status_code,
            status_message=error
        )