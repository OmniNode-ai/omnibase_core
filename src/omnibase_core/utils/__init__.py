"""
Omnibase Core - Utilities

Utility functions and helpers for ONEX architecture.

Deprecated Aliases (OMN-1071)
=============================
This module provides deprecated aliases for classes renamed in v0.4.0.
The following aliases will be removed in a future version:

- ``ProtocolContractLoader`` -> use ``UtilContractLoader``

The ``__getattr__`` function provides lazy loading with deprecation warnings
to help users migrate to the new names. These utilities have heavy model
dependencies and are lazy-loaded to avoid circular imports during initial
module loading.
"""

from typing import Any

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
from .util_validators import convert_dict_to_frozen_pairs, convert_list_to_tuple

# Note: parse_datetime is lazy-loaded via __getattr__ to avoid circular imports
# when types/ imports from utils/ during initialization

# Note: The following utilities have heavy model dependencies and are NOT imported
# here to avoid circular dependencies during initial module loading. Import directly:
# - util_cli_result_formatter.UtilCliResultFormatter
# - util_safe_yaml_loader
# - util_field_converter
# - util_security.UtilSecurity
# - util_stability_calculator.calculate_stability, calculate_confidence
# - util_streaming_window.UtilStreamingWindow
# - util_contract_loader.UtilContractLoader (also available via lazy import below)

__all__ = [
    "UtilConflictResolver",
    "UtilContractLoader",
    "ProtocolContractLoader",  # DEPRECATED: Use UtilContractLoader instead
    "allow_any_type",
    "allow_dict_str_any",
    "convert_dict_to_frozen_pairs",
    "convert_list_to_tuple",
    "create_enum_normalizer",
    "deterministic_cache_key",
    "deterministic_error_code",
    "deterministic_hash",
    "deterministic_hash_int",
    "deterministic_jitter",
    "parse_datetime",
    "string_to_uuid",
]


# =============================================================================
# Lazy loading: Utilities with heavy model dependencies
# =============================================================================
def __getattr__(name: str) -> Any:
    """
    Lazy loading for utilities with heavy model dependencies.

    This avoids circular imports during module initialization while still
    allowing `from omnibase_core.utils import UtilContractLoader`.

    Lazy-loaded utilities:
    ----------------------
    - UtilConflictResolver: Has ModelOnexError dependency (circular via error_codes)
    - UtilContractLoader: Has heavy model dependencies
    - parse_datetime: Avoids circular imports with types/

    Deprecated Aliases (OMN-1071):
    ------------------------------
    All deprecated aliases emit DeprecationWarning when accessed:
    - ProtocolContractLoader -> UtilContractLoader
    """
    import warnings

    # -------------------------------------------------------------------------
    # parse_datetime: lazy-loaded to avoid circular imports with types/
    # -------------------------------------------------------------------------
    if name == "parse_datetime":
        from .util_datetime_parser import parse_datetime

        return parse_datetime

    # -------------------------------------------------------------------------
    # UtilConflictResolver: lazy-loaded to avoid circular imports
    # The resolver imports ModelOnexError which imports error_codes, which
    # would cause circular dependencies if loaded at module initialization.
    # -------------------------------------------------------------------------
    if name == "UtilConflictResolver":
        from .util_conflict_resolver import UtilConflictResolver

        return UtilConflictResolver

    # -------------------------------------------------------------------------
    # Consolidated imports: UtilContractLoader and its deprecated alias
    # ProtocolContractLoader is DEPRECATED - emits DeprecationWarning
    # -------------------------------------------------------------------------
    _contract_loader_names = {"UtilContractLoader", "ProtocolContractLoader"}
    if name in _contract_loader_names:
        # Emit deprecation warning only for deprecated alias
        if name == "ProtocolContractLoader":
            warnings.warn(
                "'ProtocolContractLoader' is deprecated, use 'UtilContractLoader' "
                "from 'omnibase_core.utils.util_contract_loader' instead",
                DeprecationWarning,
                stacklevel=2,
            )
        # Single import for all contract loader names
        from .util_contract_loader import UtilContractLoader

        return UtilContractLoader

    raise AttributeError(  # error-ok: required for __getattr__ protocol
        f"module {__name__!r} has no attribute {name!r}"
    )
