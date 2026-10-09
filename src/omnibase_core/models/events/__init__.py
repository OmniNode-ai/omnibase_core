# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
ONEX event models.

Event models for coordination and domain events in the ONEX framework.
"""

from __future__ import annotations

import importlib.util
from typing import TYPE_CHECKING

if TYPE_CHECKING:
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
    from omnibase_core.models.events.model_agent_match_payload import (
        ModelAgentMatchPayload,
    )
    from omnibase_core.models.events.model_context_utilization_payload import (
        ModelContextUtilizationPayload,
    )
    from omnibase_core.models.events.model_episode_event import (
        TOPIC_EPISODE_BOUNDARY,
        ModelEpisodeEvent,
    )
    from omnibase_core.models.events.model_event_envelope_v1_minimal import (
        EventEnvelopeV1Minimal,
        ModelEventEnvelopeV1Minimal,
    )
    from omnibase_core.models.events.model_event_payload_base import (
        ModelEventPayloadBase,
    )
    from omnibase_core.models.events.model_git_hook_event import (
        TOPIC_GIT_HOOK_EVENT,
        ModelGitHookEvent,
    )
    from omnibase_core.models.events.model_github_pr_status_event import (
        TOPIC_GITHUB_PR_STATUS_EVENT,
        ModelGitHubPRStatusEvent,
    )
    from omnibase_core.models.events.model_intent_events import (
        ModelEventPublishIntent,
        ModelIntentExecutionResult,
    )
    from omnibase_core.models.events.model_intent_query_requested_event import (
        ModelIntentQueryRequestedEvent,
    )
    from omnibase_core.models.events.model_intent_query_response_event import (
        ModelIntentQueryResponseEvent,
    )
    from omnibase_core.models.events.model_intent_record_payload import (
        ModelIntentRecordPayload,
    )
    from omnibase_core.models.events.model_intent_stored_event import (
        ModelIntentStoredEvent,
    )
    from omnibase_core.models.events.model_latency_breakdown_payload import (
        ModelLatencyBreakdownPayload,
    )
    from omnibase_core.models.events.model_linear_snapshot_event import (
        TOPIC_LINEAR_SNAPSHOT_EVENT,
        ModelLinearSnapshotEvent,
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
    # Intent storage events (WS-4)
    "ModelIntentStoredEvent",
    "ModelIntentQueryRequestedEvent",
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
    # Injection metrics payloads (OMN-1901)
    "ModelAgentMatchPayload",
    "ModelContextUtilizationPayload",
    "ModelLatencyBreakdownPayload",
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
    # Workflow automation event models (OMN-2655)
    "TOPIC_GITHUB_PR_STATUS_EVENT",
    "ModelGitHubPRStatusEvent",
    "TOPIC_GIT_HOOK_EVENT",
    "ModelGitHookEvent",
    "TOPIC_LINEAR_SNAPSHOT_EVENT",
    "ModelLinearSnapshotEvent",
    # Episode boundary events (OMN-5559)
    "TOPIC_EPISODE_BOUNDARY",
    "ModelEpisodeEvent",
    # Minimal cross-repo wire envelope migrated from compat (OMN-12188)
    "EventEnvelopeV1Minimal",
    "ModelEventEnvelopeV1Minimal",
]


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "EnumCleanupPolicy": (
        "omnibase_core.enums.enum_topic_taxonomy",
        "EnumCleanupPolicy",
    ),
    "EnumTopicType": ("omnibase_core.enums.enum_topic_taxonomy", "EnumTopicType"),
    "CONTRACT_DEREGISTERED_EVENT": (
        "omnibase_core.models.events.contract_registration",
        "CONTRACT_DEREGISTERED_EVENT",
    ),
    "CONTRACT_REGISTERED_EVENT": (
        "omnibase_core.models.events.contract_registration",
        "CONTRACT_REGISTERED_EVENT",
    ),
    "NODE_HEARTBEAT_EVENT": (
        "omnibase_core.models.events.contract_registration",
        "NODE_HEARTBEAT_EVENT",
    ),
    "ModelContractDeregisteredEvent": (
        "omnibase_core.models.events.contract_registration",
        "ModelContractDeregisteredEvent",
    ),
    "ModelContractRegisteredEvent": (
        "omnibase_core.models.events.contract_registration",
        "ModelContractRegisteredEvent",
    ),
    "ModelNodeHeartbeatEvent": (
        "omnibase_core.models.events.contract_registration",
        "ModelNodeHeartbeatEvent",
    ),
    "ModelAgentMatchPayload": (
        "omnibase_core.models.events.model_agent_match_payload",
        "ModelAgentMatchPayload",
    ),
    "ModelContextUtilizationPayload": (
        "omnibase_core.models.events.model_context_utilization_payload",
        "ModelContextUtilizationPayload",
    ),
    "TOPIC_EPISODE_BOUNDARY": (
        "omnibase_core.models.events.model_episode_event",
        "TOPIC_EPISODE_BOUNDARY",
    ),
    "ModelEpisodeEvent": (
        "omnibase_core.models.events.model_episode_event",
        "ModelEpisodeEvent",
    ),
    "EventEnvelopeV1Minimal": (
        "omnibase_core.models.events.model_event_envelope_v1_minimal",
        "EventEnvelopeV1Minimal",
    ),
    "ModelEventEnvelopeV1Minimal": (
        "omnibase_core.models.events.model_event_envelope_v1_minimal",
        "ModelEventEnvelopeV1Minimal",
    ),
    "ModelEventPayloadBase": (
        "omnibase_core.models.events.model_event_payload_base",
        "ModelEventPayloadBase",
    ),
    "TOPIC_GIT_HOOK_EVENT": (
        "omnibase_core.models.events.model_git_hook_event",
        "TOPIC_GIT_HOOK_EVENT",
    ),
    "ModelGitHookEvent": (
        "omnibase_core.models.events.model_git_hook_event",
        "ModelGitHookEvent",
    ),
    "TOPIC_GITHUB_PR_STATUS_EVENT": (
        "omnibase_core.models.events.model_github_pr_status_event",
        "TOPIC_GITHUB_PR_STATUS_EVENT",
    ),
    "ModelGitHubPRStatusEvent": (
        "omnibase_core.models.events.model_github_pr_status_event",
        "ModelGitHubPRStatusEvent",
    ),
    "ModelEventPublishIntent": (
        "omnibase_core.models.events.model_intent_events",
        "ModelEventPublishIntent",
    ),
    "ModelIntentExecutionResult": (
        "omnibase_core.models.events.model_intent_events",
        "ModelIntentExecutionResult",
    ),
    "ModelIntentQueryRequestedEvent": (
        "omnibase_core.models.events.model_intent_query_requested_event",
        "ModelIntentQueryRequestedEvent",
    ),
    "ModelIntentQueryResponseEvent": (
        "omnibase_core.models.events.model_intent_query_response_event",
        "ModelIntentQueryResponseEvent",
    ),
    "ModelIntentRecordPayload": (
        "omnibase_core.models.events.model_intent_record_payload",
        "ModelIntentRecordPayload",
    ),
    "ModelIntentStoredEvent": (
        "omnibase_core.models.events.model_intent_stored_event",
        "ModelIntentStoredEvent",
    ),
    "ModelLatencyBreakdownPayload": (
        "omnibase_core.models.events.model_latency_breakdown_payload",
        "ModelLatencyBreakdownPayload",
    ),
    "TOPIC_LINEAR_SNAPSHOT_EVENT": (
        "omnibase_core.models.events.model_linear_snapshot_event",
        "TOPIC_LINEAR_SNAPSHOT_EVENT",
    ),
    "ModelLinearSnapshotEvent": (
        "omnibase_core.models.events.model_linear_snapshot_event",
        "ModelLinearSnapshotEvent",
    ),
    "NODE_GRAPH_READY_EVENT": (
        "omnibase_core.models.events.model_runtime_events",
        "NODE_GRAPH_READY_EVENT",
    ),
    "NODE_REGISTERED_EVENT": (
        "omnibase_core.models.events.model_runtime_events",
        "NODE_REGISTERED_EVENT",
    ),
    "NODE_UNREGISTERED_EVENT": (
        "omnibase_core.models.events.model_runtime_events",
        "NODE_UNREGISTERED_EVENT",
    ),
    "RUNTIME_READY_EVENT": (
        "omnibase_core.models.events.model_runtime_events",
        "RUNTIME_READY_EVENT",
    ),
    "SUBSCRIPTION_CREATED_EVENT": (
        "omnibase_core.models.events.model_runtime_events",
        "SUBSCRIPTION_CREATED_EVENT",
    ),
    "SUBSCRIPTION_FAILED_EVENT": (
        "omnibase_core.models.events.model_runtime_events",
        "SUBSCRIPTION_FAILED_EVENT",
    ),
    "SUBSCRIPTION_REMOVED_EVENT": (
        "omnibase_core.models.events.model_runtime_events",
        "SUBSCRIPTION_REMOVED_EVENT",
    ),
    "WIRING_ERROR_EVENT": (
        "omnibase_core.models.events.model_runtime_events",
        "WIRING_ERROR_EVENT",
    ),
    "WIRING_RESULT_EVENT": (
        "omnibase_core.models.events.model_runtime_events",
        "WIRING_RESULT_EVENT",
    ),
    "ModelNodeGraphInfo": (
        "omnibase_core.models.events.model_runtime_events",
        "ModelNodeGraphInfo",
    ),
    "ModelNodeGraphReadyEvent": (
        "omnibase_core.models.events.model_runtime_events",
        "ModelNodeGraphReadyEvent",
    ),
    "ModelNodeRegisteredEvent": (
        "omnibase_core.models.events.model_runtime_events",
        "ModelNodeRegisteredEvent",
    ),
    "ModelNodeUnregisteredEvent": (
        "omnibase_core.models.events.model_runtime_events",
        "ModelNodeUnregisteredEvent",
    ),
    "ModelRuntimeEventBase": (
        "omnibase_core.models.events.model_runtime_events",
        "ModelRuntimeEventBase",
    ),
    "ModelRuntimeReadyEvent": (
        "omnibase_core.models.events.model_runtime_events",
        "ModelRuntimeReadyEvent",
    ),
    "ModelSubscriptionCreatedEvent": (
        "omnibase_core.models.events.model_runtime_events",
        "ModelSubscriptionCreatedEvent",
    ),
    "ModelSubscriptionFailedEvent": (
        "omnibase_core.models.events.model_runtime_events",
        "ModelSubscriptionFailedEvent",
    ),
    "ModelSubscriptionRemovedEvent": (
        "omnibase_core.models.events.model_runtime_events",
        "ModelSubscriptionRemovedEvent",
    ),
    "ModelWiringErrorEvent": (
        "omnibase_core.models.events.model_runtime_events",
        "ModelWiringErrorEvent",
    ),
    "ModelWiringErrorInfo": (
        "omnibase_core.models.events.model_runtime_events",
        "ModelWiringErrorInfo",
    ),
    "ModelWiringResultEvent": (
        "omnibase_core.models.events.model_runtime_events",
        "ModelWiringResultEvent",
    ),
    "ModelTopicConfig": (
        "omnibase_core.models.events.model_topic_config",
        "ModelTopicConfig",
    ),
    "ModelTopicManifest": (
        "omnibase_core.models.events.model_topic_manifest",
        "ModelTopicManifest",
    ),
    "ModelTopicNaming": (
        "omnibase_core.models.events.model_topic_naming",
        "ModelTopicNaming",
    ),
    "get_topic_category": (
        "omnibase_core.models.events.model_topic_naming",
        "get_topic_category",
    ),
    "validate_topic_matches_category": (
        "omnibase_core.models.events.model_topic_naming",
        "validate_topic_matches_category",
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
