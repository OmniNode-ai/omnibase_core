"""
Type-safe YAML dump options model.

Author: ONEX Framework Team
"""

from pydantic import BaseModel


class ModelYamlDumpOptions(BaseModel):
    """Type-safe YAML dump options."""

    sort_keys: bool = False
    default_flow_style: bool = False
    allow_unicode: bool = True
    explicit_start: bool = False
    explicit_end: bool = False
    indent: int = 2
    width: int = 120

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }


# Export the model
__all__ = ["ModelYamlDumpOptions"]
