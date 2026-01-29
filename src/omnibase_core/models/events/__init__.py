"""
ONEX event models.

Event models for coordination and domain events in the ONEX framework.
"""

from omnibase_core.enums.enum_topic_taxonomy import (
    EnumCleanupPolicy,
    EnumTopicType,
)
from omnibase_core.models.events.contract_registration import (
    CONTRACT_DEREGISTERED_EVENT,
    CONTRACT_REGISTERED_EVENT,
    NODE_HEARTBEAT_EVENT,
    ModelContractDeregisteredEvent,
    ModelContractRegisteredEvent,
    ModelNodeHeartbeatEvent,
)
from omnibase_core.models.events.model_event_payload_base import (
    ModelEventPayloadBase,
)
from omnibase_core.models.events.model_intent_events import (
    TOPIC_EVENT_PUBLISH_INTENT,
    ModelEventPublishIntent,
    ModelIntentExecutionResult,
)
from omnibase_core.models.events.model_intent_query_requested_event import (
    INTENT_QUERY_REQUESTED_EVENT,
    ModelIntentQueryRequestedEvent,
)
from omnibase_core.models.events.model_intent_query_response_event import (
    INTENT_QUERY_RESPONSE_EVENT,
    ModelIntentQueryResponseEvent,
)
from omnibase_core.models.events.model_intent_record_payload import (
    ModelIntentRecordPayload,
)
from omnibase_core.models.events.model_intent_stored_event import (
    INTENT_STORED_EVENT,
    ModelIntentStoredEvent,
)
from omnibase_core.models.events.model_runtime_events import (
    NODE_GRAPH_READY_EVENT,
    NODE_REGISTERED_EVENT,
    NODE_UNREGISTERED_EVENT,
    RUNTIME_READY_EVENT,
    SUBSCRIPTION_CREATED_EVENT,
    SUBSCRIPTION_FAILED_EVENT,
    SUBSCRIPTION_REMOVED_EVENT,
    WIRING_ERROR_EVENT,
    WIRING_RESULT_EVENT,
    ModelNodeGraphInfo,
    ModelNodeGraphReadyEvent,
    ModelNodeRegisteredEvent,
    ModelNodeUnregisteredEvent,
    ModelRuntimeEventBase,
    ModelRuntimeReadyEvent,
    ModelSubscriptionCreatedEvent,
    ModelSubscriptionFailedEvent,
    ModelSubscriptionRemovedEvent,
    ModelWiringErrorEvent,
    ModelWiringErrorInfo,
    ModelWiringResultEvent,
)
from omnibase_core.models.events.model_topic_config import ModelTopicConfig
from omnibase_core.models.events.model_topic_manifest import ModelTopicManifest
from omnibase_core.models.events.model_topic_naming import (
    ModelTopicNaming,
    get_topic_category,
    validate_topic_matches_category,
)

__all__ = [
    # Contract registration events (OMN-1651)
    "CONTRACT_DEREGISTERED_EVENT",
    "CONTRACT_REGISTERED_EVENT",
    "NODE_HEARTBEAT_EVENT",
    "ModelContractDeregisteredEvent",
    "ModelContractRegisteredEvent",
    "ModelNodeHeartbeatEvent",
    # Intent coordination events (existing)
    "ModelEventPublishIntent",
    "ModelIntentExecutionResult",
    "TOPIC_EVENT_PUBLISH_INTENT",
    # Intent storage events (WS-4)
    "INTENT_STORED_EVENT",
    "ModelIntentStoredEvent",
    "INTENT_QUERY_REQUESTED_EVENT",
    "ModelIntentQueryRequestedEvent",
    "INTENT_QUERY_RESPONSE_EVENT",
    "ModelIntentRecordPayload",
    "ModelIntentQueryResponseEvent",
    # Topic naming and routing
    "ModelTopicNaming",
    "get_topic_category",
    "validate_topic_matches_category",
    # Runtime event type constants
    "NODE_GRAPH_READY_EVENT",
    "NODE_REGISTERED_EVENT",
    "NODE_UNREGISTERED_EVENT",
    "RUNTIME_READY_EVENT",
    "SUBSCRIPTION_CREATED_EVENT",
    "SUBSCRIPTION_FAILED_EVENT",
    "SUBSCRIPTION_REMOVED_EVENT",
    "WIRING_ERROR_EVENT",
    "WIRING_RESULT_EVENT",
    # Runtime event models
    "ModelEventPayloadBase",
    "ModelNodeGraphInfo",
    "ModelNodeGraphReadyEvent",
    "ModelNodeRegisteredEvent",
    "ModelNodeUnregisteredEvent",
    "ModelRuntimeEventBase",
    "ModelRuntimeReadyEvent",
    "ModelSubscriptionCreatedEvent",
    "ModelSubscriptionFailedEvent",
    "ModelSubscriptionRemovedEvent",
    "ModelWiringErrorEvent",
    "ModelWiringErrorInfo",
    "ModelWiringResultEvent",
    # Topic manifest models
    "EnumCleanupPolicy",
    "EnumTopicType",
    "ModelTopicConfig",
    "ModelTopicManifest",
]
