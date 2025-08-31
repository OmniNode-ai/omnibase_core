"""
Environment Model

Extensible environment configuration model that replaces hardcoded
environment enums with flexible, user-defined environments.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field, HttpUrl

from omnibase_core.model.core.model_environment_properties import (
    ModelEnvironmentProperties,
)
from omnibase_core.model.core.model_feature_flags import ModelFeatureFlags

if TYPE_CHECKING:
    from omnibase_core.model.configuration.model_resource_limits import (
        ModelResourceLimits,
    )
    from omnibase_core.model.security.model_security_level import ModelSecurityLevel


class ModelEnvironment(BaseModel):
    """
    Extensible environment configuration model.

    This model allows users and third-party nodes to define custom
    environments beyond the standard dev/staging/prod pattern.
    """

    name: str = Field(..., description="Environment name", pattern="^[a-z][a-z0-9-]*$")

    display_name: str = Field(..., description="Human-readable environment name")

    description: str | None = Field(None, description="Environment description")

    configuration_url: HttpUrl | None = Field(
        None,
        description="Configuration endpoint URL",
    )

    feature_flags: ModelFeatureFlags = Field(
        default_factory=ModelFeatureFlags,
        description="Feature flag configuration",
    )

    security_level: "ModelSecurityLevel" = Field(
        None,
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
    )

    resource_limits: "ModelResourceLimits" = Field(
        None,
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

    def add_environment_variable(self, key: str, value: str) -> None:
        """Add an environment variable."""
        self.environment_variables[key] = value

    def add_custom_property(self, key: str, value: Any) -> None:
        """Add a custom property."""
        # Use the type-safe method from ModelEnvironmentProperties
        if isinstance(value, str | int | bool | float | list | datetime):
            self.custom_properties.set_property(key, value)
        else:
            # Convert to string for unsupported types
            self.custom_properties.set_property(key, str(value))

    def get_environment_variable(
        self,
        key: str,
        default: str | None = None,
    ) -> str | None:
        """Get environment variable value."""
        return self.environment_variables.get(key, default)

    def get_custom_property(self, key: str, default: Any = None) -> Any:
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

    @classmethod
    def create_default(cls, name: str = "development") -> "ModelEnvironment":
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
        from omnibase_core.model.configuration.model_resource_limits import (
            ModelResourceLimits,
        )

        if is_production:
            resource_limits = ModelResourceLimits.create_high_performance()
        elif name in ["staging", "stage", "test", "testing"]:
            resource_limits = ModelResourceLimits.create_standard()
        else:
            resource_limits = ModelResourceLimits.create_minimal()

        return cls(
            name=name,
            display_name=display_name,
            is_production=is_production,
            monitoring_enabled=True,
            auto_scaling_enabled=is_production,
            logging_level=(
                "DEBUG" if name in ["development", "dev", "local"] else "INFO"
            ),
            resource_limits=resource_limits,
        )

    @classmethod
    def create_development(cls) -> "ModelEnvironment":
        """Create a development environment."""
        from omnibase_core.model.configuration.model_resource_limits import (
            ModelResourceLimits,
        )

        env = cls.create_default("development")
        env.feature_flags.enable("debug_mode")
        env.feature_flags.enable("verbose_logging")
        env.logging_level = "DEBUG"
        env.resource_limits = ModelResourceLimits.create_minimal()
        return env

    @classmethod
    def create_staging(cls) -> "ModelEnvironment":
        """Create a staging environment."""
        from omnibase_core.model.configuration.model_resource_limits import (
            ModelResourceLimits,
        )

        env = cls.create_default("staging")
        env.monitoring_enabled = True
        env.auto_scaling_enabled = True
        env.resource_limits = ModelResourceLimits.create_standard()
        return env

    @classmethod
    def create_production(cls) -> "ModelEnvironment":
        """Create a production environment."""
        from omnibase_core.model.configuration.model_resource_limits import (
            ModelResourceLimits,
        )
        from omnibase_core.model.security.model_security_level import ModelSecurityLevel

        env = cls.create_default("production")
        env.security_level = ModelSecurityLevel.create_high_security()
        env.monitoring_enabled = True
        env.auto_scaling_enabled = True
        env.logging_level = "INFO"
        env.resource_limits = ModelResourceLimits.create_high_performance()
        return env
