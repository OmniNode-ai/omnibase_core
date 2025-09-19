#!/usr/bin/env python3
"""File with backward compatibility anti-patterns."""

from pydantic import BaseModel


class ModelUserProfile(BaseModel):
    """User profile model."""

    user_id: str
    name: str

    def to_dict(self) -> dict:
        """Convert to dictionary for backward compatibility."""
        return self.model_dump()

    def get_legacy_format(self) -> dict:
        """Get data in legacy format for backward compatibility."""
        return {"id": self.user_id, "full_name": self.name}


# Accept simple Protocol* names for backward compatibility
def validate_protocol_name(name: str) -> bool:
    if name.startswith("Protocol"):
        return True
    return False


class ModelConfig:
    """Model configuration."""

    extra = "allow"  # Allow extra fields for compatibility
    validate_assignment = True


def process_legacy_data(data: dict) -> dict:
    """Process data maintaining compatibility with legacy systems."""
    # Legacy support for old field names
    if "old_field" in data:
        data["new_field"] = data.pop("old_field")
    return data
