"""
Omnibase Core - Utilities

Utility functions and helpers for ONEX architecture.
"""

from .util_conflict_resolver import UtilConflictResolver
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

# Note: The following utilities have heavy model dependencies and are NOT imported
# here to avoid circular dependencies during initial module loading. Import directly:
# - util_cli_result_formatter.UtilCliResultFormatter
# - util_safe_yaml_loader
# - util_field_converter
# - util_security.UtilSecurity
# - util_streaming_window.UtilStreamingWindow
# - util_contract_loader.UtilContractLoader (also available via lazy import below)

__all__ = [
    "UtilConflictResolver",
    "UtilContractLoader",
    "ProtocolContractLoader",  # DEPRECATED: Use UtilContractLoader
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


def __getattr__(name: str) -> type:
    """
    Lazy loading for utilities with heavy model dependencies.

    This avoids circular imports during module initialization while still
    allowing `from omnibase_core.utils import UtilContractLoader`.
    """
    if name == "UtilContractLoader":
        from .util_contract_loader import UtilContractLoader

        return UtilContractLoader

    if name == "ProtocolContractLoader":
        # DEPRECATED: Use UtilContractLoader instead.
        # This alias exists for backwards compatibility with code that used
        # the old name prior to PR #261 rename.
        from .util_contract_loader import UtilContractLoader

        return UtilContractLoader

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
