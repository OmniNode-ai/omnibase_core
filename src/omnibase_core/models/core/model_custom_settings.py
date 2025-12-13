"""
Custom settings model.
"""

from datetime import UTC, datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.types.type_serializable_value import (
    SerializableValue,
    SerializedDict,
)


class ModelCustomSettings(BaseModel):
    """
    Custom settings with typed fields and validation.
    Replaces Dict[str, Any] for custom_settings fields.
    """

    # Settings categories
    general_settings: SerializedDict = Field(
        default_factory=dict,
        description="General settings",
    )

    advanced_settings: SerializedDict = Field(
        default_factory=dict,
        description="Advanced settings",
    )

    experimental_settings: SerializedDict = Field(
        default_factory=dict,
        description="Experimental settings",
    )

    # Metadata
    version: ModelSemVer | None = Field(default=None, description="Settings version")

    @field_validator("version", mode="before")
    @classmethod
    def parse_version(cls, v: object) -> object:
        """Convert string versions to ModelSemVer."""
        if v is None:
            return ModelSemVer(major=1, minor=0, patch=0)
        if isinstance(v, str):
            from omnibase_core.utils.util_semver_parser import parse_semver_from_string

            return parse_semver_from_string(v)
        return v

    last_modified: datetime | None = Field(
        default=None,
        description="Last modification time",
    )

    # Validation
    validate_on_set: bool = Field(
        default=False,
        description="Validate settings on modification",
    )
    allow_unknown: bool = Field(default=True, description="Allow unknown settings")

    def to_dict(self) -> SerializedDict:
        """Convert to dictionary for current standards."""
        # Custom flattening logic for current standards
        result: SerializedDict = {}
        result.update(self.general_settings)
        result.update(self.advanced_settings)
        result.update(self.experimental_settings)
        return result

    @classmethod
    def from_dict(
        cls,
        data: SerializedDict | None,
    ) -> Optional["ModelCustomSettings"]:
        """Create from dictionary for easy migration."""
        if data is None:
            return None

        # Check if already in new format
        if "general_settings" in data:
            return cls(**data)

        # Legacy format - all settings in flat dict
        return cls(general_settings=data.copy())

    def get_setting(
        self, key: str, default: SerializableValue = None
    ) -> SerializableValue:
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

    def set_setting(
        self, key: str, value: SerializableValue, category: str = "general"
    ) -> None:
        """Set a setting value."""
        if category == "advanced":
            self.advanced_settings[key] = value
        elif category == "experimental":
            self.experimental_settings[key] = value
        else:
            self.general_settings[key] = value

        self.last_modified = datetime.now(UTC)
