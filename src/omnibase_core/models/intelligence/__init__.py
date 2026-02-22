# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Intelligence models for ONEX integration.

This module provides domain models for AI/ML intelligence operations,
including intent classification and pattern extraction. These models are
cross-repo domain nouns designed for sharing between omnibase_core,
omniintelligence, and other ONEX repositories.

Models:
    ModelIntentClassificationInput: Input for intent classification operations.
    ModelIntentClassificationOutput: Output from intent classification operations.
    ModelPatternError: Error encountered during pattern extraction.
    ModelPatternExtractionInput: Input for pattern extraction operations.
    ModelPatternExtractionOutput: Output from pattern extraction operations.
    ModelPatternRecord: Individual extracted pattern record.
    ModelPatternWarning: Warning encountered during pattern extraction.
    ModelToolExecution: Structured tool execution data for pattern extraction.
    ModelToolExecutionContent: Content captured from Claude Code tool execution.

Intent Intelligence Framework models (OMN-2486):
    ModelTypedIntent: Classified, structured intent object.
    ModelIntentDriftSignal: Drift detection output.
    ModelIntentCostForecast: Cost/latency prediction before execution.
    ModelIntentGraphNode: Intent graph vertex.
    ModelIntentTransition: Intent graph edge with statistics.
    ModelIntentToCommitBinding: Commit-level causal link.
    ModelUserIntentProfile: Per-user intent tendency patterns.
    ModelIntentRollbackTrigger: Signal when to revert based on outcome.

TypedDicts (from omnibase_core.types):
    TypedDictConversationMessage: TypedDict for conversation message structure.
    TypedDictIntentContext: TypedDict for intent classification context.
    TypedDictSecondaryIntent: TypedDict for secondary intent entries.
    TypedDictIntentMetadata: TypedDict for classification metadata.

Enums (re-exported for convenience):
    EnumPatternKind: Classification of pattern types (architectural, behavioral, etc.).

"""

from omnibase_core.enums import EnumPatternKind
from omnibase_core.models.intelligence.intent.model_intent_cost_forecast import (
    ModelIntentCostForecast,
)
from omnibase_core.models.intelligence.intent.model_intent_drift_signal import (
    ModelIntentDriftSignal,
)
from omnibase_core.models.intelligence.intent.model_intent_graph_node import (
    ModelIntentGraphNode,
)
from omnibase_core.models.intelligence.intent.model_intent_rollback_trigger import (
    ModelIntentRollbackTrigger,
)
from omnibase_core.models.intelligence.intent.model_intent_to_commit_binding import (
    ModelIntentToCommitBinding,
)
from omnibase_core.models.intelligence.intent.model_intent_transition import (
    ModelIntentTransition,
)
from omnibase_core.models.intelligence.intent.model_typed_intent import (
    ModelTypedIntent,
)
from omnibase_core.models.intelligence.intent.model_user_intent_profile import (
    ModelUserIntentProfile,
)
from omnibase_core.models.intelligence.model_intent_classification_input import (
    ModelIntentClassificationInput,
    TypedDictConversationMessage,
    TypedDictIntentContext,
)
from omnibase_core.models.intelligence.model_intent_classification_output import (
    ModelIntentClassificationOutput,
    TypedDictIntentMetadata,
    TypedDictSecondaryIntent,
)
from omnibase_core.models.intelligence.model_intent_query_result import (
    ModelIntentQueryResult,
)
from omnibase_core.models.intelligence.model_intent_record import ModelIntentRecord
from omnibase_core.models.intelligence.model_intent_storage_result import (
    ModelIntentStorageResult,
)
from omnibase_core.models.intelligence.model_pattern_error import ModelPatternError
from omnibase_core.models.intelligence.model_pattern_extraction_input import (
    ModelPatternExtractionInput,
)
from omnibase_core.models.intelligence.model_pattern_extraction_output import (
    ModelPatternExtractionOutput,
)
from omnibase_core.models.intelligence.model_pattern_record import ModelPatternRecord
from omnibase_core.models.intelligence.model_pattern_warning import ModelPatternWarning
from omnibase_core.models.intelligence.model_tool_execution import ModelToolExecution
from omnibase_core.models.intelligence.model_tool_execution_content import (
    ModelToolExecutionContent,
)

__all__ = [
    # Enums (re-exported for convenience)
    "EnumPatternKind",
    # Models - Intent classification
    "ModelIntentClassificationInput",
    "ModelIntentClassificationOutput",
    # Models - Pattern extraction (OMN-1587)
    "ModelPatternError",
    "ModelPatternExtractionInput",
    "ModelPatternExtractionOutput",
    "ModelPatternRecord",
    "ModelPatternWarning",
    # Models - Tool execution (OMN-1608)
    "ModelToolExecution",
    # Models - Tool execution content (OMN-1701)
    "ModelToolExecutionContent",
    # Models - Intent storage (OMN-1645)
    "ModelIntentQueryResult",
    "ModelIntentRecord",
    "ModelIntentStorageResult",
    # Models - Intent Intelligence Framework (OMN-2486)
    "ModelTypedIntent",
    "ModelIntentDriftSignal",
    "ModelIntentCostForecast",
    "ModelIntentGraphNode",
    "ModelIntentTransition",
    "ModelIntentToCommitBinding",
    "ModelUserIntentProfile",
    "ModelIntentRollbackTrigger",
    # TypedDicts (canonical names)
    "TypedDictConversationMessage",
    "TypedDictIntentContext",
    "TypedDictIntentMetadata",
    "TypedDictSecondaryIntent",
]
