"""
Custom settings model.
"""

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class ModelCustomSettings(BaseModel):
    """
    Custom settings with typed fields and validation.
    Replaces Dict[str, Any] for custom_settings fields.
    """

    # Settings categories
    general_settings: Dict[str, Any] = Field(
        default_factory=dict, description="General settings"
    )

    advanced_settings: Dict[str, Any] = Field(
        default_factory=dict, description="Advanced settings"
    )

    experimental_settings: Dict[str, Any] = Field(
        default_factory=dict, description="Experimental settings"
    )

    # Metadata
    version: str = Field("1.0", description="Settings version")
    last_modified: Optional[datetime] = Field(
        None, description="Last modification time"
    )

    # Validation
    validate_on_set: bool = Field(
        False, description="Validate settings on modification"
    )
    allow_unknown: bool = Field(True, description="Allow unknown settings")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for backward compatibility."""
        # Merge all settings for backward compatibility
        result = {}
        result.update(self.general_settings)
        result.update(self.advanced_settings)
        result.update(self.experimental_settings)
        return result

    @classmethod
    def from_dict(
        cls, data: Optional[Dict[str, Any]]
    ) -> Optional["ModelCustomSettings"]:
        """Create from dictionary for easy migration."""
        if data is None:
            return None

        # Check if already in new format
        if "general_settings" in data:
            return cls(**data)

        # Legacy format - all settings in flat dict
        return cls(general_settings=data.copy())

    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a setting value."""
        # Check all categories
        for settings in [
            self.general_settings,
            self.advanced_settings,
            self.experimental_settings,
        ]:
            if key in settings:
                return settings[key]
        return default

    def set_setting(self, key: str, value: Any, category: str = "general"):
        """Set a setting value."""
        if category == "advanced":
            self.advanced_settings[key] = value
        elif category == "experimental":
            self.experimental_settings[key] = value
        else:
            self.general_settings[key] = value

        self.last_modified = datetime.utcnow()
