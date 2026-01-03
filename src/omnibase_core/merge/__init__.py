"""
Merge module for contract patching system.

This module provides the core merge semantics for combining base contracts
with patch overlays, enabling environment-specific customizations without
duplicating entire contract definitions.

Components:
    - **ContractMergeEngine**: Main engine that combines patches with base profiles
    - **merge_rules**: Core merge functions (scalar, dict, list operations)

.. versionadded:: 0.4.0

Merge Semantics:
    - **Scalars**: Patch value overrides base value (if patch is not None)
    - **Dicts**: Recursive merge (patch keys override/add to base keys)
    - **Lists**: Replace by default, or use explicit add/remove operations

Example:
    Basic dict merge::

        >>> from omnibase_core.merge import merge_dict, merge_scalar
        >>> base = {"host": "localhost", "port": 8080}
        >>> patch = {"port": 9090}
        >>> merge_dict(base, patch)
        {'host': 'localhost', 'port': 9090}

    Using ContractMergeEngine::

        >>> from omnibase_core.merge import ContractMergeEngine
        >>> engine = ContractMergeEngine(profile_factory)
        >>> contract = engine.merge(patch)

See Also:
    - OMN-1127: Typed Contract Merge Engine
    - OMN-1126: ModelContractPatch & Patch Validation
"""

from __future__ import annotations

from omnibase_core.merge.contract_merge_engine import ContractMergeEngine
from omnibase_core.merge.merge_rules import (
    apply_list_add,
    apply_list_operations,
    apply_list_remove,
    merge_dict,
    merge_list_replace,
    merge_scalar,
)

__all__ = [
    # Contract Merge Engine (OMN-1127)
    "ContractMergeEngine",
    # Merge rules
    "apply_list_add",
    "apply_list_operations",
    "apply_list_remove",
    "merge_dict",
    "merge_list_replace",
    "merge_scalar",
]
