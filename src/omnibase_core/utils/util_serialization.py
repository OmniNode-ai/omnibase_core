"""
Serialization utilities wrapper.

Re-exports serialization functions from safe_yaml_loader.
"""

from omnibase_core.utils.safe_yaml_loader import (
    serialize_data_to_yaml,
    serialize_pydantic_model_to_yaml,
)

__all__ = [
    "serialize_data_to_yaml",
    "serialize_pydantic_model_to_yaml",
]
