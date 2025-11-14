"""
Omnibase Core - Utilities

Utility functions and helpers for ONEX architecture.
"""

from .util_decorators import allow_any_type, allow_dict_str_any

# Note: util_safe_yaml_loader and util_field_converter are available but not imported
# here to avoid circular dependencies during initial module loading
__all__ = [
    "allow_any_type",
    "allow_dict_str_any",
]
