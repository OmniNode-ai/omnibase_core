# SPDX-FileCopyrightText: 2025 OmniNode Team
# SPDX-License-Identifier: Apache-2.0
"""
Reducer models for ONEX NodeReducer operations.

This module provides models for FSM-driven state management:
- ModelReducerInput: Input model for reduction operations
- ModelReducerOutput: Output model with intents for side effects
- ModelReducerContext: Handler context (deliberately excludes time injection)
- ModelIntent: Side effect declaration for pure FSM pattern
- ModelIntentPublishResult: Result of publishing an intent
- UtilConflictResolver: Conflict resolution strategies (moved from ModelConflictResolver)
- UtilStreamingWindow: Time-based windowing for streaming (moved from ModelStreamingWindow)

"""

from omnibase_core.models.reducer.model_intent import ModelIntent
from omnibase_core.models.reducer.model_intent_publish_result import (
    ModelIntentPublishResult,
)
from omnibase_core.models.reducer.model_reducer_context import ModelReducerContext
from omnibase_core.models.reducer.model_reducer_input import ModelReducerInput
from omnibase_core.models.reducer.model_reducer_output import ModelReducerOutput

# Utilities moved to utils/ - re-export for backwards compatibility
from omnibase_core.utils.util_conflict_resolver import (
    ModelConflictResolver,  # DEPRECATED alias, use UtilConflictResolver
    UtilConflictResolver,
)
from omnibase_core.utils.util_streaming_window import (
    ModelStreamingWindow,  # DEPRECATED alias, use UtilStreamingWindow
    UtilStreamingWindow,
)

__all__ = [
    "ModelConflictResolver",  # DEPRECATED alias, use UtilConflictResolver
    "ModelIntent",
    "ModelIntentPublishResult",
    "ModelReducerContext",
    "ModelReducerInput",
    "ModelReducerOutput",
    "ModelStreamingWindow",  # DEPRECATED alias, use UtilStreamingWindow
    "UtilConflictResolver",
    "UtilStreamingWindow",
]
