"""
ModelConfigurationSummary: Configuration summary model.

This model provides structured configuration summary without using Any types.
"""

from typing import Dict, List

from pydantic import BaseModel, Field


class ModelConfigurationSummary(BaseModel):
    """Configuration summary model."""

    backend_type: str = Field(..., description="Backend type identifier")
    backend_capabilities: Dict[str, bool] = Field(
        default_factory=dict, description="Backend capabilities"
    )
    security_profile: Dict[str, str] = Field(
        default_factory=dict, description="Security profile settings"
    )
    performance_profile: Dict[str, str] = Field(
        default_factory=dict, description="Performance profile settings"
    )
    audit_enabled: bool = Field(..., description="Audit logging enabled status")
    fallback_enabled: bool = Field(..., description="Fallback mechanism enabled status")
    fallback_backends: List[str] = Field(
        default_factory=list, description="Available fallback backends"
    )
    environment_type: str = Field(..., description="Detected environment type")
    production_ready: bool = Field(..., description="Production readiness status")

    def to_dict(self) -> Dict[str, object]:
        """Convert to dictionary for backwards compatibility."""
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
