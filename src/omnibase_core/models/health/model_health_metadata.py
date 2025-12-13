"""
ModelHealthMetadata - Health system metadata and configuration

Health metadata model for storing additional health system configuration,
environment context, and custom attributes.
"""

from typing import Any

from pydantic import BaseModel, Field

from omnibase_core.models.primitives.model_semver import ModelSemVer

from .model_health_attributes import ModelHealthAttributes


class ModelHealthMetadata(BaseModel):
    """
    Health system metadata and configuration model

    This model stores additional health system metadata including
    environment context, configuration, and custom attributes.
    """

    environment: str = Field(
        default="unknown",
        description="Environment context (e.g., development, staging, production)",
    )

    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Health system version",
    )

    check_interval_seconds: int = Field(
        default=30,
        description="Health check interval in seconds",
        ge=1,
        le=3600,
    )

    auto_healing_enabled: bool = Field(
        default=True,
        description="Whether auto-healing mechanisms are enabled",
    )

    maintenance_mode: bool = Field(
        default=False,
        description="Whether system is in maintenance mode",
    )

    notification_enabled: bool = Field(
        default=True,
        description="Whether health notifications are enabled",
    )

    escalation_enabled: bool = Field(
        default=True,
        description="Whether issue escalation is enabled",
    )

    max_issue_retention_days: int = Field(
        default=30,
        description="Maximum days to retain resolved issues",
        ge=1,
        le=365,
    )

    health_score_algorithm: str = Field(
        default="weighted",
        description="Algorithm used for health score calculation",
        pattern="^(simple|weighted|custom)$",
    )

    custom_attributes: ModelHealthAttributes | None = Field(
        default=None,
        description="Custom health attributes for extensibility",
    )

    def is_production_environment(self) -> bool:
        """Check if this is a production environment"""
        return self.environment.lower() in ["production", "prod"]

    def is_development_environment(self) -> bool:
        """Check if this is a development environment"""
        return self.environment.lower() in ["development", "dev", "local"]

    def should_auto_heal(self) -> bool:
        """Check if auto-healing should be performed"""
        return self.auto_healing_enabled and not self.maintenance_mode

    def should_send_notifications(self) -> bool:
        """Check if notifications should be sent"""
        return self.notification_enabled and not self.maintenance_mode

    def get_custom_attribute(self, key: str, default: Any = None) -> Any:
        """Get a custom attribute value"""
        if self.custom_attributes is None:
            return default
        return getattr(self.custom_attributes, key, default)

    def ensure_custom_attributes(self) -> ModelHealthAttributes:
        """Ensure custom attributes exist"""
        if self.custom_attributes is None:
            self.custom_attributes = ModelHealthAttributes()
        return self.custom_attributes

    def get_effective_check_interval(self) -> int:
        """Get effective check interval considering maintenance mode"""
        if self.maintenance_mode:
            # Longer intervals during maintenance
            return min(self.check_interval_seconds * 3, 300)  # Max 5 minutes
        return self.check_interval_seconds

    @classmethod
    def create_production(cls, **kwargs: Any) -> "ModelHealthMetadata":
        """Create production health metadata configuration"""
        # Provide default version if not specified
        if "version" not in kwargs:
            kwargs["version"] = ModelSemVer(major=1, minor=0, patch=0)
        return cls(
            environment="production",
            check_interval_seconds=30,
            auto_healing_enabled=True,
            notification_enabled=True,
            escalation_enabled=True,
            **kwargs,
        )

    @classmethod
    def create_development(cls, **kwargs: Any) -> "ModelHealthMetadata":
        """Create development health metadata configuration"""
        # Provide default version if not specified
        if "version" not in kwargs:
            kwargs["version"] = ModelSemVer(major=1, minor=0, patch=0)
        return cls(
            environment="development",
            check_interval_seconds=60,
            auto_healing_enabled=False,
            notification_enabled=False,
            escalation_enabled=False,
            **kwargs,
        )

    @classmethod
    def create_maintenance_mode(cls, **kwargs: Any) -> "ModelHealthMetadata":
        """Create maintenance mode health metadata configuration"""
        # Provide default version if not specified
        if "version" not in kwargs:
            kwargs["version"] = ModelSemVer(major=1, minor=0, patch=0)
        return cls(
            maintenance_mode=True,
            auto_healing_enabled=False,
            notification_enabled=False,
            check_interval_seconds=120,
            **kwargs,
        )
