"""
Node configuration model for node settings and parameters.
Restructured to use focused sub-models for better organization.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.core.model_custom_properties import ModelCustomProperties
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.types import TypedDictMetadataDict, TypedDictSerializedModel
from omnibase_core.types.typed_dict_node_configuration_summary import (
    TypedDictNodeConfigurationSummary,
)

from .model_node_connection_settings import ModelNodeConnectionSettings
from .model_node_execution_settings import ModelNodeExecutionSettings
from .model_node_feature_flags import ModelNodeFeatureFlags
from .model_node_resource_limits import ModelNodeResourceLimits


class ModelNodeConfiguration(BaseModel):
    """Configuration for a node with structured sub-components."""

    # Grouped configuration components (4 primary components)
    execution: ModelNodeExecutionSettings = Field(
        default_factory=lambda: ModelNodeExecutionSettings(),
        description="Execution configuration settings",
    )
    resources: ModelNodeResourceLimits = Field(
        default_factory=lambda: ModelNodeResourceLimits(),
        description="Resource limitation settings",
    )
    features: ModelNodeFeatureFlags = Field(
        default_factory=lambda: ModelNodeFeatureFlags(),
        description="Feature toggle settings",
    )
    connection: ModelNodeConnectionSettings = Field(
        default_factory=lambda: ModelNodeConnectionSettings(),
        description="Connection settings",
    )

    # Custom configuration with type safety
    custom_properties: ModelCustomProperties = Field(
        default_factory=lambda: ModelCustomProperties(),
        description="Custom configuration properties",
    )

    # Delegation properties
    @property
    def max_retries(self) -> int:
        """Maximum retry attempts (delegated to execution)."""
        return self.execution.max_retries

    @max_retries.setter
    def max_retries(self, value: int | None) -> None:
        """Set maximum retry attempts."""
        self.execution.max_retries = value if value is not None else 3

    @property
    def timeout_seconds(self) -> int:
        """Execution timeout (delegated to execution)."""
        return self.execution.timeout_seconds

    @timeout_seconds.setter
    def timeout_seconds(self, value: int | None) -> None:
        """Set execution timeout."""
        self.execution.timeout_seconds = value if value is not None else 30

    @property
    def batch_size(self) -> int:
        """Batch processing size (delegated to execution)."""
        return self.execution.batch_size

    @batch_size.setter
    def batch_size(self, value: int | None) -> None:
        """Set batch processing size."""
        self.execution.batch_size = value if value is not None else 1

    @property
    def parallel_execution(self) -> bool:
        """Parallel execution flag (delegated to execution)."""
        return self.execution.parallel_execution

    @parallel_execution.setter
    def parallel_execution(self, value: bool) -> None:
        """Set parallel execution flag."""
        self.execution.parallel_execution = value

    @property
    def max_memory_mb(self) -> int:
        """Maximum memory usage (delegated to resources)."""
        return self.resources.max_memory_mb

    @max_memory_mb.setter
    def max_memory_mb(self, value: int | None) -> None:
        """Set maximum memory usage."""
        self.resources.max_memory_mb = value if value is not None else 1024

    @property
    def max_cpu_percent(self) -> float:
        """Maximum CPU usage (delegated to resources)."""
        return self.resources.max_cpu_percent

    @max_cpu_percent.setter
    def max_cpu_percent(self, value: float | None) -> None:
        """Set maximum CPU usage."""
        self.resources.max_cpu_percent = value if value is not None else 100.0

    @property
    def enable_caching(self) -> bool:
        """Caching enabled flag (delegated to features)."""
        return self.features.enable_caching

    @enable_caching.setter
    def enable_caching(self, value: bool) -> None:
        """Set caching enabled flag."""
        self.features.enable_caching = value

    @property
    def enable_monitoring(self) -> bool:
        """Monitoring enabled flag (delegated to features)."""
        return self.features.enable_monitoring

    @enable_monitoring.setter
    def enable_monitoring(self, value: bool) -> None:
        """Set monitoring enabled flag."""
        self.features.enable_monitoring = value

    @property
    def enable_tracing(self) -> bool:
        """Tracing enabled flag (delegated to features)."""
        return self.features.enable_tracing

    @enable_tracing.setter
    def enable_tracing(self, value: bool) -> None:
        """Set tracing enabled flag."""
        self.features.enable_tracing = value

    @property
    def endpoint(self) -> str | None:
        """Service endpoint (delegated to connection)."""
        return self.connection.endpoint

    @endpoint.setter
    def endpoint(self, value: str | None) -> None:
        """Set service endpoint."""
        self.connection.endpoint = value

    @property
    def port(self) -> int | None:
        """Service port (delegated to connection)."""
        return self.connection.port

    @port.setter
    def port(self, value: int | None) -> None:
        """Set service port."""
        self.connection.port = value

    @property
    def protocol(self) -> str | None:
        """Communication protocol (delegated to connection, converted to string)."""
        return self.connection.protocol.value if self.connection.protocol else None

    @protocol.setter
    def protocol(self, value: str | None) -> None:
        """Set communication protocol from string."""
        if value is None:
            self.connection.protocol = None
        else:
            from omnibase_core.enums.enum_protocol_type import EnumProtocolType

            try:
                self.connection.protocol = EnumProtocolType(value)
            except ValueError:
                self.connection.protocol = None

    def get_configuration_summary(self) -> TypedDictNodeConfigurationSummary:
        """Get comprehensive configuration summary."""
        return {
            "execution": self.execution.get_execution_summary(),
            "resources": self.resources.get_resource_summary(),
            "features": self.features.get_feature_summary(),
            "connection": self.connection.get_connection_summary(),
            "is_production_ready": self.is_production_ready(),
            "is_performance_optimized": self.is_performance_optimized(),
            "has_custom_settings": self.has_custom_settings(),
        }

    def is_production_ready(self) -> bool:
        """Check if configuration is production-ready."""
        return self.features.is_production_ready() and self.features.enable_monitoring

    def is_performance_optimized(self) -> bool:
        """Check if configuration is performance-optimized."""
        return (
            self.execution.is_configured_for_performance()
            and self.features.enable_caching
        )

    def has_custom_settings(self) -> bool:
        """Check if any custom settings are configured."""
        return bool(
            self.custom_properties.custom_strings
            or self.custom_properties.custom_flags
            or self.custom_properties.custom_numbers,
        )

    @classmethod
    def create_default(cls) -> ModelNodeConfiguration:
        """Create default node configuration."""
        return cls()

    @classmethod
    def create_production(
        cls,
        endpoint: str | None = None,
        port: int | None = None,
    ) -> ModelNodeConfiguration:
        """Create production-ready node configuration."""
        config = cls(
            features=ModelNodeFeatureFlags.create_production(),
            execution=ModelNodeExecutionSettings.create_performance_optimized(),
        )
        if endpoint:
            config.connection.endpoint = endpoint
        if port:
            config.connection.port = port
        return config

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
        # Cast TypedDict to SerializableValue dict for TypedDictMetadataDict compatibility
        result["metadata"] = cast(
            dict[str, SerializableValue], dict(self.get_configuration_summary())
        )
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

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )


# Export for use
__all__ = ["ModelNodeConfiguration"]
