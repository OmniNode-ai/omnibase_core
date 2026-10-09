# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Intelligence models for ONEX integration.

Domain models for AI/ML intelligence operations,
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

from __future__ import annotations

import importlib.util
from typing import TYPE_CHECKING

if TYPE_CHECKING:
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
    from omnibase_core.models.intelligence.model_pattern_record import (
        ModelPatternRecord,
    )
    from omnibase_core.models.intelligence.model_pattern_warning import (
        ModelPatternWarning,
    )
    from omnibase_core.models.intelligence.model_tool_execution import (
        ModelToolExecution,
    )
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


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "EnumPatternKind": ("omnibase_core.enums", "EnumPatternKind"),
    "ModelIntentCostForecast": (
        "omnibase_core.models.intelligence.intent.model_intent_cost_forecast",
        "ModelIntentCostForecast",
    ),
    "ModelIntentDriftSignal": (
        "omnibase_core.models.intelligence.intent.model_intent_drift_signal",
        "ModelIntentDriftSignal",
    ),
    "ModelIntentGraphNode": (
        "omnibase_core.models.intelligence.intent.model_intent_graph_node",
        "ModelIntentGraphNode",
    ),
    "ModelIntentRollbackTrigger": (
        "omnibase_core.models.intelligence.intent.model_intent_rollback_trigger",
        "ModelIntentRollbackTrigger",
    ),
    "ModelIntentToCommitBinding": (
        "omnibase_core.models.intelligence.intent.model_intent_to_commit_binding",
        "ModelIntentToCommitBinding",
    ),
    "ModelIntentTransition": (
        "omnibase_core.models.intelligence.intent.model_intent_transition",
        "ModelIntentTransition",
    ),
    "ModelTypedIntent": (
        "omnibase_core.models.intelligence.intent.model_typed_intent",
        "ModelTypedIntent",
    ),
    "ModelUserIntentProfile": (
        "omnibase_core.models.intelligence.intent.model_user_intent_profile",
        "ModelUserIntentProfile",
    ),
    "ModelIntentClassificationInput": (
        "omnibase_core.models.intelligence.model_intent_classification_input",
        "ModelIntentClassificationInput",
    ),
    "TypedDictConversationMessage": (
        "omnibase_core.models.intelligence.model_intent_classification_input",
        "TypedDictConversationMessage",
    ),
    "TypedDictIntentContext": (
        "omnibase_core.models.intelligence.model_intent_classification_input",
        "TypedDictIntentContext",
    ),
    "ModelIntentClassificationOutput": (
        "omnibase_core.models.intelligence.model_intent_classification_output",
        "ModelIntentClassificationOutput",
    ),
    "TypedDictIntentMetadata": (
        "omnibase_core.models.intelligence.model_intent_classification_output",
        "TypedDictIntentMetadata",
    ),
    "TypedDictSecondaryIntent": (
        "omnibase_core.models.intelligence.model_intent_classification_output",
        "TypedDictSecondaryIntent",
    ),
    "ModelIntentQueryResult": (
        "omnibase_core.models.intelligence.model_intent_query_result",
        "ModelIntentQueryResult",
    ),
    "ModelIntentRecord": (
        "omnibase_core.models.intelligence.model_intent_record",
        "ModelIntentRecord",
    ),
    "ModelIntentStorageResult": (
        "omnibase_core.models.intelligence.model_intent_storage_result",
        "ModelIntentStorageResult",
    ),
    "ModelPatternError": (
        "omnibase_core.models.intelligence.model_pattern_error",
        "ModelPatternError",
    ),
    "ModelPatternExtractionInput": (
        "omnibase_core.models.intelligence.model_pattern_extraction_input",
        "ModelPatternExtractionInput",
    ),
    "ModelPatternExtractionOutput": (
        "omnibase_core.models.intelligence.model_pattern_extraction_output",
        "ModelPatternExtractionOutput",
    ),
    "ModelPatternRecord": (
        "omnibase_core.models.intelligence.model_pattern_record",
        "ModelPatternRecord",
    ),
    "ModelPatternWarning": (
        "omnibase_core.models.intelligence.model_pattern_warning",
        "ModelPatternWarning",
    ),
    "ModelToolExecution": (
        "omnibase_core.models.intelligence.model_tool_execution",
        "ModelToolExecution",
    ),
    "ModelToolExecutionContent": (
        "omnibase_core.models.intelligence.model_tool_execution_content",
        "ModelToolExecutionContent",
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
