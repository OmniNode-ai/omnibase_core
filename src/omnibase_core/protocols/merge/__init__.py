# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Merge Protocols for ONEX Contract Merging.

Protocols for contract patch merging, enabling the
combination of user-authored patches with base profiles to produce
expanded (complete) contracts.

Protocols:
    ProtocolMergeEngine: Interface for merging contract patches with base
        profiles. The merge follows deterministic rules:
        - Scalars: Patch overrides base (if not None)
        - Dicts: Recursive merge (patch keys override/add to base)
        - Lists: Explicit __add/__remove operations from patch

Usage:
    .. code-block:: python

        from omnibase_core.protocols.merge import ProtocolMergeEngine
        from omnibase_core.models.contracts import ModelContractPatch

        def expand_contract(
            engine: ProtocolMergeEngine,
            patch: ModelContractPatch,
        ) -> ModelHandlerContract:
            '''Expand a contract patch to a full contract.'''
            return engine.merge(patch)

See Also:
    - OMN-1127: Typed Contract Merge Engine
    - ModelContractPatch: User-authored contract patches
    - ModelHandlerContract: Expanded contract output
    - ModelMergeConflict: Conflict detection results

.. versionadded:: 0.4.1
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.protocols.merge.protocol_merge_engine import (
        ProtocolMergeEngine,
    )

__all__ = [
    "ProtocolMergeEngine",
]


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "ProtocolMergeEngine": (
        "omnibase_core.protocols.merge.protocol_merge_engine",
        "ProtocolMergeEngine",
    ),
}


def __getattr__(name: str) -> object:
    target = _LAZY_IMPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = importlib.import_module(target[0])
    value = module if target[1] is None else getattr(module, target[1])
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted({*globals(), *_LAZY_IMPORTS})
