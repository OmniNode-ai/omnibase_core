"""
Replay infrastructure protocols.

This module provides protocol definitions for deterministic replay infrastructure:

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
