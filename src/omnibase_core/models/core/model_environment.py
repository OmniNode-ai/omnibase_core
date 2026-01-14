"""
Environment Model.

Extensible environment configuration model that replaces hardcoded
environment enums with flexible, user-defined environments.

IMPORT ORDER CONSTRAINTS (Critical - Do Not Break):
===============================================
This module is part of a carefully managed import chain to avoid circular dependencies.

Safe Runtime Imports:
- omnibase_core.models.examples.model_environment_properties (no circular risk)
- omnibase_core.models.core.model_feature_flags (no circular risk)
- omnibase_core.errors.error_codes (imports only from types.core_types and enums)
- pydantic, typing, datetime (standard library)

Import Chain Position:
1. errors.error_codes → types.core_types
2. THIS MODULE → errors.error_codes (OK - no circle)
3. types.constraints → TYPE_CHECKING import of errors.error_codes
4. models.* → types.constraints

This module can safely import error_codes because error_codes only imports
from types.core_types (not from models or types.constraints).
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from omnibase_core.constants.constants_field_limits import MAX_NAME_LENGTH
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.core.model_feature_flags import ModelFeatureFlags

# Safe runtime import - error_codes only imports from types.core_types
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.examples.model_environment_properties import (
    ModelEnvironmentProperties,
)

if TYPE_CHECKING:
    from omnibase_core.models.configuration.model_resource_limits import (
        ModelResourceLimits,
    )
    from omnibase_core.models.security.model_security_level import ModelSecurityLevel


class ModelEnvironment(BaseModel):
    """
    Extensible environment configuration model with ONEX compliance.

    This model allows users and third-party nodes to define custom
    environments beyond the standard dev/staging/prod pattern.
    Implements Core protocols:
    - Configurable: Environment-specific configuration management
    - Validatable: Comprehensive validation and verification
    """

    name: str = Field(
        default=...,
        description="Environment name",
        pattern="^[a-z][a-z0-9-]*$",
        min_length=1,
        max_length=50,
    )

    display_name: str = Field(
        default=...,
        description="Human-readable environment name",
        min_length=1,
        max_length=MAX_NAME_LENGTH,
    )

    description: str | None = Field(
        default=None,
        description="Environment description",
        max_length=500,
    )

    configuration_url: HttpUrl | None = Field(
        default=None,
        description="Configuration endpoint URL",
    )

    feature_flags: ModelFeatureFlags = Field(
        default_factory=ModelFeatureFlags,
        description="Feature flag configuration",
    )

    security_level: ModelSecurityLevel | None = Field(
        default=None,
        description="Security requirements and configuration",
    )

    is_production: bool = Field(
        default=False,
        description="Whether this is a production environment",
    )

    is_ephemeral: bool = Field(
        default=False,
        description="Whether this environment is temporary/ephemeral",
    )

    auto_scaling_enabled: bool = Field(
        default=False,
        description="Whether auto-scaling is enabled",
    )

    monitoring_enabled: bool = Field(
        default=True,
        description="Whether monitoring is enabled",
    )

    logging_level: str = Field(
        default="INFO",
        description="Default logging level for this environment",
        pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$",
    )

    resource_limits: ModelResourceLimits | None = Field(
        default=None,
        description="Resource limits for this environment",
    )

    environment_variables: dict[str, str] = Field(
        default_factory=dict,
        description="Environment-specific variables",
    )

    custom_properties: ModelEnvironmentProperties = Field(
        default_factory=ModelEnvironmentProperties,
        description="Custom environment properties",
    )

    model_config = ConfigDict(
        extra="ignore",
        arbitrary_types_allowed=True,
        use_enum_values=False,
        validate_assignment=True,
    )

    # === Environment Type Detection ===

    def is_development(self) -> bool:
        """Check if this is a development environment."""
        return self.name in ["development", "dev", "local"]

    def is_staging(self) -> bool:
        """Check if this is a staging environment."""
        return self.name in ["staging", "stage", "test", "testing"]

    def is_secure(self) -> bool:
        """Check if this environment has high security requirements."""
        if self.security_level is None:
            return self.is_production
        return self.security_level.is_high_security() or self.is_production

    def supports_debug(self) -> bool:
        """Check if debug features are allowed in this environment."""
        return not self.is_production or self.feature_flags.is_enabled(
            "debug_in_prod",
            False,
        )

    # === Performance Configuration ===

    def get_timeout_multiplier(self) -> float:
        """Get timeout multiplier for this environment."""
        if self.is_production:
            return 2.0  # Longer timeouts in production
        if self.is_development():
            return 0.5  # Shorter timeouts in development
        return 1.0  # Default timeouts

    def get_retry_multiplier(self) -> float:
        """Get retry multiplier for this environment."""
        if self.is_production:
            return 2.0  # More retries in production
        if self.is_development():
            return 0.5  # Fewer retries in development
        return 1.0  # Default retries

    # === Environment Variable Management ===

    def add_environment_variable(self, key: str, value: str) -> None:
        """Add an environment variable."""
        if not key or not isinstance(key, str):
            msg = "Environment variable key must be a non-empty string"
            raise ModelOnexError(msg, error_code=EnumCoreErrorCode.VALIDATION_ERROR)

        self.environment_variables[key] = value

    def add_custom_property(
        self, key: str, value: str | int | float | bool | datetime | list[str]
    ) -> None:
        """Add a custom property."""
        if not key or not isinstance(key, str):
            msg = "Custom property key must be a non-empty string"
            raise ModelOnexError(msg, error_code=EnumCoreErrorCode.VALIDATION_ERROR)

        # Import ModelPropertyValue for factory methods
        from omnibase_core.models.examples.model_property_value import (
            ModelPropertyValue,
        )

        # Use the type-safe method from ModelEnvironmentProperties
        # Convert value to ModelPropertyValue using factory methods
        prop_value: ModelPropertyValue
        if isinstance(value, str):
            prop_value = ModelPropertyValue.from_string(value)
        elif isinstance(
            value, bool
        ):  # Must check bool before int (bool is subclass of int)
            prop_value = ModelPropertyValue.from_bool(value)
        elif isinstance(value, int):
            prop_value = ModelPropertyValue.from_int(value)
        elif isinstance(value, float):
            prop_value = ModelPropertyValue.from_float(value)
        elif isinstance(value, datetime):
            prop_value = ModelPropertyValue.from_datetime(value)
        else:
            # list[str] - convert all items to strings
            prop_value = ModelPropertyValue.from_string_list([str(v) for v in value])

        self.custom_properties.set_property(key, prop_value)

    def get_environment_variable(
        self,
        key: str,
        default: str | None = None,
    ) -> str | None:
        """Get environment variable value."""
        return self.environment_variables.get(key, default)

    def get_custom_property(self, key: str, default: object = None) -> object:
        """Get custom property value."""
        if self.custom_properties.has_property(key):
            # Try to return the most appropriate type
            value = self.custom_properties.properties.get(key)
            return value if value is not None else default
        return default

    def to_environment_dict(self) -> dict[str, str]:
        """Convert to environment variables dictionary."""
        env_dict = self.environment_variables.copy()

        # Add standard environment variables
        env_dict["ONEX_ENVIRONMENT"] = self.name
        env_dict["ONEX_ENVIRONMENT_DISPLAY"] = self.display_name
        env_dict["ONEX_IS_PRODUCTION"] = str(self.is_production).lower()
        env_dict["ONEX_IS_EPHEMERAL"] = str(self.is_ephemeral).lower()
        env_dict["ONEX_LOGGING_LEVEL"] = self.logging_level
        env_dict["ONEX_MONITORING_ENABLED"] = str(self.monitoring_enabled).lower()
        env_dict["ONEX_AUTO_SCALING_ENABLED"] = str(self.auto_scaling_enabled).lower()

        if self.configuration_url:
            env_dict["ONEX_CONFIG_URL"] = str(self.configuration_url)

        # Add custom properties as environment variables
        custom_env = self.custom_properties.to_environment_variables()
        env_dict.update(custom_env)

        # Add resource limits as environment variables if constrained
        if self.resource_limits and self.resource_limits.is_constrained():
            if self.resource_limits.cpu_cores is not None:
                env_dict["ONEX_CPU_CORES"] = str(self.resource_limits.cpu_cores)
            if self.resource_limits.memory_mb is not None:
                env_dict["ONEX_MEMORY_MB"] = str(self.resource_limits.memory_mb)
            if self.resource_limits.storage_gb is not None:
                env_dict["ONEX_STORAGE_GB"] = str(self.resource_limits.storage_gb)
            if self.resource_limits.max_connections is not None:
                env_dict["ONEX_MAX_CONNECTIONS"] = str(
                    self.resource_limits.max_connections,
                )
            if self.resource_limits.max_requests_per_second is not None:
                env_dict["ONEX_MAX_RPS"] = str(
                    self.resource_limits.max_requests_per_second,
                )

        return env_dict

    # === Factory Methods ===

    @classmethod
    def create_default(cls, name: str = "development") -> ModelEnvironment:
        """Create a default environment configuration."""
        display_names = {
            "development": "Development",
            "dev": "Development",
            "local": "Local Development",
            "staging": "Staging",
            "stage": "Staging",
            "test": "Testing",
            "testing": "Testing",
            "production": "Production",
            "prod": "Production",
        }

        display_name = display_names.get(name, name.title())
        is_production = name in ["production", "prod"]

        # Set appropriate resource limits based on environment
        from omnibase_core.models.configuration.model_resource_limits import (
            ModelResourceLimits,
        )

        if is_production:
            resource_limits = ModelResourceLimits(
                cpu_cores=8.0,
                memory_mb=16384,
                storage_gb=100.0,
                max_connections=10000,
                max_requests_per_second=1000.0,
                max_processes=1000,
                max_threads=10000,
                network_bandwidth_mbps=1000.0,
                max_file_descriptors=100000,
                execution_time_seconds=3600,
                queue_size=10000,
                max_retries=5,
            )
        elif name in {"staging", "stage", "test", "testing"}:
            resource_limits = ModelResourceLimits(
                cpu_cores=2.0,
                memory_mb=2048,
                storage_gb=10.0,
                max_connections=1000,
                max_requests_per_second=100.0,
                max_processes=100,
                max_threads=1000,
                network_bandwidth_mbps=100.0,
                max_file_descriptors=10000,
                execution_time_seconds=1800,
                queue_size=1000,
                max_retries=3,
            )
        else:
            resource_limits = ModelResourceLimits(
                cpu_cores=1.0,
                memory_mb=512,
                storage_gb=1.0,
                max_connections=100,
                max_requests_per_second=10.0,
                max_processes=100,
                max_threads=1000,
                network_bandwidth_mbps=100.0,
                max_file_descriptors=1000,
                execution_time_seconds=300,
                queue_size=100,
                max_retries=1,
            )

        return cls(
            name=name,
            display_name=display_name,
            description=f"Default {name} environment configuration",
            configuration_url=None,
            security_level=None,
            is_production=is_production,
            monitoring_enabled=True,
            auto_scaling_enabled=is_production,
            logging_level=(
                "DEBUG" if name in {"development", "dev", "local"} else "INFO"
            ),
            resource_limits=resource_limits,
        )

    @classmethod
    def create_development(cls) -> ModelEnvironment:
        """Create a development environment."""
        from omnibase_core.models.configuration.model_resource_limits import (
            ModelResourceLimits,
        )

        env = cls.create_default("development")
        env.feature_flags.enable("debug_mode")
        env.feature_flags.enable("verbose_logging")
        env.logging_level = "DEBUG"
        env.resource_limits = ModelResourceLimits(
            cpu_cores=1.0,
            memory_mb=512,
            storage_gb=1.0,
            max_connections=100,
            max_requests_per_second=10.0,
            max_processes=100,
            max_threads=1000,
            network_bandwidth_mbps=100.0,
            max_file_descriptors=1000,
            execution_time_seconds=300,
            queue_size=100,
            max_retries=1,
        )
        return env

    @classmethod
    def create_staging(cls) -> ModelEnvironment:
        """Create a staging environment."""
        from omnibase_core.models.configuration.model_resource_limits import (
            ModelResourceLimits,
        )

        env = cls.create_default("staging")
        env.monitoring_enabled = True
        env.auto_scaling_enabled = True
        env.resource_limits = ModelResourceLimits(
            cpu_cores=2.0,
            memory_mb=2048,
            storage_gb=10.0,
            max_connections=1000,
            max_requests_per_second=100.0,
            max_processes=100,
            max_threads=1000,
            network_bandwidth_mbps=100.0,
            max_file_descriptors=10000,
            execution_time_seconds=1800,
            queue_size=1000,
            max_retries=3,
        )
        return env

    @classmethod
    def create_production(cls) -> ModelEnvironment:
        """Create a production environment."""
        from omnibase_core.models.configuration.model_resource_limits import (
            ModelResourceLimits,
        )
        from omnibase_core.models.security.model_security_level import (
            ModelSecurityLevel,
        )

        env = cls.create_default("production")
        env.security_level = ModelSecurityLevel.create_high_security()
        env.monitoring_enabled = True
        env.auto_scaling_enabled = True
        env.logging_level = "INFO"
        env.resource_limits = ModelResourceLimits(
            cpu_cores=8.0,
            memory_mb=16384,
            storage_gb=100.0,
            max_connections=10000,
            max_requests_per_second=1000.0,
            max_processes=1000,
            max_threads=10000,
            network_bandwidth_mbps=1000.0,
            max_file_descriptors=100000,
            execution_time_seconds=3600,
            queue_size=10000,
            max_retries=5,
        )
        return env

    # === Additional Factory Methods ===

    @classmethod
    def create_custom(
        cls,
        name: str,
        display_name: str,
        description: str | None = None,
        *,
        is_production: bool = False,
        is_ephemeral: bool = False,
        auto_scaling_enabled: bool = False,
        monitoring_enabled: bool = True,
        logging_level: str = "INFO",
        security_level: ModelSecurityLevel | None = None,
        configuration_url: HttpUrl | None = None,
    ) -> ModelEnvironment:
        """Create a custom environment configuration."""
        return cls(
            name=name,
            display_name=display_name,
            description=description,
            configuration_url=configuration_url,
            security_level=security_level,
            is_production=is_production,
            is_ephemeral=is_ephemeral,
            auto_scaling_enabled=auto_scaling_enabled,
            monitoring_enabled=monitoring_enabled,
            logging_level=logging_level,
            resource_limits=None,
        )

    @classmethod
    def create_testing(cls) -> ModelEnvironment:
        """Create a testing environment."""
        return cls.create_default("test")

    @classmethod
    def create_local(cls) -> ModelEnvironment:
        """Create a local development environment."""
        env = cls.create_default("local")
        env.feature_flags.enable("debug_mode")
        env.feature_flags.enable("verbose_logging")
        env.feature_flags.enable("hot_reload")
        env.logging_level = "DEBUG"
        return env


# Rebuild model to resolve forward references
# With `from __future__ import annotations`, this should not be needed,
# but we do it explicitly to ensure Pydantic has all types available
try:
    from omnibase_core.models.configuration.model_resource_limits import (
        ModelResourceLimits,
    )
    from omnibase_core.models.security.model_security_level import (
        ModelSecurityLevel,
    )

    ModelEnvironment.model_rebuild()
except ImportError:
    # If imports fail (e.g., during initial module loading), skip rebuild
    # The model will be rebuilt on first use
    pass
