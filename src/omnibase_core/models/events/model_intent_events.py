"""
Intent event models for coordination I/O (re-exports).

This module provides a unified import location for intent event models.
The actual implementations are in separate files per ONEX single-class rule.

See:
    - model_event_publish_intent.py: ModelEventPublishIntent
    - model_intent_execution_result.py: ModelIntentExecutionResult
    - constants_topic_taxonomy.py: TOPIC_EVENT_PUBLISH_INTENT
"""

from omnibase_core.constants.constants_topic_taxonomy import (
    TOPIC_EVENT_PUBLISH_INTENT,
)
from omnibase_core.models.events.model_event_publish_intent import (
    ModelEventPublishIntent,
)
from omnibase_core.models.events.model_event_publish_intent import (
    _rebuild_model as _rebuild_event_publish_intent,
)
from omnibase_core.models.events.model_intent_execution_result import (
    ModelIntentExecutionResult,
)

# Rebuild forward references for ModelEventPublishIntent
# This resolves ModelEventPayloadUnion and ModelRetryPolicy type annotations
_rebuild_event_publish_intent()

__all__ = [
    "TOPIC_EVENT_PUBLISH_INTENT",
    "ModelEventPublishIntent",
    "ModelIntentExecutionResult",
]
