"""
ModelConfigurationSummary: Configuration summary model.

This model provides structured configuration summary without using Any types.
"""

from pydantic import BaseModel, Field


class ModelConfigurationSummary(BaseModel):
    """Configuration summary model."""

    backend_type: str = Field(default=..., description="Backend type identifier")
    backend_capabilities: dict[str, bool] = Field(
        default_factory=dict,
        description="Backend capabilities",
    )
    security_profile: dict[str, str] = Field(
        default_factory=dict,
        description="Security profile settings",
    )
    performance_profile: dict[str, str] = Field(
        default_factory=dict,
        description="Performance profile settings",
    )
    audit_enabled: bool = Field(default=..., description="Audit logging enabled status")
    fallback_enabled: bool = Field(
        default=..., description="Fallback mechanism enabled status"
    )
    fallback_backends: list[str] = Field(
        default_factory=list,
        description="Available fallback backends",
    )
    environment_type: str = Field(default=..., description="Detected environment type")
    production_ready: bool = Field(
        default=..., description="Production readiness status"
    )

    def to_dict(self) -> dict[str, object]:
        """Convert to dictionary for current standards."""
        # Custom dictionary format for configuration summary
        return {
            "backend_type": self.backend_type,
            "backend_capabilities": self.backend_capabilities,
            "security_profile": self.security_profile,
            "performance_profile": self.performance_profile,
            "audit_enabled": self.audit_enabled,
            "fallback_enabled": self.fallback_enabled,
            "fallback_backends": self.fallback_backends,
            "environment_type": self.environment_type,
            "production_ready": self.production_ready,
        }
