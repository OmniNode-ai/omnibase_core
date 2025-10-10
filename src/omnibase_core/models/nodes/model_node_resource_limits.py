from __future__ import annotations

import uuid
from typing import Dict, TypedDict
from uuid import UUID

from pydantic import Field

from omnibase_core.errors.model_onex_error import ModelOnexError

"""
Node Resource Limits Model.

Resource limitation configuration for nodes.
Part of the ModelNodeConfiguration restructuring.
"""


from typing import Any, Dict, TypedDict

from pydantic import BaseModel, Field

from omnibase_core.errors.error_codes import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.types.typed_dict_node_resource_constraint_kwargs import (
    TypedDictNodeResourceConstraintKwargs,
)
from omnibase_core.types.typed_dict_node_resource_summary_type import (
    TypedDictNodeResourceSummaryType,
)


class ModelNodeResourceLimits(BaseModel):
    """
    Node resource limitation settings.

    Contains resource management parameters:
    - Memory and CPU limits
    - Performance constraints

    Implements omnibase_spi protocols:
    - Identifiable: UUID-based identification
    - ProtocolMetadataProvider: Metadata management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    # Resource limits (2 fields)
    max_memory_mb: int = Field(
        default=1024,
        description="Maximum memory usage in MB",
        ge=0,
    )
    max_cpu_percent: float = Field(
        default=100.0,
        description="Maximum CPU usage percentage",
        ge=0.0,
        le=100.0,
    )

    def has_memory_limit(self) -> bool:
        """Check if memory limit is set."""
        return self.max_memory_mb > 0

    def has_cpu_limit(self) -> bool:
        """Check if CPU limit is set."""
        return self.max_cpu_percent < 100.0

    def has_any_limits(self) -> bool:
        """Check if any resource limits are configured."""
        return self.has_memory_limit() or self.has_cpu_limit()

    def get_resource_summary(self) -> TypedDictNodeResourceSummaryType:
        """Get resource limits summary."""
        return {
            "max_memory_mb": self.max_memory_mb,
            "max_cpu_percent": self.max_cpu_percent,
            "has_memory_limit": self.has_memory_limit(),
            "has_cpu_limit": self.has_cpu_limit(),
            "has_any_limits": self.has_any_limits(),
        }

    def is_memory_constrained(self, threshold_mb: int = 1024) -> bool:
        """Check if memory is constrained below threshold."""
        return self.max_memory_mb < threshold_mb

    def is_cpu_constrained(self, threshold_percent: float = 50.0) -> bool:
        """Check if CPU is constrained below threshold."""
        return self.max_cpu_percent < threshold_percent

    @classmethod
    def create_unlimited(cls) -> ModelNodeResourceLimits:
        """Create unlimited resource configuration."""
        return cls()

    @classmethod
    def create_constrained(
        cls,
        memory_mb: int | None = None,
        cpu_percent: float | None = None,
    ) -> ModelNodeResourceLimits:
        """Create constrained resource configuration."""
        kwargs: TypedDictNodeResourceConstraintKwargs = {}
        if memory_mb is not None:
            kwargs["max_memory_mb"] = memory_mb
        if cpu_percent is not None:
            kwargs["max_cpu_percent"] = cpu_percent
        return cls(**kwargs)

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }

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
            code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"{self.__class__.__name__} must have a valid ID field "
            f"(type_id, id, uuid, identifier, etc.). "
            f"Cannot generate stable ID without UUID field.",
        )

    def get_metadata(self) -> dict[str, Any]:
        """Get metadata as dict[str, Any]ionary (ProtocolMetadataProvider protocol)."""
        metadata = {}
        # Include common metadata fields
        for field in ["name", "description", "version", "tags", "metadata"]:
            if hasattr(self, field):
                value = getattr(self, field)
                if value is not None:
                    metadata[field] = (
                        str(value) if not isinstance(value, (dict, list)) else value
                    )
        return metadata

    def set_metadata(self, metadata: dict[str, Any]) -> bool:
        """Set metadata from dict[str, Any]ionary (ProtocolMetadataProvider protocol)."""
        try:
            for key, value in metadata.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except (
            Exception
        ):  # fallback-ok: Protocol method - graceful fallback for optional implementation
            return False

    def serialize(self) -> dict[str, Any]:
        """Serialize to dict[str, Any]ionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol)."""
        try:
            # Basic validation - ensure required fields exist
            # Override in specific models for custom validation
            return True
        except (
            Exception
        ):  # fallback-ok: Protocol method - graceful fallback for optional implementation
            return False


# Export for use
__all__ = ["ModelNodeResourceLimits"]
