"""
Environment Properties Model

Type-safe custom environment properties configuration with support
for various property types and metadata.
"""

from datetime import datetime

from pydantic import BaseModel, Field

from .model_typed_property import PropertyValue


class ModelEnvironmentProperties(BaseModel):
    """
    Type-safe custom environment properties.

    This model provides structured storage for custom environment properties
    with type safety and helper methods for property access.
    """

    properties: dict[str, PropertyValue] = Field(
        default_factory=dict,
        description="Custom property values",
    )

    property_metadata: dict[str, dict[str, str]] = Field(
        default_factory=dict,
        description="Metadata about each property (description, source, etc.)",
    )

    def get_string(self, key: str, default: str = "") -> str:
        """Get string property value."""
        value = self.properties.get(key, default)
        return str(value) if value is not None else default

    def get_int(self, key: str, default: int = 0) -> int:
        """Get integer property value."""
        value = self.properties.get(key, default)
        if isinstance(value, int | float) or (
            isinstance(value, str) and value.isdigit()
        ):
            return int(value)
        return default

    def get_float(self, key: str, default: float = 0.0) -> float:
        """Get float property value."""
        value = self.properties.get(key, default)
        if isinstance(value, int | float):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                return default
        return default

    def get_bool(self, key: str, default: bool = False) -> bool:
        """Get boolean property value."""
        value = self.properties.get(key, default)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ["true", "yes", "1", "on", "enabled"]
        if isinstance(value, int | float):
            return bool(value)
        return default

    def get_list(self, key: str, default: list[str] | None = None) -> list[str]:
        """Get list property value."""
        if default is None:
            default = []
        value = self.properties.get(key, default)
        if isinstance(value, list):
            return [str(item) for item in value]
        if isinstance(value, str):
            # Support comma-separated values
            return [item.strip() for item in value.split(",") if item.strip()]
        return default

    def get_datetime(
        self,
        key: str,
        default: datetime | None = None,
    ) -> datetime | None:
        """Get datetime property value."""
        value = self.properties.get(key, default)
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value)
            except ValueError:
                return default
        return default

    def set_property(
        self,
        key: str,
        value: PropertyValue,
        description: str | None = None,
        source: str | None = None,
    ) -> None:
        """Set a property with optional metadata."""
        self.properties[key] = value

        if description or source:
            metadata = self.property_metadata.get(key, {})
            if description:
                metadata["description"] = description
            if source:
                metadata["source"] = source
            self.property_metadata[key] = metadata

    def remove_property(self, key: str) -> None:
        """Remove a property and its metadata."""
        self.properties.pop(key, None)
        self.property_metadata.pop(key, None)

    def has_property(self, key: str) -> bool:
        """Check if a property exists."""
        return key in self.properties

    def get_property_description(self, key: str) -> str | None:
        """Get property description from metadata."""
        metadata = self.property_metadata.get(key, {})
        return metadata.get("description")

    def get_property_source(self, key: str) -> str | None:
        """Get property source from metadata."""
        metadata = self.property_metadata.get(key, {})
        return metadata.get("source")

    def get_all_properties(
        self,
    ) -> dict[str, PropertyValue]:
        """Get all properties."""
        return self.properties.copy()

    def get_properties_by_prefix(self, prefix: str) -> dict[str, PropertyValue]:
        """Get all properties with keys starting with a prefix."""
        return {
            key: value
            for key, value in self.properties.items()
            if key.startswith(prefix)
        }

    def merge_properties(self, other: "ModelEnvironmentProperties") -> None:
        """Merge properties from another instance."""
        self.properties.update(other.properties)
        self.property_metadata.update(other.property_metadata)

    def to_environment_variables(self, prefix: str = "ONEX_CUSTOM_") -> dict[str, str]:
        """Convert properties to environment variables with prefix."""
        env_vars = {}
        for key, value in self.properties.items():
            env_key = f"{prefix}{key.upper()}"
            if isinstance(value, list):
                env_vars[env_key] = ",".join(str(item) for item in value)
            elif isinstance(value, datetime):
                env_vars[env_key] = value.isoformat()
            else:
                env_vars[env_key] = str(value)
        return env_vars

    @classmethod
    def create_from_dict(
        cls,
        properties: dict[
            str,
            PropertyValue,
        ],
    ) -> "ModelEnvironmentProperties":
        """Create from a dictionary of properties."""
        return cls(properties=properties)

    @classmethod
    def create_empty(cls) -> "ModelEnvironmentProperties":
        """Create empty properties instance."""
        return cls()
