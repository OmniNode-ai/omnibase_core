"""
Merge Protocols for ONEX Contract Merging.

This module provides protocols for contract patch merging, enabling the
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

from omnibase_core.protocols.merge.protocol_merge_engine import (
    ProtocolMergeEngine,
)

__all__ = [
    "ProtocolMergeEngine",
]
