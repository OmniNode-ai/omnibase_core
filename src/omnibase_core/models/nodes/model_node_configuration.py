"""
Node configuration model for node settings and parameters.
Restructured to use focused sub-models for better organization.
"""

from __future__ import annotations

from typing import TypedDict

from pydantic import BaseModel, Field

from ..core.model_custom_properties import ModelCustomProperties
from .model_node_connection_settings import ModelNodeConnectionSettings
from .model_node_execution_settings import ModelNodeExecutionSettings
from .model_node_feature_flags import ModelNodeFeatureFlags
from .model_node_resource_limits import ModelNodeResourceLimits


class TypedDictNodeConfigurationSummary(TypedDict):
    """Type-safe dictionary for node configuration summary."""

    execution: dict[str, int | bool | None]
    resources: dict[str, int | float | bool | None]
    features: dict[str, bool | list[str] | int]
    connection: dict[str, str | int | bool | None]
    is_production_ready: bool
    is_performance_optimized: bool
    has_custom_settings: bool


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
    def max_retries(self) -> int | None:
        """Maximum retry attempts (delegated to execution)."""
        return self.execution.max_retries

    @max_retries.setter
    def max_retries(self, value: int | None) -> None:
        """Set maximum retry attempts."""
        self.execution.max_retries = value

    @property
    def timeout_seconds(self) -> int | None:
        """Execution timeout (delegated to execution)."""
        return self.execution.timeout_seconds

    @timeout_seconds.setter
    def timeout_seconds(self, value: int | None) -> None:
        """Set execution timeout."""
        self.execution.timeout_seconds = value

    @property
    def batch_size(self) -> int | None:
        """Batch processing size (delegated to execution)."""
        return self.execution.batch_size

    @batch_size.setter
    def batch_size(self, value: int | None) -> None:
        """Set batch processing size."""
        self.execution.batch_size = value

    @property
    def parallel_execution(self) -> bool:
        """Parallel execution flag (delegated to execution)."""
        return self.execution.parallel_execution

    @parallel_execution.setter
    def parallel_execution(self, value: bool) -> None:
        """Set parallel execution flag."""
        self.execution.parallel_execution = value

    @property
    def max_memory_mb(self) -> int | None:
        """Maximum memory usage (delegated to resources)."""
        return self.resources.max_memory_mb

    @max_memory_mb.setter
    def max_memory_mb(self, value: int | None) -> None:
        """Set maximum memory usage."""
        self.resources.max_memory_mb = value

    @property
    def max_cpu_percent(self) -> float | None:
        """Maximum CPU usage (delegated to resources)."""
        return self.resources.max_cpu_percent

    @max_cpu_percent.setter
    def max_cpu_percent(self, value: float | None) -> None:
        """Set maximum CPU usage."""
        self.resources.max_cpu_percent = value

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
            from ...enums.enum_protocol_type import EnumProtocolType

            try:
                self.connection.protocol = EnumProtocolType(value)
            except ValueError:
                self.connection.protocol = None

    @property
    def custom_settings(self) -> dict[str, str] | None:
        """Custom string settings (backward compatible)."""
        return (
            self.custom_properties.custom_strings
            if self.custom_properties.custom_strings
            else None
        )

    @custom_settings.setter
    def custom_settings(self, value: dict[str, str] | None) -> None:
        """Set custom string settings."""
        if value:
            self.custom_properties.custom_strings.update(value)
        else:
            self.custom_properties.custom_strings.clear()

    @property
    def custom_flags(self) -> dict[str, bool] | None:
        """Custom boolean flags (backward compatible)."""
        return (
            self.custom_properties.custom_flags
            if self.custom_properties.custom_flags
            else None
        )

    @custom_flags.setter
    def custom_flags(self, value: dict[str, bool] | None) -> None:
        """Set custom boolean flags."""
        if value:
            self.custom_properties.custom_flags.update(value)
        else:
            self.custom_properties.custom_flags.clear()

    @property
    def custom_limits(self) -> dict[str, int] | None:
        """Custom numeric limits (backward compatible)."""
        numeric_props = self.custom_properties.custom_numbers
        if not numeric_props:
            return None
        # Convert float values to int
        return {k: int(v) for k, v in numeric_props.items()}

    @custom_limits.setter
    def custom_limits(self, value: dict[str, int] | None) -> None:
        """Set custom numeric limits."""
        if value:
            # Convert int values to float for storage
            float_values = {k: float(v) for k, v in value.items()}
            self.custom_properties.custom_numbers.update(float_values)
        else:
            self.custom_properties.custom_numbers.clear()

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
            or self.custom_properties.custom_numbers
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


# Export for use
__all__ = ["ModelNodeConfiguration"]
