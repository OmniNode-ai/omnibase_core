# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""
Replay infrastructure models.

This module provides model definitions for deterministic replay infrastructure:

- **ModelConfigOverride**: Single configuration override with key path and value
- **ModelConfigOverrideSet**: Collection of configuration overrides for replay scenarios
- **ModelConfigOverrideFieldPreview**: Preview of a single field change from override
- **ModelConfigOverridePreview**: Complete preview of all changes from applying overrides
- **ModelConfigOverrideResult**: Result of applying configuration overrides
- **ModelConfigOverrideValidation**: Validation result for configuration overrides
- **ModelEffectRecord**: Captured effect intent and result pair for replay
- **ModelReplayContext**: Determinism context bundling time, RNG seed, and effect records
- **ModelReplayInput**: Input configuration for replay execution

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

.. versionadded:: 0.4.0
    Added Configuration Override Models (OMN-1205)
"""

from omnibase_core.models.replay.model_config_override import ModelConfigOverride
from omnibase_core.models.replay.model_config_override_field_preview import (
    ModelConfigOverrideFieldPreview,
)
from omnibase_core.models.replay.model_config_override_preview import (
    ModelConfigOverridePreview,
)
from omnibase_core.models.replay.model_config_override_result import (
    ModelConfigOverrideResult,
)
from omnibase_core.models.replay.model_config_override_set import ModelConfigOverrideSet
from omnibase_core.models.replay.model_config_override_validation import (
    ModelConfigOverrideValidation,
)
from omnibase_core.models.replay.model_effect_record import ModelEffectRecord
from omnibase_core.models.replay.model_replay_context import ModelReplayContext
from omnibase_core.models.replay.model_replay_input import ModelReplayInput

__all__ = [
    "ModelConfigOverride",
    "ModelConfigOverrideFieldPreview",
    "ModelConfigOverridePreview",
    "ModelConfigOverrideResult",
    "ModelConfigOverrideSet",
    "ModelConfigOverrideValidation",
    "ModelEffectRecord",
    "ModelReplayContext",
    "ModelReplayInput",
]
