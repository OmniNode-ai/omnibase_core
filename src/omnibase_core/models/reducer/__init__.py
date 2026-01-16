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

Deprecated Aliases (OMN-1071)
=============================
This module provides deprecated aliases for classes renamed in v0.4.0.
The following aliases will be removed in a future version:

- ``ModelConflictResolver`` -> use ``UtilConflictResolver``
- ``ModelStreamingWindow`` -> use ``UtilStreamingWindow``

The ``__getattr__`` function provides lazy loading with deprecation warnings
to help users migrate to the new names.
"""

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

from typing import Any

from omnibase_core.models.reducer.model_intent import ModelIntent
from omnibase_core.models.reducer.model_intent_publish_result import (
    ModelIntentPublishResult,
)
from omnibase_core.models.reducer.model_reducer_context import ModelReducerContext
from omnibase_core.models.reducer.model_reducer_input import ModelReducerInput
from omnibase_core.models.reducer.model_reducer_output import ModelReducerOutput

# Canonical utility classes (import directly, no deprecation warning)
from omnibase_core.utils.util_conflict_resolver import UtilConflictResolver
from omnibase_core.utils.util_streaming_window import UtilStreamingWindow


# =============================================================================
# Deprecated aliases: Lazy-load with warnings per OMN-1071 renaming.
# =============================================================================
def __getattr__(name: str) -> Any:
    """
    Lazy loading for deprecated aliases per OMN-1071 renaming.

    Deprecated Aliases:
    -------------------
    All deprecated aliases emit DeprecationWarning when accessed:
    - ModelConflictResolver -> UtilConflictResolver
    - ModelStreamingWindow -> UtilStreamingWindow
    """
    import warnings

    if name == "ModelConflictResolver":
        warnings.warn(
            "'ModelConflictResolver' is deprecated, use 'UtilConflictResolver' "
            "from 'omnibase_core.utils.util_conflict_resolver' instead",
            DeprecationWarning,
            stacklevel=2,
        )
        return UtilConflictResolver

    if name == "ModelStreamingWindow":
        warnings.warn(
            "'ModelStreamingWindow' is deprecated, use 'UtilStreamingWindow' "
            "from 'omnibase_core.utils.util_streaming_window' instead",
            DeprecationWarning,
            stacklevel=2,
        )
        return UtilStreamingWindow

    raise AttributeError(  # error-ok: required for __getattr__ protocol
        f"module {__name__!r} has no attribute {name!r}"
    )
