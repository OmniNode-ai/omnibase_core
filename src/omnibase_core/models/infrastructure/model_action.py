from __future__ import annotations

"""
Action model for reducer pattern.

Simple stub model for ONEX 2.0 minimal implementation.
Follows ONEX strong typing principles and one-model-per-file architecture.
"""


from pydantic import BaseModel


class ModelAction(BaseModel):
    """Stub action model for reducer pattern."""

    model_config = {
        "extra": "forbid",
        "use_enum_values": False,
        "validate_assignment": True,
    }


# Export for use
__all__ = ["ModelAction"]
