"""
Feature Flags Model

Type-safe feature flag configuration model for enabling/disabling
features across different environments and contexts.
"""

from pydantic import BaseModel, Field

from .model_feature_flag_metadata import ModelFeatureFlagMetadata
from .model_feature_flag_summary import ModelFeatureFlagSummary

# Re-export from split modules
__all__ = ["ModelFeatureFlags", "ModelFeatureFlagMetadata", "ModelFeatureFlagSummary"]


class ModelFeatureFlags(BaseModel):
    """
    Type-safe feature flag configuration model.

    This model provides a structured way to manage feature flags
    across different environments and contexts.
    """

    flags: dict[str, bool] = Field(
        default_factory=dict,
        description="Feature flag states (name -> enabled)",
    )

    flag_metadata: dict[str, ModelFeatureFlagMetadata] = Field(
        default_factory=dict,
        description="Metadata for each feature flag",
    )

    default_enabled: bool = Field(
        default=False,
        description="Default state for undefined flags",
    )

    def is_enabled(self, flag: str, default: bool | None = None) -> bool:
        """
        Check if a feature flag is enabled.

        Args:
            flag: Feature flag name
            default: Default value if flag not found (uses default_enabled if None)

        Returns:
            True if flag is enabled, False otherwise
        """
        if flag in self.flags:
            return self.flags[flag]
        return default if default is not None else self.default_enabled

    def enable(
        self, flag: str, metadata: ModelFeatureFlagMetadata | None = None
    ) -> None:
        """Enable a feature flag with optional metadata."""
        self.flags[flag] = True
        if metadata:
            self.flag_metadata[flag] = metadata

    def disable(
        self, flag: str, metadata: ModelFeatureFlagMetadata | None = None
    ) -> None:
        """Disable a feature flag with optional metadata."""
        self.flags[flag] = False
        if metadata:
            self.flag_metadata[flag] = metadata

    def toggle(self, flag: str) -> bool:
        """Toggle a feature flag and return the new state."""
        current_state = self.is_enabled(flag)
        new_state = not current_state
        self.flags[flag] = new_state
        return new_state

    def set_flag(
        self,
        flag: str,
        enabled: bool,
        metadata: ModelFeatureFlagMetadata | None = None,
    ) -> None:
        """Set a feature flag to a specific state."""
        self.flags[flag] = enabled
        if metadata:
            self.flag_metadata[flag] = metadata

    def remove_flag(self, flag: str) -> bool:
        """Remove a feature flag and return whether it existed."""
        existed = flag in self.flags
        self.flags.pop(flag, None)
        self.flag_metadata.pop(flag, None)
        return existed

    def get_enabled_flags(self) -> list[str]:
        """Get list[Any]of all enabled feature flags."""
        return [flag for flag, enabled in self.flags.items() if enabled]

    def get_disabled_flags(self) -> list[str]:
        """Get list[Any]of all disabled feature flags."""
        return [flag for flag, enabled in self.flags.items() if not enabled]

    def get_all_flags(self) -> list[str]:
        """Get list[Any]of all defined feature flags."""
        return list(self.flags.keys())

    def get_flag_metadata(self, flag: str) -> ModelFeatureFlagMetadata | None:
        """Get metadata for a specific flag."""
        return self.flag_metadata.get(flag)

    def set_flag_metadata(self, flag: str, metadata: ModelFeatureFlagMetadata) -> None:
        """Set metadata for a specific flag."""
        self.flag_metadata[flag] = metadata

    def has_flag(self, flag: str) -> bool:
        """Check if a flag is defined (regardless of state)."""
        return flag in self.flags

    def get_flag_count(self) -> int:
        """Get total number of defined flags."""
        return len(self.flags)

    def get_enabled_count(self) -> int:
        """Get number of enabled flags."""
        return len(self.get_enabled_flags())

    def get_disabled_count(self) -> int:
        """Get number of disabled flags."""
        return len(self.get_disabled_flags())

    def clear_all_flags(self) -> None:
        """Clear all feature flags and metadata."""
        self.flags.clear()
        self.flag_metadata.clear()

    def merge_flags(self, other: "ModelFeatureFlags", override: bool = True) -> None:
        """
        Merge flags from another ModelFeatureFlags instance.

        Args:
            other: Other feature flags to merge
            override: Whether to override existing flags (default: True)
        """
        for flag, enabled in other.flags.items():
            if override or flag not in self.flags:
                self.flags[flag] = enabled

        for flag, metadata in other.flag_metadata.items():
            if override or flag not in self.flag_metadata:
                self.flag_metadata[flag] = metadata

    def to_environment_dict(self, prefix: str = "ONEX_FEATURE_") -> dict[str, str]:
        """Convert to environment variables dictionary."""
        env_dict = {}
        for flag, enabled in self.flags.items():
            env_var_name = f"{prefix}{flag.upper()}"
            env_dict[env_var_name] = str(enabled).lower()
        return env_dict

    def get_summary(self) -> ModelFeatureFlagSummary:
        """Get summary of feature flag state."""
        return ModelFeatureFlagSummary(
            total_flags=self.get_flag_count(),
            enabled_flags=self.get_enabled_count(),
            disabled_flags=self.get_disabled_count(),
            default_enabled=self.default_enabled,
            enabled_flag_names=self.get_enabled_flags(),
            disabled_flag_names=self.get_disabled_flags(),
        )

    @classmethod
    def create_development(cls) -> "ModelFeatureFlags":
        """Create feature flags for development environment."""
        flags = cls(default_enabled=False)
        flags.enable("debug_mode")
        flags.enable("verbose_logging")
        flags.enable("hot_reload")
        flags.enable("development_tools")
        flags.disable("rate_limiting")
        flags.disable("caching")
        return flags

    @classmethod
    def create_staging(cls) -> "ModelFeatureFlags":
        """Create feature flags for staging environment."""
        flags = cls(default_enabled=False)
        flags.enable("monitoring")
        flags.enable("rate_limiting")
        flags.enable("caching")
        flags.disable("debug_mode")
        flags.disable("development_tools")
        return flags

    @classmethod
    def create_production(cls) -> "ModelFeatureFlags":
        """Create feature flags for production environment."""
        flags = cls(default_enabled=False)
        flags.enable("monitoring")
        flags.enable("rate_limiting")
        flags.enable("caching")
        flags.enable("security_hardening")
        flags.enable("performance_optimization")
        flags.disable("debug_mode")
        flags.disable("verbose_logging")
        flags.disable("development_tools")
        return flags

    @classmethod
    def from_environment_dict(
        cls,
        env_dict: dict[str, str],
        prefix: str = "ONEX_FEATURE_",
    ) -> "ModelFeatureFlags":
        """Create feature flags from environment variables."""
        flags = cls()
        for key, value in env_dict.items():
            if key.startswith(prefix):
                flag_name = key[len(prefix) :].lower()
                enabled = value.lower() in ("true", "1", "yes", "on")
                flags.set_flag(flag_name, enabled)
        return flags
