"""
Legacy node implementations.

.. deprecated:: 0.4.0
    These legacy implementations are maintained for backward compatibility.
    New code should use the contract-driven nodes from :mod:`omnibase_core.nodes`.

This module exports legacy code-driven node implementations that were used
prior to the contract-driven architecture introduced in v0.4.0.

Exports:
    NodeEffectLegacy: Legacy code-driven effect node with inline handlers.
"""

import warnings

from omnibase_core.nodes.legacy.node_effect_legacy import NodeEffectLegacy

__all__ = ["NodeEffectLegacy"]

# Emit deprecation warning on import
warnings.warn(
    "omnibase_core.nodes.legacy is deprecated. Use contract-driven nodes from "
    "omnibase_core.nodes instead. See docs/guides/MIGRATING_TO_DECLARATIVE_NODES.md",
    DeprecationWarning,
    stacklevel=2,
)
