"""
Omnibase Core - Utilities

Utility functions and helpers for ONEX architecture.
"""

from .decorators import allow_any_type, allow_dict_str_any

# Note: safe_yaml_loader and model_field_converter are available but not imported
# here to avoid circular dependencies during initial module loading
__all__ = [
    "allow_any_type",
    "allow_dict_str_any",
]
