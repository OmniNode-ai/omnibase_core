"""
Registry Mode Model for ONEX Configuration-Driven Registry System.

This module provides the ModelRegistryMode for defining registry operation modes
with extensible configuration. Extracted from model_service_configuration.py
for modular architecture compliance.

Author: OmniNode Team
"""

from enum import Enum
from typing import TYPE_CHECKING, Optional

from pydantic import BaseModel, Field

from omnibase_core.models.core import ModelGenericMetadata

if TYPE_CHECKING:
    from omnibase_core.models.core import ModelResourceAllocation


class RegistryModeCategory(str, Enum):
    """Core registry mode categories."""

    PRODUCTION = "production"
    DISTRIBUTED = "distributed"
    DEVELOPMENT = "development"
    BOOTSTRAP = "bootstrap"
    EMERGENCY = "emergency"
    TESTING = "testing"


class ModelRegistryMode(BaseModel):
    """Scalable registry mode configuration model."""

    mode_category: RegistryModeCategory = Field(
        ...,
        description="The category of registry mode",
    )

    custom_mode_name: str | None = Field(
        None,
        description="Custom mode name (for specialized deployment scenarios)",
    )

    performance_profile: str | None = Field(
        None,
        description="Performance optimization profile (high_throughput, low_latency, balanced)",
    )

    security_level: str = Field(
        "standard",
        description="Security level (minimal, standard, enhanced, maximum)",
    )

    fault_tolerance: str = Field(
        "standard",
        description="Fault tolerance level (minimal, standard, high, maximum)",
    )

    resource_allocation: Optional["ModelResourceAllocation"] = Field(
        None,
        description="Resource allocation limits and preferences",
    )

    feature_flags: dict[str, bool] = Field(
        default_factory=dict,
        description="Feature enablement flags for this mode",
    )

    monitoring_level: str = Field(
        "standard",
        description="Monitoring verbosity (minimal, standard, verbose, debug)",
    )

    allowed_operations: list[str] = Field(
        default_factory=lambda: ["read", "write", "admin"],
        description="Operations allowed in this registry mode",
    )

    metadata: ModelGenericMetadata | None = Field(
        default_factory=lambda: ModelGenericMetadata(),
        description="Additional mode-specific configuration",
    )

    def get_effective_mode_name(self) -> str:
        """Get the effective registry mode name."""
        if self.custom_mode_name:
            return self.custom_mode_name
        return self.mode_category.value

    def is_production_like(self) -> bool:
        """Check if this mode has production-like characteristics."""
        return self.mode_category in [
            RegistryModeCategory.PRODUCTION,
            RegistryModeCategory.DISTRIBUTED,
        ]

    def is_development_like(self) -> bool:
        """Check if this mode has development-like characteristics."""
        return self.mode_category in [
            RegistryModeCategory.DEVELOPMENT,
            RegistryModeCategory.TESTING,
        ]

    def is_emergency_mode(self) -> bool:
        """Check if this is an emergency/bootstrap mode."""
        return self.mode_category in [
            RegistryModeCategory.EMERGENCY,
            RegistryModeCategory.BOOTSTRAP,
        ]

    def requires_high_security(self) -> bool:
        """Check if this mode requires enhanced security."""
        return self.is_production_like() or self.security_level in [
            "enhanced",
            "maximum",
        ]

    def get_default_feature_flags(self) -> dict[str, bool]:
        """Get default feature flags for this mode."""
        defaults = {
            RegistryModeCategory.PRODUCTION: {
                "debug_logging": False,
                "performance_monitoring": True,
                "circuit_breakers": True,
                "rate_limiting": True,
                "caching": True,
            },
            RegistryModeCategory.DEVELOPMENT: {
                "debug_logging": True,
                "performance_monitoring": False,
                "circuit_breakers": False,
                "rate_limiting": False,
                "caching": False,
            },
            RegistryModeCategory.TESTING: {
                "debug_logging": True,
                "performance_monitoring": True,
                "circuit_breakers": True,
                "rate_limiting": True,
                "caching": False,
            },
            RegistryModeCategory.EMERGENCY: {
                "debug_logging": True,
                "performance_monitoring": False,
                "circuit_breakers": False,
                "rate_limiting": False,
                "caching": False,
            },
        }
        base_defaults = defaults.get(self.mode_category, {})

        # Merge with custom feature flags
        result = base_defaults.copy()
        result.update(self.feature_flags)
        return result
