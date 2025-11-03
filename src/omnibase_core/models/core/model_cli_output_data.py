from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.errors import ModelOnexError
from omnibase_core.models.core.model_custom_fields import ModelCustomFields
from omnibase_core.models.core.model_node_info import ModelNodeInfo
from omnibase_core.models.core.model_node_metadata_info import ModelNodeMetadataInfo


class ModelCliOutputData(BaseModel):
    """
    Enterprise-grade CLI output data model with comprehensive status tracking,
    validation, and business intelligence capabilities.

    Features:
    - Comprehensive CLI output structure with business logic
    - Node discovery and metadata integration
    - Registry and validation result tracking
    - File operation and scenario execution monitoring
    - Extensible custom fields for specialized commands
    - Factory methods for common CLI patterns
    """

    model_config = ConfigDict(
        validate_assignment=True,
        extra="forbid",
    )

    # Common output fields
    message: str | None = Field(
        default=None,
        description="Human-readable output message",
        max_length=2000,
    )

    status: str | None = Field(
        default=None,
        description="Status indicator",
        max_length=50,
    )

    # Node-related output
    nodes: list[ModelNodeInfo] | None = Field(
        default=None,
        description="List of nodes (for discovery/list[Any]commands)",
    )

    node_info: ModelNodeInfo | None = Field(
        default=None,
        description="Single node information",
    )

    node_metadata: ModelNodeMetadataInfo | None = Field(
        default=None,
        description="Node metadata information",
    )

    # Registry-related output
    registry_count: int | None = Field(
        default=None,
        description="Number of items in registry",
    )

    registry_status: str | None = Field(
        default=None,
        description="Registry status information",
    )

    # Validation/test results
    validation_passed: bool | None = Field(
        default=None,
        description="Whether validation passed",
    )

    test_results: dict[str, bool] | None = Field(
        default=None,
        description="Test results by test name",
    )

    # Scenario results
    scenario_name: str | None = Field(
        default=None, description="Name of executed scenario"
    )

    scenario_status: str | None = Field(
        default=None,
        description="Scenario execution status",
    )

    # Config/settings output
    config_details: dict[str, Any] | None = Field(
        default=None,
        description="Configuration values",
    )

    # File operation results
    files_processed: list[str] | None = Field(
        default=None,
        description="List of processed files",
    )

    files_created: list[str] | None = Field(
        default=None,
        description="List of created files",
    )

    files_modified: list[str] | None = Field(
        default=None,
        description="List of modified files",
    )

    # Numeric results
    count: int | None = Field(default=None, description="Generic count value")

    total: int | None = Field(default=None, description="Total items")

    processed: int | None = Field(default=None, description="Items processed")

    failed: int | None = Field(default=None, description="Items failed")

    skipped: int | None = Field(default=None, description="Items skipped")

    # Extended fields for complex outputs
    custom_fields: ModelCustomFields | None = Field(
        default=None,
        description="Extensible custom fields for specific commands",
    )

    # Compatibility field for truly dynamic data
    # This should only be used when the structure is genuinely unknown
    raw_data: dict[str, Any] | None = Field(
        default=None,
        description="Raw unstructured data (use sparingly)",
    )

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str | None) -> str | None:
        """Validate message content."""
        if v is None:
            return v

        if not v or not v.strip():
            raise ModelOnexError(
                message="message cannot be empty or whitespace",
                error_code="ONEX_CLI_OUTPUT_DATA_ERROR",
            )

        return v.strip()

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        """Validate status format."""
        if v is None:
            return v

        v = v.strip().lower()
        if not v:
            return None

        # Common status patterns
        valid_statuses = [
            "success",
            "error",
            "failed",
            "warning",
            "info",
            "pending",
            "running",
            "completed",
            "skipped",
            "timeout",
        ]

        if v not in valid_statuses:
            # Allow custom statuses but normalize them
            v = v.replace(" ", "_").replace("-", "_")

        return v

    @field_validator("count", "total", "processed", "failed", "skipped")
    @classmethod
    def validate_non_negative_int(cls, v: int | None) -> int | None:
        """Validate that integer fields are non-negative."""
        if v is None:
            return v

        if v < 0:
            raise ModelOnexError(
                message="value must be non-negative",
                error_code="ONEX_CLI_OUTPUT_DATA_ERROR",
            )

        return v

    # === Business Logic Methods ===

    def is_successful(self) -> bool:
        """Check if the operation was successful."""
        return self.status in ["success", "completed"]

    def is_failed(self) -> bool:
        """Check if the operation failed."""
        return self.status in ["error", "failed"]

    def has_warnings(self) -> bool:
        """Check if there are warnings."""
        return self.status == "warning"

    def get_summary(self) -> str:
        """Get a human-readable summary of the output."""
        if self.message:
            return self.message

        if self.nodes:
            return f"Found {len(self.nodes)} nodes"

        if self.files_processed:
            return f"Processed {len(self.files_processed)} files"

        if self.count is not None:
            return f"Count: {self.count}"

        if self.status:
            return f"Status: {self.status}"

        return "No output data"

    def get_processing_stats(self) -> dict[str, int]:
        """Get processing statistics."""
        stats = {}

        if self.total is not None:
            stats["total"] = self.total

        if self.processed is not None:
            stats["processed"] = self.processed

        if self.failed is not None:
            stats["failed"] = self.failed

        if self.skipped is not None:
            stats["skipped"] = self.skipped

        if self.count is not None:
            stats["count"] = self.count

        return stats

    def get_success_rate(self) -> float | None:
        """Calculate success rate as percentage."""
        if self.processed is None or self.total is None:
            return None

        if self.total == 0:
            return 0.0

        return (self.processed / self.total) * 100.0

    def has_data(self) -> bool:
        """Check if any meaningful data is present."""
        return any(
            [
                self.message,
                self.nodes,
                self.files_processed,
                self.files_created,
                self.files_modified,
                self.total is not None,
                self.processed is not None,
                self.custom_fields,
                self.raw_data,
            ]
        )

    def get_field_value(self, field_name: str, default: Any = None) -> Any:
        """Get a field value by name, checking custom fields if not found."""
        # First check direct fields
        if hasattr(self, field_name):
            value = getattr(self, field_name)
            if value is not None:
                return value

        # Then check custom fields
        if self.custom_fields:
            return self.custom_fields.fields.get(field_name, default)

        # Finally check raw data
        if self.raw_data and field_name in self.raw_data:
            return self.raw_data[field_name]

        return default

    def set_field_value(self, field_name: str, value: Any) -> None:
        """Set a field value, using custom fields for non-standard fields."""
        # If it's a known field, set it directly
        if hasattr(self, field_name) and field_name not in [
            "custom_fields",
            "raw_data",
        ]:
            setattr(self, field_name, value)
        else:
            # Otherwise use custom fields
            if not self.custom_fields:
                self.custom_fields = ModelCustomFields()
            self.custom_fields.set_field(field_name, value)

    def to_dict(self, include_none: bool = False) -> dict[str, Any]:
        """Convert to dictionary, optionally including None values."""
        # Use model_dump() as base and filter None values if requested
        data = {}

        # Add all fields, optionally filtering None values
        for field_name, field_value in self.model_dump().items():
            if include_none or field_value is not None:
                data[field_name] = field_value

        # Merge custom fields if present
        if self.custom_fields:
            custom_data = self.custom_fields.to_dict()
            for key, value in custom_data.items():
                if key not in data:  # Don't override standard fields
                    data[key] = value

        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ModelCliOutputData":
        """Create from dictionary, handling unknown fields gracefully."""
        known_fields = set(cls.model_fields.keys())
        standard_data = {}
        custom_data = {}

        for key, value in data.items():
            if key in known_fields:
                standard_data[key] = value
            else:
                custom_data[key] = value

        # Create instance with standard fields
        instance = cls(**standard_data)

        # Add custom fields if any
        if custom_data:
            instance.custom_fields = ModelCustomFields()
            for key, value in custom_data.items():
                instance.custom_fields.set_field(key, value)

        return instance

    @classmethod
    def create_simple(
        cls,
        message: str,
        status: str = "success",
    ) -> "ModelCliOutputData":
        """Create a simple output with just message and status."""
        return cls(
            message=message,
            status=status,
            nodes=None,
            node_info=None,
            node_metadata=None,
            registry_count=None,
            registry_status=None,
            validation_passed=None,
            test_results=None,
            scenario_name=None,
            scenario_status=None,
            config_details=None,
            files_processed=None,
            files_created=None,
            files_modified=None,
            count=None,
            total=None,
            processed=None,
            failed=None,
            skipped=None,
            custom_fields=None,
            raw_data=None,
        )

    @classmethod
    def create_node_list(cls, nodes: list[ModelNodeInfo]) -> "ModelCliOutputData":
        """Create output for node list[Any]ing."""
        return cls(
            message=f"Found {len(nodes)} nodes",
            status="success",
            nodes=nodes,
            node_info=None,
            node_metadata=None,
            registry_count=None,
            registry_status=None,
            validation_passed=None,
            test_results=None,
            scenario_name=None,
            scenario_status=None,
            config_details=None,
            files_processed=None,
            files_created=None,
            files_modified=None,
            count=len(nodes),
            total=None,
            processed=None,
            failed=None,
            skipped=None,
            custom_fields=None,
            raw_data=None,
        )

    @classmethod
    def create_validation_result(
        cls,
        passed: bool,
        message: str,
        test_results: dict[str, bool] | None = None,
    ) -> "ModelCliOutputData":
        """Create output for validation results."""
        return cls(
            validation_passed=passed,
            message=message,
            status="success" if passed else "failed",
            test_results=test_results,
            nodes=None,
            node_info=None,
            node_metadata=None,
            registry_count=None,
            registry_status=None,
            scenario_name=None,
            scenario_status=None,
            config_details=None,
            files_processed=None,
            files_created=None,
            files_modified=None,
            count=None,
            total=None,
            processed=None,
            failed=None,
            skipped=None,
            custom_fields=None,
            raw_data=None,
        )

    @classmethod
    def create_file_operation_result(
        cls,
        operation: str,
        files_processed: list[str],
        message: str | None = None,
        status: str = "success",
    ) -> "ModelCliOutputData":
        """Create output for file operation results."""
        return cls(
            message=message or f"File {operation} completed successfully",
            status=status,
            files_processed=files_processed,
            count=len(files_processed),
            nodes=None,
            node_info=None,
            node_metadata=None,
            registry_count=None,
            registry_status=None,
            validation_passed=None,
            test_results=None,
            scenario_name=None,
            scenario_status=None,
            config_details=None,
            files_created=None,
            files_modified=None,
            total=None,
            processed=None,
            failed=None,
            skipped=None,
            custom_fields=None,
            raw_data=None,
        )

    @classmethod
    def create_registry_result(
        cls,
        operation: str,
        registry_count: int,
        registry_status: str,
        message: str | None = None,
    ) -> "ModelCliOutputData":
        """Create output for registry operations."""
        return cls(
            message=message or f"Registry {operation} completed",
            status="success" if "success" in registry_status.lower() else "info",
            registry_count=registry_count,
            registry_status=registry_status,
            count=registry_count,
            nodes=None,
            node_info=None,
            node_metadata=None,
            validation_passed=None,
            test_results=None,
            scenario_name=None,
            scenario_status=None,
            config_details=None,
            files_processed=None,
            files_created=None,
            files_modified=None,
            total=None,
            processed=None,
            failed=None,
            skipped=None,
            custom_fields=None,
            raw_data=None,
        )
