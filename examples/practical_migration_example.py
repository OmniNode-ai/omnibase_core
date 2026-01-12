"""
Practical example showing migration of ModelCliOutputData to use ModelResultAccessor.

This demonstrates a real migration from the existing pattern to the new
field accessor pattern with discriminated unions for proper type safety.
"""

from typing import Any

from pydantic import BaseModel, Field

# Import the new field accessor
from omnibase_core.models.core import ModelResultAccessor
# Import discriminated union models for proper type safety
from omnibase_core.models.examples.model_property_value import \
    ModelPropertyValue


# ========== BEFORE: Current Implementation (with generic unions) ==========
class CurrentModelCliOutputData(BaseModel):
    """Current implementation with custom field access methods using generic unions."""

    # Core output fields
    output_type: str = Field(default="execution", description="Type of output data")
    format: str = Field(default="json", description="Output format")

    # Standard output content
    stdout: str | None = Field(None, description="Standard output content")
    stderr: str | None = Field(None, description="Standard error content")

    # PROBLEM: Generic union types lose type information and validation
    results: dict[str, str | int | bool | float] = Field(
        default_factory=dict, description="Execution results with basic types"
    )

    # PROBLEM: Generic union types lose type information and validation
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

    def add_result(self, key: str, value: str | int | bool | float) -> None:
        """Add a result value with type safety."""
        self.results[key] = value

    def add_metadata(self, key: str, value: str | int | bool) -> None:
        """Add metadata with type safety."""
        self.metadata[key] = value


# ========== AFTER: Migrated Implementation with Discriminated Unions ==========
class MigratedModelCliOutputData(ModelResultAccessor):
    """Migrated implementation using ModelResultAccessor pattern with proper discriminated unions."""

    # Core output fields (unchanged)
    output_type: str = Field(default="execution", description="Type of output data")
    format: str = Field(default="json", description="Output format")

    # Standard output content (unchanged)
    stdout: str | None = Field(None, description="Standard output content")
    stderr: str | None = Field(None, description="Standard error content")

    # SOLUTION: Use ModelPropertyValue for type-safe, validated storage
    results: dict[str, ModelPropertyValue] = Field(
        default_factory=dict,
        description="Execution results with discriminated union types",
    )

    # SOLUTION: Use ModelPropertyValue for type-safe, validated storage
    metadata: dict[str, ModelPropertyValue] = Field(
        default_factory=dict,
        description="Output metadata with discriminated union types",
    )

    # Status and validation (unchanged)
    status: str = Field(default="completed", description="Output status")
    is_valid: bool = Field(default=True, description="Whether output is valid")

    # Performance metrics (unchanged)
    execution_time_ms: float | None = Field(
        None, description="Execution time in milliseconds"
    )
    memory_usage_mb: float | None = Field(None, description="Memory usage in MB")

    # File output information (unchanged)
    files_created: list[str] = Field(
        default_factory=list, description="List of files created during execution"
    )
    files_modified: list[str] = Field(
        default_factory=list, description="List of files modified during execution"
    )

    # ========== WRAPPER METHODS ==========
    def get_field_value(
        self, key: str, default: str | int | bool | float | None = None
    ) -> str | int | bool | float | None:
        """
        Get field value method.

        Delegates to the new get_result_value method from ModelResultAccessor.
        """
        return self.get_result_value(key, default)

    def set_field_value(self, key: str, value: str | int | bool | float) -> None:
        """
        Set field value method.

        Delegates to the new set_result_value method from ModelResultAccessor.
        """
        self.set_result_value(key, value)

    # ========== ENHANCED METHODS (using discriminated unions) ==========
    def add_result(self, key: str, value: str | int | bool | float) -> None:
        """Add a result value with type safety using discriminated unions."""
        if isinstance(value, str):
            self.results[key] = ModelPropertyValue.from_string(value)
        elif isinstance(value, int):
            self.results[key] = ModelPropertyValue.from_int(value)
        elif isinstance(value, float):
            self.results[key] = ModelPropertyValue.from_float(value)
        elif isinstance(value, bool):
            self.results[key] = ModelPropertyValue.from_bool(value)

    def add_metadata(self, key: str, value: str | int | bool) -> None:
        """Add metadata value with type safety using discriminated unions."""
        if isinstance(value, str):
            self.metadata[key] = ModelPropertyValue.from_string(value)
        elif isinstance(value, int):
            self.metadata[key] = ModelPropertyValue.from_int(value)
        elif isinstance(value, bool):
            self.metadata[key] = ModelPropertyValue.from_bool(value)

    def add_file_created(self, file_path: str) -> None:
        """Add a created file to the list."""
        if file_path not in self.files_created:
            self.files_created.append(file_path)

    def add_file_modified(self, file_path: str) -> None:
        """Add a modified file to the list."""
        if file_path not in self.files_modified:
            self.files_modified.append(file_path)

    # ========== NEW ENHANCED METHODS ==========
    def set_nested_result(self, path: str, value: Any) -> bool:
        """Set nested result using dot notation."""
        return self.set_field(f"results.{path}", value)

    def get_nested_result(self, path: str, default: Any = None) -> Any:
        """Get nested result using dot notation."""
        return self.get_field(f"results.{path}", default)

    def set_nested_metadata(self, path: str, value: Any) -> bool:
        """Set nested metadata using dot notation."""
        return self.set_field(f"metadata.{path}", value)

    def get_nested_metadata(self, path: str, default: Any = None) -> Any:
        """Get nested metadata using dot notation."""
        return self.get_field(f"metadata.{path}", default)

    def add_performance_metric(self, metric_name: str, value: float) -> None:
        """Add a performance metric with structured storage."""
        self.set_field(f"metadata.performance.{metric_name}", value)

    def get_performance_metrics(self) -> dict[str, Any]:
        """Get all performance metrics."""
        return self.get_field("metadata.performance", {})

    def set_execution_context(self, context: dict[str, Any]) -> None:
        """Set execution context information."""
        for key, value in context.items():
            self.set_field(f"metadata.context.{key}", value)

    def get_execution_context(self) -> dict[str, Any]:
        """Get execution context information."""
        return self.get_field("metadata.context", {})

    # ========== CLASS METHODS (unchanged) ==========
    @classmethod
    def create_simple(
        cls,
        stdout: str | None = None,
        stderr: str | None = None,
        status: str = "completed",
    ) -> "MigratedModelCliOutputData":
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
    ) -> "MigratedModelCliOutputData":
        """Create output data with structured results."""
        return cls(
            results=results,
            status=status,
            stdout=None,
            stderr=None,
            execution_time_ms=None,
            memory_usage_mb=None,
        )


