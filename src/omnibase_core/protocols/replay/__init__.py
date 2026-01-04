# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""
Replay infrastructure protocols.

This module provides protocol definitions for deterministic replay infrastructure:

- **ProtocolEffectRecorder**: Interface for effect recording and replay
- **ProtocolRNGService**: Interface for RNG injection in replay
- **ProtocolTimeService**: Interface for time injection in replay

Usage:
    >>> from omnibase_core.protocols.replay import (
    ...     ProtocolEffectRecorder,
    ...     ProtocolRNGService,
    ...     ProtocolTimeService,
    ... )

.. versionadded:: 0.4.0
    Added Replay Infrastructure (OMN-1116)
"""

from omnibase_core.protocols.replay.protocol_effect_recorder import (
    ProtocolEffectRecorder,
)
from omnibase_core.protocols.replay.protocol_rng_service import ProtocolRNGService
from omnibase_core.protocols.replay.protocol_time_service import ProtocolTimeService

__all__ = [
    "ProtocolEffectRecorder",
    "ProtocolRNGService",
    "ProtocolTimeService",
]
