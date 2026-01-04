# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""
Replay infrastructure models.

This module provides model definitions for deterministic replay infrastructure:

- **ModelEffectRecord**: Captured effect intent and result pair for replay
- **ModelReplayContext**: Determinism context bundling time, RNG seed, and effect records

Usage:
    >>> from omnibase_core.models.replay import ModelEffectRecord, ModelReplayContext
    >>> from omnibase_core.enums.replay import EnumReplayMode
    >>> from datetime import datetime, timezone
    >>>
    >>> # Create effect record
    >>> record = ModelEffectRecord(
    ...     effect_id="http.get",
    ...     intent={"url": "https://api.example.com"},
    ...     result={"status_code": 200},
    ...     captured_at=datetime.now(timezone.utc),
    ...     sequence_index=0,
    ... )
    >>>
    >>> # Create replay context
    >>> ctx = ModelReplayContext(
    ...     mode=EnumReplayMode.RECORDING,
    ...     rng_seed=42,
    ... )

.. versionadded:: 0.4.0
    Added Replay Infrastructure (OMN-1116)
"""

from omnibase_core.models.replay.model_effect_record import ModelEffectRecord
from omnibase_core.models.replay.model_replay_context import ModelReplayContext

__all__ = [
    "ModelEffectRecord",
    "ModelReplayContext",
]
