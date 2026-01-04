# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""
Replay infrastructure models.

This module provides model definitions for deterministic replay infrastructure:

- **ModelEffectRecord**: Captured effect intent and result pair for replay
- **ModelReplayContext**: Determinism context bundling time, RNG seed, and effect records
- **ModelExecutionCorpus**: Collection of execution manifests for replay testing
- **ModelCorpusStatistics**: Computed statistics for an execution corpus
- **ModelCorpusTimeRange**: Time range for corpus executions
- **ModelCorpusCaptureWindow**: Capture window for corpus collection

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

    >>> from omnibase_core.models.replay import ModelExecutionCorpus
    >>>
    >>> # Create execution corpus
    >>> corpus = ModelExecutionCorpus(
    ...     name="production-sample",
    ...     version="1.0.0",
    ...     source="production",
    ... )

.. versionadded:: 0.4.0
    Added Replay Infrastructure (OMN-1116)

.. versionadded:: 0.4.0
    Added Execution Corpus Model (OMN-1202)
"""

from omnibase_core.models.replay.model_corpus_capture_window import (
    ModelCorpusCaptureWindow,
)
from omnibase_core.models.replay.model_corpus_statistics import ModelCorpusStatistics
from omnibase_core.models.replay.model_corpus_time_range import ModelCorpusTimeRange
from omnibase_core.models.replay.model_effect_record import ModelEffectRecord
from omnibase_core.models.replay.model_execution_corpus import ModelExecutionCorpus
from omnibase_core.models.replay.model_replay_context import ModelReplayContext

__all__ = [
    "ModelCorpusCaptureWindow",
    "ModelCorpusStatistics",
    "ModelCorpusTimeRange",
    "ModelEffectRecord",
    "ModelExecutionCorpus",
    "ModelReplayContext",
]
