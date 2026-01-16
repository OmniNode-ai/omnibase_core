"""
Replay infrastructure models.

This module provides model definitions for deterministic replay infrastructure:

- **ModelAuditTrailEntry**: Individual entry in enforcement decision audit trail (OMN-1150)
- **ModelAuditTrailSummary**: Summary statistics for enforcement decisions (OMN-1150)
- **ModelConfigOverride**: Single configuration override with key path and value
- **ModelConfigOverrideSet**: Collection of configuration overrides for replay scenarios
- **ModelConfigOverrideFieldPreview**: Preview of a single field change from override
- **ModelConfigOverridePreview**: Complete preview of all changes from applying overrides
- **ModelConfigOverrideResult**: Result of applying configuration overrides
- **ModelConfigOverrideValidation**: Validation result for configuration overrides
- **ModelEffectRecord**: Captured effect intent and result pair for replay
- **ModelEnforcementDecision**: Enforcement decision outcome for replay safety (OMN-1150)
- **ModelReplayContext**: Determinism context bundling time, RNG seed, and effect records
- **ModelReplayInput**: Input configuration for replay execution
- **ModelExecutionCorpus**: Collection of execution manifests for replay testing
- **ModelCorpusStatistics**: Computed statistics for an execution corpus
- **ModelCorpusTimeRange**: Time range for corpus executions
- **ModelCorpusCaptureWindow**: Capture window for corpus collection

Comparison models (for baseline vs replay evaluation):
- **ModelExecutionComparison**: Complete comparison between baseline and replay execution
- **ModelInvariantComparisonSummary**: Aggregated statistics of invariant comparison
- **ModelOutputDiff**: Structured representation of output differences
- **ModelValueChange**: Single value change between baseline and replay

Related models re-exported for convenience:
- **ModelExecutionManifest**: Individual execution manifest (from models.manifest)

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
    Added Configuration Override Models (OMN-1205)

.. versionadded:: 0.4.0
    Added Execution Corpus Model (OMN-1202)

.. versionadded:: 0.6.3
    Added ModelEnforcementDecision (OMN-1150)
"""

from omnibase_core.mixins.mixin_truncation_validation import (
    MixinTruncationValidation,
)
from omnibase_core.models.manifest.model_execution_manifest import (
    ModelExecutionManifest,
)
from omnibase_core.models.replay.model_aggregate_metrics import ModelAggregateMetrics
from omnibase_core.models.replay.model_audit_trail_entry import ModelAuditTrailEntry
from omnibase_core.models.replay.model_audit_trail_summary import ModelAuditTrailSummary
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
from omnibase_core.models.replay.model_corpus_capture_window import (
    ModelCorpusCaptureWindow,
)
from omnibase_core.models.replay.model_corpus_replay_config import (
    ModelCorpusReplayConfig,
)
from omnibase_core.models.replay.model_corpus_replay_progress import (
    ModelCorpusReplayProgress,
)
from omnibase_core.models.replay.model_corpus_replay_result import (
    ModelCorpusReplayResult,
)
from omnibase_core.models.replay.model_corpus_statistics import ModelCorpusStatistics
from omnibase_core.models.replay.model_corpus_time_range import ModelCorpusTimeRange

# Execution detail view models
from omnibase_core.models.replay.model_diff_line import ModelDiffLine
from omnibase_core.models.replay.model_effect_record import ModelEffectRecord
from omnibase_core.models.replay.model_enforcement_decision import (
    EnforcementOutcome,
    ModelEnforcementDecision,
)

# Comparison models (consolidated from models.comparison)
from omnibase_core.models.replay.model_execution_comparison import (
    ModelExecutionComparison,
)
from omnibase_core.models.replay.model_execution_corpus import ModelExecutionCorpus
from omnibase_core.models.replay.model_execution_detail_view import (
    ModelExecutionDetailView,
)
from omnibase_core.models.replay.model_input_snapshot import ModelInputSnapshot
from omnibase_core.models.replay.model_invariant_comparison_summary import (
    ModelInvariantComparisonSummary,
)
from omnibase_core.models.replay.model_invariant_result_detail import (
    ModelInvariantResultDetail,
)
from omnibase_core.models.replay.model_output_diff import ModelOutputDiff
from omnibase_core.models.replay.model_output_snapshot import ModelOutputSnapshot
from omnibase_core.models.replay.model_phase_time import ModelPhaseTime
from omnibase_core.models.replay.model_replay_context import ModelReplayContext
from omnibase_core.models.replay.model_replay_input import ModelReplayInput
from omnibase_core.models.replay.model_side_by_side_comparison import (
    ModelSideBySideComparison,
)
from omnibase_core.models.replay.model_single_replay_result import (
    ModelSingleReplayResult,
)
from omnibase_core.models.replay.model_subset_filter import ModelSubsetFilter
from omnibase_core.models.replay.model_timing_breakdown import ModelTimingBreakdown
from omnibase_core.models.replay.model_value_change import ModelValueChange

# Rebuild ModelCorpusReplayConfig after ModelCorpusReplayProgress is defined
# to resolve the TYPE_CHECKING forward reference in progress_callback type hint
ModelCorpusReplayConfig.model_rebuild()

__all__ = [
    # Audit trail models (OMN-1150)
    "EnforcementOutcome",
    "ModelAuditTrailEntry",
    "ModelAuditTrailSummary",
    # Configuration override models
    "ModelConfigOverride",
    "ModelConfigOverrideFieldPreview",
    "ModelConfigOverridePreview",
    "ModelConfigOverrideResult",
    "ModelConfigOverrideSet",
    "ModelConfigOverrideValidation",
    # Corpus models
    "ModelCorpusCaptureWindow",
    "ModelCorpusStatistics",
    "ModelCorpusTimeRange",
    # Corpus replay models (OMN-1204)
    "ModelAggregateMetrics",
    "ModelCorpusReplayConfig",
    "ModelCorpusReplayProgress",
    "ModelCorpusReplayResult",
    "ModelSingleReplayResult",
    "ModelSubsetFilter",
    # Replay models
    "ModelEffectRecord",
    "ModelEnforcementDecision",
    "ModelExecutionCorpus",
    "ModelReplayContext",
    "ModelReplayInput",
    # Related models re-exported for convenience
    "ModelExecutionManifest",
    # Comparison models (consolidated from models.comparison)
    "ModelExecutionComparison",
    "ModelInvariantComparisonSummary",
    "ModelOutputDiff",
    "ModelPhaseTime",
    "ModelValueChange",
    # Execution detail view models
    "ModelDiffLine",
    "ModelExecutionDetailView",
    "ModelInputSnapshot",
    "ModelInvariantResultDetail",
    "MixinTruncationValidation",
    "ModelOutputSnapshot",
    "ModelSideBySideComparison",
    "ModelTimingBreakdown",
]