# ========== DEMONSTRATION ==========
def demonstrate_migration():
    """Demonstrate the migration and new capabilities."""

    print("=== Current Implementation ===")
    current = CurrentModelCliOutputData()

    # Current usage patterns
    current.set_field_value("exit_code", 0)
    current.set_field_value("duration", 150.5)
    current.add_result("files_processed", 42)
    current.add_metadata("user", "admin")

    print(f"Exit code: {current.get_field_value('exit_code')}")
    print(f"Duration: {current.get_field_value('duration')}")
    print(f"Files processed: {current.get_field_value('files_processed')}")
    print(f"User: {current.get_field_value('user')}")

    print("\n=== Migrated Implementation with Discriminated Unions ===")
    migrated = MigratedModelCliOutputData()

    # Enhanced API usage with type safety
    migrated.add_result("exit_code", 0)  # Type-safe using ModelPropertyValue
    migrated.add_result("duration", 150.5)
    migrated.add_result("files_processed", 42)
    migrated.add_metadata("user", "admin")

    # Demonstrate type safety and validation
    print(
        f"Exit code: {migrated.results['exit_code'].value} (type: {migrated.results['exit_code'].value_type})"
    )
    print(
        f"Duration: {migrated.results['duration'].value} (type: {migrated.results['duration'].value_type})"
    )
    print(
        f"Files processed: {migrated.results['files_processed'].value} (type: {migrated.results['files_processed'].value_type})"
    )
    print(
        f"User: {migrated.metadata['user'].value} (type: {migrated.metadata['user'].value_type})"
    )

    print("\n=== New Enhanced Capabilities with Type Safety ===")

    # New dot notation capabilities
    migrated.set_field("results.execution.phase", "compilation")
    migrated.set_field("results.execution.step", 3)
    migrated.set_field("results.output.format", "json")
    migrated.set_field("results.output.compression", True)

    # New nested methods
    migrated.set_nested_result("validation.syntax_errors", 0)
    migrated.set_nested_result("validation.warnings", 2)
    migrated.set_nested_metadata("environment.os", "linux")
    migrated.set_nested_metadata("environment.arch", "x64")

    # Performance metrics
    migrated.add_performance_metric("cpu_usage", 45.2)
    migrated.add_performance_metric("memory_peak", 128.5)
    migrated.add_performance_metric("disk_io", 1024.0)

    # Execution context
    migrated.set_execution_context(
        {
            "working_directory": "/app/src",
            "command_line": "python main.py --verbose",
            "environment_vars": ["DEBUG=1", "LOG_LEVEL=info"],
        }
    )

    # Access new structured data
    print(f"Execution phase: {migrated.get_field('results.execution.phase')}")
    print(f"Syntax errors: {migrated.get_nested_result('validation.syntax_errors')}")
    print(f"OS: {migrated.get_nested_metadata('environment.os')}")
    print(f"Performance metrics: {migrated.get_performance_metrics()}")
    print(f"Working dir: {migrated.get_field('metadata.context.working_directory')}")

    print("\n=== Advanced Queries ===")

    # Complex nested queries
    has_errors = migrated.has_field("results.validation.syntax_errors")
    print(f"Has syntax error data: {has_errors}")

    # Check for nested performance data
    has_perf_data = migrated.has_field("metadata.performance")
    print(f"Has performance data: {has_perf_data}")

    # Get all results as a structured view
    all_results = migrated.get_field("results", {})
    print(f"All results structure: {all_results}")


if __name__ == "__main__":
    demonstrate_migration()
