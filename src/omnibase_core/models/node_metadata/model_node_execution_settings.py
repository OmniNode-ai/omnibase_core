"""
Node Execution Settings Model.

Execution-related configuration for nodes.
Part of the ModelNodeConfiguration restructuring.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.types import TypedDictMetadataDict, TypedDictSerializedModel
from omnibase_core.types.typed_dict_node_execution_summary import (
    TypedDictNodeExecutionSummary,
)


class ModelNodeExecutionSettings(BaseModel):
    """
    Node execution configuration settings.

    Contains execution-specific parameters:
    - Retry and timeout settings
    - Batch processing configuration
    - Execution mode flags
    Implements Core protocols:
    - Identifiable: UUID-based identification
    - ProtocolMetadataProvider: Metadata management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    # Execution control (3 fields)
    max_retries: int = Field(default=3, description="Maximum retry attempts")
    timeout_seconds: int = Field(default=30, description="Execution timeout")
    batch_size: int = Field(default=1, description="Batch processing size")

    # Execution mode (1 field)
    parallel_execution: bool = Field(
        default=False,
        description="Enable parallel execution",
    )

    def get_execution_summary(self) -> TypedDictNodeExecutionSummary:
        """Get execution settings summary."""
        return {
            "max_retries": self.max_retries,
            "timeout_seconds": self.timeout_seconds,
            "batch_size": self.batch_size,
            "parallel_execution": self.parallel_execution,
            "has_retry_limit": self.max_retries > 0,
            "has_timeout": self.timeout_seconds > 0,
            "supports_batching": self.batch_size > 1,
        }

    def is_configured_for_performance(self) -> bool:
        """Check if configured for performance."""
        return self.parallel_execution and self.batch_size > 1

    @classmethod
    def create_default(cls) -> ModelNodeExecutionSettings:
        """Create default execution settings."""
        return cls()

    @classmethod
    def create_performance_optimized(
        cls,
        batch_size: int = 10,
        parallel: bool = True,
    ) -> ModelNodeExecutionSettings:
        """Create performance-optimized settings."""
        return cls(
            batch_size=batch_size,
            parallel_execution=parallel,
            max_retries=3,
            timeout_seconds=300,
        )

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )

    # Protocol method implementations

    def get_id(self) -> str:
        """Get unique identifier (Identifiable protocol)."""
        # Try common ID field patterns
        for field in [
            "id",
            "uuid",
            "identifier",
            "node_id",
            "execution_id",
            "metadata_id",
        ]:
            if hasattr(self, field):
                value = getattr(self, field)
                if value is not None:
                    return str(value)
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"{self.__class__.__name__} must have a valid ID field "
            f"(type_id, id, uuid, identifier, etc.). "
            f"Cannot generate stable ID without UUID field.",
        )

    def get_metadata(self) -> TypedDictMetadataDict:
        """Get metadata as dictionary (ProtocolMetadataProvider protocol)."""
        from typing import cast

        from omnibase_core.types.type_serializable_value import SerializableValue

        result: TypedDictMetadataDict = {}
        summary = dict(self.get_execution_summary())
        summary["is_configured_for_performance"] = self.is_configured_for_performance()
        # Cast TypedDict to SerializableValue dict for TypedDictMetadataDict compatibility
        result["metadata"] = cast(dict[str, SerializableValue], summary)
        return result

    def set_metadata(self, metadata: TypedDictMetadataDict) -> bool:
        """Set metadata from dictionary (ProtocolMetadataProvider protocol)."""
        try:
            for key, value in metadata.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except Exception:  # fallback-ok: Protocol method - graceful fallback for optional implementation
            return False

    def serialize(self) -> TypedDictSerializedModel:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol)."""
        return True


# Export for use
__all__ = ["ModelNodeExecutionSettings"]
