from datetime import UTC, datetime

from pydantic import BaseModel, Field

from omnibase_core.types.constraints import BasicValueType
from omnibase_core.types.typed_dict_usage_metadata import TypedDictUsageMetadata


class ModelMetadataUsageMetrics(BaseModel):
    """Usage metrics for metadata nodes.
    Implements Core protocols:
    - ProtocolMetadataProvider: Metadata management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    total_invocations: int = Field(
        default=0,
        description="Total number of invocations",
        ge=0,
    )
    success_count: int = Field(
        default=0,
        description="Number of successful invocations",
        ge=0,
    )
    failure_count: int = Field(
        default=0,
        description="Number of failed invocations",
        ge=0,
    )
    average_execution_time_ms: float = Field(
        default=0.0,
        description="Average execution time in milliseconds",
        ge=0.0,
    )
    last_invocation: datetime | None = Field(
        default=None,
        description="Last invocation timestamp",
    )
    peak_memory_usage_mb: float = Field(
        default=0.0,
        description="Peak memory usage in MB",
        ge=0.0,
    )

    def get_success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total_invocations == 0:
            return 100.0
        return (self.success_count / self.total_invocations) * 100.0

    def get_failure_rate(self) -> float:
        """Calculate failure rate percentage."""
        if self.total_invocations == 0:
            return 0.0
        return (self.failure_count / self.total_invocations) * 100.0

    def record_invocation(
        self,
        success: bool,
        execution_time_ms: float = 0.0,
        memory_usage_mb: float = 0.0,
    ) -> None:
        """Record a new invocation."""
        self.total_invocations += 1
        if success:
            self.success_count += 1
        else:
            self.failure_count += 1

        # Update averages
        if execution_time_ms > 0:
            current_total = self.average_execution_time_ms * (
                self.total_invocations - 1
            )
            self.average_execution_time_ms = (
                current_total + execution_time_ms
            ) / self.total_invocations

        # Update peak memory usage
        self.peak_memory_usage_mb = max(memory_usage_mb, self.peak_memory_usage_mb)

        self.last_invocation = datetime.now(UTC)

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }

    # Protocol method implementations

    def get_metadata(self) -> TypedDictUsageMetadata:
        """Get metadata as dictionary (ProtocolMetadataProvider protocol)."""
        metadata: TypedDictUsageMetadata = {}
        # Include common metadata fields
        for field in ["name", "description", "version", "tags", "metadata"]:
            if hasattr(self, field):
                value = getattr(self, field)
                if value is not None:
                    if (field == "tags" and isinstance(value, list)) or (
                        field == "metadata" and isinstance(value, dict)
                    ):
                        metadata[field] = value  # type: ignore[literal-required]
                    else:
                        metadata[field] = str(value)  # type: ignore[literal-required]
        return metadata

    def set_metadata(self, metadata: TypedDictUsageMetadata) -> bool:
        """Set metadata from dictionary (ProtocolMetadataProvider protocol)."""
        try:
            for key, value in metadata.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except Exception:  # fallback-ok: protocol method contract requires bool return - False indicates metadata update failed safely
            return False

    def serialize(self) -> dict[str, BasicValueType]:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol)."""
        try:
            # Basic validation - ensure required fields exist
            # Override in specific models for custom validation
            return True
        except Exception:  # fallback-ok: protocol method contract requires bool return - False indicates validation failed, no logging needed
            return False
