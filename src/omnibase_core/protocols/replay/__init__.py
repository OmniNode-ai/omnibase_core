# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Replay infrastructure protocols.

Protocol definitions for deterministic replay infrastructure:

- **ProtocolAuditTrail**: Interface for enforcement decision audit trail
- **ProtocolEffectRecorder**: Interface for effect recording and replay
- **ProtocolReplaySafetyEnforcer**: Interface for replay safety enforcement
- **ProtocolRNGService**: Interface for RNG injection in replay
- **ProtocolTimeService**: Interface for time injection in replay
- **ProtocolUUIDService**: Interface for UUID injection in replay

Usage:
    >>> from omnibase_core.protocols.replay import (
    ...     ProtocolAuditTrail,
    ...     ProtocolEffectRecorder,
    ...     ProtocolReplaySafetyEnforcer,
    ...     ProtocolRNGService,
    ...     ProtocolTimeService,
    ...     ProtocolUUIDService,
    ... )

.. versionadded:: 0.4.0
    Added Replay Infrastructure (OMN-1116)

.. versionadded:: 0.6.3
    Added ProtocolUUIDService (OMN-1150)
    Added ProtocolAuditTrail (OMN-1150)
    Added ProtocolReplaySafetyEnforcer (OMN-1150)
"""

from __future__ import annotations

import importlib.util
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.protocols.replay.protocol_audit_trail import ProtocolAuditTrail
    from omnibase_core.protocols.replay.protocol_effect_recorder import (
        ProtocolEffectRecorder,
    )
    from omnibase_core.protocols.replay.protocol_replay_safety_enforcer import (
        ProtocolReplaySafetyEnforcer,
    )
    from omnibase_core.protocols.replay.protocol_rng_service import ProtocolRNGService
    from omnibase_core.protocols.replay.protocol_time_service import ProtocolTimeService
    from omnibase_core.protocols.replay.protocol_uuid_service import ProtocolUUIDService

__all__ = [
    "ProtocolAuditTrail",
    "ProtocolEffectRecorder",
    "ProtocolReplaySafetyEnforcer",
    "ProtocolRNGService",
    "ProtocolTimeService",
    "ProtocolUUIDService",
]


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "ProtocolAuditTrail": (
        "omnibase_core.protocols.replay.protocol_audit_trail",
        "ProtocolAuditTrail",
    ),
    "ProtocolEffectRecorder": (
        "omnibase_core.protocols.replay.protocol_effect_recorder",
        "ProtocolEffectRecorder",
    ),
    "ProtocolReplaySafetyEnforcer": (
        "omnibase_core.protocols.replay.protocol_replay_safety_enforcer",
        "ProtocolReplaySafetyEnforcer",
    ),
    "ProtocolRNGService": (
        "omnibase_core.protocols.replay.protocol_rng_service",
        "ProtocolRNGService",
    ),
    "ProtocolTimeService": (
        "omnibase_core.protocols.replay.protocol_time_service",
        "ProtocolTimeService",
    ),
    "ProtocolUUIDService": (
        "omnibase_core.protocols.replay.protocol_uuid_service",
        "ProtocolUUIDService",
    ),
}


def __getattr__(name: str) -> object:
    target = _LAZY_IMPORTS.get(name)
    if target is None:
        # A submodule that the old eager __init__ loaded as a side effect
        # stays reachable as ``package.submodule``: import it on first access.
        if (
            name.isidentifier()
            and not name.startswith("__")
            and importlib.util.find_spec(f"{__name__}.{name}") is not None
        ):
            return importlib.import_module(f"{__name__}.{name}")
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = importlib.import_module(target[0])
    value = module if target[1] is None else getattr(module, target[1])
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted({*globals(), *_LAZY_IMPORTS})
