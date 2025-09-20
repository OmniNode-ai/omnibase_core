"""
CLI output data model.

Clean, strongly-typed replacement for dict[str, Any] in CLI execution output.
Follows ONEX one-model-per-file naming conventions.
"""

from pydantic import BaseModel, Field


class ModelCliOutputData(BaseModel):
    """
    Clean model for CLI execution output data.

    Replaces dict[str, Any] with structured data model.
    """

    # Core output fields
    output_type: str = Field(default="execution", description="Type of output data")
    format: str = Field(default="json", description="Output format")

    # Standard output content
    stdout: str | None = Field(None, description="Standard output content")
    stderr: str | None = Field(None, description="Standard error content")

    # Structured results
    results: dict[str, str | int | bool | float] = Field(
        default_factory=dict, description="Execution results with basic types"
    )

    # Metadata
    metadata: dict[str, str | int | bool] = Field(
        default_factory=dict, description="Output metadata with basic types"
    )

    # Status and validation
    status: str = Field(default="completed", description="Output status")
    is_valid: bool = Field(default=True, description="Whether output is valid")

    # Performance metrics
    execution_time_ms: float | None = Field(
        None, description="Execution time in milliseconds"
    )
    memory_usage_mb: float | None = Field(None, description="Memory usage in MB")

    # File output information
    files_created: list[str] = Field(
        default_factory=list, description="List of files created during execution"
    )

    files_modified: list[str] = Field(
        default_factory=list, description="List of files modified during execution"
    )

    def add_result(self, key: str, value: str | int | bool | float) -> None:
        """Add a result value with type safety."""
        self.results[key] = value

    def add_metadata(self, key: str, value: str | int | bool) -> None:
        """Add metadata with type safety."""
        self.metadata[key] = value

    def add_file_created(self, file_path: str) -> None:
        """Add a created file to the list."""
        if file_path not in self.files_created:
            self.files_created.append(file_path)

    def add_file_modified(self, file_path: str) -> None:
        """Add a modified file to the list."""
        if file_path not in self.files_modified:
            self.files_modified.append(file_path)

    def get_field_value(
        self, key: str, default: str | int | bool | float | None = None
    ) -> str | int | bool | float | None:
        """Get a field value from results or metadata."""
        if key in self.results:
            return self.results[key]
        if key in self.metadata:
            return self.metadata[key]
        return default

    def set_field_value(self, key: str, value: str | int | bool | float) -> None:
        """Set a field value in results."""
        self.results[key] = value

    @classmethod
    def create_simple(
        cls,
        stdout: str | None = None,
        stderr: str | None = None,
        status: str = "completed",
    ) -> "ModelCliOutputData":
        """Create simple output data with just stdout/stderr."""
        return cls(
            stdout=stdout,
            stderr=stderr,
            status=status,
            execution_time_ms=None,
            memory_usage_mb=None,
        )

    @classmethod
    def create_with_results(
        cls, results: dict[str, str | int | bool | float], status: str = "completed"
    ) -> "ModelCliOutputData":
        """Create output data with structured results."""
        return cls(
            results=results,
            status=status,
            stdout=None,
            stderr=None,
            execution_time_ms=None,
            memory_usage_mb=None,
        )


# Export the model
__all__ = [
    "ModelCliOutputData",
]
