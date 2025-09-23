"""
Node Feature Flags Model.

Feature toggle configuration for nodes.
Part of the ModelNodeConfiguration restructuring.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from .model_types_node_feature_summary import NodeFeatureSummaryType


class ModelNodeFeatureFlags(BaseModel):
    """
    Node feature toggle settings.

    Contains feature enablement flags:
    - Caching and monitoring
    - Tracing and debugging features
    """

    # Feature toggles (3 fields)
    enable_caching: bool = Field(default=False, description="Enable result caching")
    enable_monitoring: bool = Field(default=True, description="Enable monitoring")
    enable_tracing: bool = Field(default=False, description="Enable detailed tracing")

    def get_enabled_features(self) -> list[str]:
        """Get list of enabled features."""
        features = []
        if self.enable_caching:
            features.append("caching")
        if self.enable_monitoring:
            features.append("monitoring")
        if self.enable_tracing:
            features.append("tracing")
        return features

    def get_disabled_features(self) -> list[str]:
        """Get list of disabled features."""
        features = []
        if not self.enable_caching:
            features.append("caching")
        if not self.enable_monitoring:
            features.append("monitoring")
        if not self.enable_tracing:
            features.append("tracing")
        return features

    def get_feature_summary(self) -> NodeFeatureSummaryType:
        """Get feature flags summary as string values for type safety."""
        enabled = self.get_enabled_features()
        return {
            "enable_caching": str(self.enable_caching),
            "enable_monitoring": str(self.enable_monitoring),
            "enable_tracing": str(self.enable_tracing),
            "enabled_features": ",".join(enabled) if enabled else "none",
            "enabled_count": str(len(enabled)),
            "is_monitoring_enabled": str(self.enable_monitoring),
            "is_debug_mode": str(self.enable_tracing),
        }

    def is_production_ready(self) -> bool:
        """Check if configuration is production-ready."""
        return self.enable_monitoring and not self.enable_tracing

    def is_debug_mode(self) -> bool:
        """Check if debug mode is enabled."""
        return self.enable_tracing

    def enable_all_features(self) -> None:
        """Enable all available features."""
        self.enable_caching = True
        self.enable_monitoring = True
        self.enable_tracing = True

    def disable_all_features(self) -> None:
        """Disable all features."""
        self.enable_caching = False
        self.enable_monitoring = False
        self.enable_tracing = False

    @classmethod
    def create_production(cls) -> ModelNodeFeatureFlags:
        """Create production-ready feature configuration."""
        return cls(
            enable_caching=True,
            enable_monitoring=True,
            enable_tracing=False,
        )

    @classmethod
    def create_development(cls) -> ModelNodeFeatureFlags:
        """Create development-friendly feature configuration."""
        return cls(
            enable_caching=False,
            enable_monitoring=True,
            enable_tracing=True,
        )


# Export for use
__all__ = ["ModelNodeFeatureFlags"]
