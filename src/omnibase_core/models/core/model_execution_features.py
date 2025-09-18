"""
Execution Feature Models

Models for tracking feature flags and execution-specific features.
"""

from typing import Dict, List

from pydantic import BaseModel, Field


class ModelFeatureFlag(BaseModel):
    """Model for individual feature flags."""

    name: str = Field(..., description="Feature flag name")
    enabled: bool = Field(..., description="Whether the feature is enabled")
    description: str | None = Field(None, description="Feature flag description")
    category: str = Field(default="general", description="Feature category")
    source: str = Field(
        default="config", description="Source of the flag (config, env, api)"
    )


class ModelExecutionFeatures(BaseModel):
    """Model for execution feature flag management."""

    enabled_features: List[ModelFeatureFlag] = Field(
        default_factory=list, description="List of enabled features"
    )

    disabled_features: List[ModelFeatureFlag] = Field(
        default_factory=list, description="List of explicitly disabled features"
    )

    def add_enabled_feature(
        self,
        name: str,
        description: str | None = None,
        category: str = "general",
        source: str = "config",
    ) -> None:
        """Add an enabled feature flag."""
        feature = ModelFeatureFlag(
            name=name,
            enabled=True,
            description=description,
            category=category,
            source=source,
        )
        self.enabled_features.append(feature)

    def add_disabled_feature(
        self,
        name: str,
        description: str | None = None,
        category: str = "general",
        source: str = "config",
    ) -> None:
        """Add a disabled feature flag."""
        feature = ModelFeatureFlag(
            name=name,
            enabled=False,
            description=description,
            category=category,
            source=source,
        )
        self.disabled_features.append(feature)

    def is_feature_enabled(self, name: str) -> bool:
        """Check if a specific feature is enabled."""
        # Check enabled features first
        for feature in self.enabled_features:
            if feature.name == name:
                return True

        # Check if explicitly disabled
        for feature in self.disabled_features:
            if feature.name == name:
                return False

        # Default to False if not found
        return False

    def get_enabled_feature_names(self) -> List[str]:
        """Get list of enabled feature names."""
        return [feature.name for feature in self.enabled_features]

    def get_disabled_feature_names(self) -> List[str]:
        """Get list of disabled feature names."""
        return [feature.name for feature in self.disabled_features]

    def get_features_by_category(self, category: str) -> List[ModelFeatureFlag]:
        """Get all features (enabled and disabled) by category."""
        features = []
        for feature in self.enabled_features + self.disabled_features:
            if feature.category == category:
                features.append(feature)
        return features

    @classmethod
    def from_lists(
        cls, enabled_names: List[str], disabled_names: List[str]
    ) -> "ModelExecutionFeatures":
        """Create instance from simple string lists (legacy compatibility)."""
        instance = cls()

        for name in enabled_names:
            instance.add_enabled_feature(name)

        for name in disabled_names:
            instance.add_disabled_feature(name)

        return instance
