"""
CLI output data model.

Clean, strongly-typed replacement for dict[str, Any] in CLI execution output.
Follows ONEX one-model-per-file naming conventions.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_cli_status import EnumCliStatus
from omnibase_core.enums.enum_output_format import EnumOutputFormat
from omnibase_core.enums.enum_output_type import EnumOutputType
from omnibase_core.models.infrastructure.model_value import ModelValue
from omnibase_core.types.type_serializable_value import SerializedDict


class ModelCliOutputData(BaseModel):
    """
    Clean model for CLI execution output data.

    Replaces dict[str, Any] with structured data model.
    Implements Core protocols:
    - Serializable: Data serialization/deserialization
    - Nameable: Name management interface
    - Validatable: Validation and verification
    """

    # Core output fields
    output_type: EnumOutputType = Field(
        default=EnumOutputType.CONSOLE,
        description="Type of output data",
    )
    format: EnumOutputFormat = Field(
        default=EnumOutputFormat.JSON,
        description="Output format",
    )

    # Standard output content
    stdout: str = Field(default="", description="Standard output content")
    stderr: str = Field(default="", description="Standard error content")

    # Structured results
    results: dict[str, ModelValue] = Field(
        default_factory=dict,
        description="Execution results with typed values",
    )

    # Metadata
    metadata: dict[str, ModelValue] = Field(
        default_factory=dict,
        description="Output metadata with typed values",
    )

    # Status and validation
    status: EnumCliStatus = Field(
        default=EnumCliStatus.SUCCESS,
        description="Output status",
    )
    is_valid: bool = Field(default=True, description="Whether output is valid")

    # Performance metrics
    execution_time_ms: float = Field(
        default=0.0,
        description="Execution time in milliseconds",
    )
    memory_usage_mb: float = Field(default=0.0, description="Memory usage in MB")

    # File output information
    files_created: list[str] = Field(
        default_factory=list,
        description="List of files created during execution",
    )

    files_modified: list[str] = Field(
        default_factory=list,
        description="List of files modified during execution",
    )

    def add_result(self, key: str, value: str) -> None:
        """Add a result value. CLI results are typically strings."""
        self.results[key] = ModelValue.from_string(value)

    def add_metadata(self, key: str, value: str) -> None:
        """Add metadata. CLI metadata is typically strings."""
        self.metadata[key] = ModelValue.from_string(value)

    def add_file_created(self, file_path: str) -> None:
        """Add a created file to the list[Any]."""
        if file_path not in self.files_created:
            self.files_created.append(file_path)

    def add_file_modified(self, file_path: str) -> None:
        """Add a modified file to the list[Any]."""
        if file_path not in self.files_modified:
            self.files_modified.append(file_path)

    def get_field_value(self, key: str, default: str = "") -> str:
        """Get a field value from results or metadata. CLI fields are strings."""
        if key in self.results:
            return str(self.results[key].to_python_value())
        if key in self.metadata:
            return str(self.metadata[key].to_python_value())
        return default

    def set_field_value(self, key: str, value: str) -> None:
        """Set a field value in results. CLI field values are strings."""
        self.results[key] = ModelValue.from_string(value)

    @classmethod
    def create_simple(
        cls,
        stdout: str = "",
        stderr: str = "",
        status: EnumCliStatus = EnumCliStatus.SUCCESS,
    ) -> ModelCliOutputData:
        """Create simple output data with just stdout/stderr."""
        return cls(
            stdout=stdout,
            stderr=stderr,
            status=status,
        )

    @classmethod
    def create_with_results(
        cls,
        results: dict[str, str],
        status: EnumCliStatus = EnumCliStatus.SUCCESS,
    ) -> ModelCliOutputData:
        """Create output data with structured results. CLI results are strings."""
        typed_results = {k: ModelValue.from_string(v) for k, v in results.items()}
        return cls(
            results=typed_results,
            status=status,
        )

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )

    # Protocol method implementations

    def serialize(self) -> SerializedDict:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def get_name(self) -> str:
        """Get name (Nameable protocol)."""
        # Try common name field patterns
        for field in ["name", "display_name", "title", "node_name"]:
            if hasattr(self, field):
                value = getattr(self, field)
                if value is not None:
                    return str(value)
        return f"Unnamed {self.__class__.__name__}"

    def set_name(self, name: str) -> None:
        """Set name (Nameable protocol)."""
        # Try to set the most appropriate name field
        for field in ["name", "display_name", "title", "node_name"]:
            if hasattr(self, field):
                setattr(self, field, name)
                return

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol)."""
        return True


__all__ = [
    "ModelCliOutputData",
]
