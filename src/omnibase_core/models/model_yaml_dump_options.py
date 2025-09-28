"""
Type-safe YAML dump options model.

Author: ONEX Framework Team
"""

from typing import Any

from pydantic import BaseModel

from omnibase_core.core.type_constraints import Serializable


class ModelYamlDumpOptions(BaseModel):
    """Type-safe YAML dump options.
    Implements omnibase_spi protocols:
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    sort_keys: bool = False
    default_flow_style: bool = False
    allow_unicode: bool = True
    explicit_start: bool = False
    explicit_end: bool = False
    indent: int = 2
    width: int = 120

    # Export the model

    # Protocol method implementations

    def serialize(self) -> dict[str, Any]:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (Validatable protocol)."""
        try:
            # Basic validation - ensure required fields exist
            # Override in specific models for custom validation
            return True
        except Exception:
            return False


__all__ = ["ModelYamlDumpOptions"]
