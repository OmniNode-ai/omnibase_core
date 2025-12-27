"""
Omnibase Core - Utilities

Utility functions and helpers for ONEX architecture.
"""

from .util_decorators import allow_any_type, allow_dict_str_any
from .util_enum_normalizer import create_enum_normalizer
from .util_hash import (
    deterministic_cache_key,
    deterministic_error_code,
    deterministic_hash,
    deterministic_hash_int,
    deterministic_jitter,
    string_to_uuid,
)

# Note: util_safe_yaml_loader and util_field_converter are available but not imported
# here to avoid circular dependencies during initial module loading
__all__ = [
    "allow_any_type",
    "allow_dict_str_any",
    "create_enum_normalizer",
    "deterministic_cache_key",
    "deterministic_error_code",
    "deterministic_hash",
    "deterministic_hash_int",
    "deterministic_jitter",
    "string_to_uuid",
]
