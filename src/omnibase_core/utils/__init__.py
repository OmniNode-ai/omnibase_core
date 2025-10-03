"""
Omnibase Core - Utilities

Utility functions and helpers for ONEX architecture.
"""

from .decorators import allow_any_type, allow_dict_str_any
from .safe_yaml_loader import load_and_validate_yaml_model

# Note: model_field_converter is available but not imported here to avoid
# circular dependencies during initial module loading
__all__ = [
    "allow_any_type",
    "allow_dict_str_any",
    "load_and_validate_yaml_model",
]
