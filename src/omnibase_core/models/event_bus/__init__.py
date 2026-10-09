# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Event bus models for ONEX message handling."""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .model_archive_replay_provenance import ModelArchiveReplayProvenance
    from .model_bus_binding import ModelBusBinding
    from .model_bus_group_describe import ModelBusGroupDescribe
    from .model_consumer_group_iam_patterns import ModelConsumerGroupIamPatterns
    from .model_consumer_group_iam_source import ModelConsumerGroupIamSource
    from .model_consumer_group_scope import ModelConsumerGroupScope
    from .model_delivery_failure_evidence import ModelDeliveryFailureEvidence
    from .model_delivery_result import ModelDeliveryResult
    from .model_event_bus_bootstrap_result import ModelEventBusBootstrapResult
    from .model_event_bus_input_output_state import ModelEventBusInputOutputState
    from .model_event_bus_input_state import ModelEventBusInputState
    from .model_event_bus_output_field import ModelEventBusOutputField
    from .model_event_bus_output_state import ModelEventBusOutputState
    from .model_event_bus_readiness import ModelEventBusReadiness
    from .model_event_bus_runtime_state import ModelEventBusRuntimeState
    from .model_event_headers import ModelEventHeaders
    from .model_event_message import ModelEventMessage
    from .model_primary_dlq_wire_payload import ModelPrimaryDlqWirePayload
    from .model_producer_health_status import ModelProducerHealthStatus
    from .model_producer_message import ModelProducerMessage
    from .model_quarantine_wire_payload import ModelQuarantineWirePayload
    from .model_resolved_bus_bindings import ModelResolvedBusBindings
    from .model_transport_publish_acknowledgement import (
        ModelTransportPublishAcknowledgement,
    )

__all__ = [
    "ModelArchiveReplayProvenance",
    "ModelBusBinding",
    "ModelBusGroupDescribe",
    "ModelConsumerGroupIamPatterns",
    "ModelConsumerGroupIamSource",
    "ModelConsumerGroupScope",
    "ModelDeliveryFailureEvidence",
    "ModelDeliveryResult",
    "ModelEventBusBootstrapResult",
    "ModelEventBusInputOutputState",
    "ModelEventBusInputState",
    "ModelEventBusOutputField",
    "ModelEventBusOutputState",
    "ModelEventBusReadiness",
    "ModelEventBusRuntimeState",
    "ModelEventHeaders",
    "ModelEventMessage",
    "ModelProducerHealthStatus",
    "ModelProducerMessage",
    "ModelPrimaryDlqWirePayload",
    "ModelQuarantineWirePayload",
    "ModelResolvedBusBindings",
    "ModelTransportPublishAcknowledgement",
]


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "ModelArchiveReplayProvenance": (
        "omnibase_core.models.event_bus.model_archive_replay_provenance",
        "ModelArchiveReplayProvenance",
    ),
    "ModelBusBinding": (
        "omnibase_core.models.event_bus.model_bus_binding",
        "ModelBusBinding",
    ),
    "ModelBusGroupDescribe": (
        "omnibase_core.models.event_bus.model_bus_group_describe",
        "ModelBusGroupDescribe",
    ),
    "ModelConsumerGroupIamPatterns": (
        "omnibase_core.models.event_bus.model_consumer_group_iam_patterns",
        "ModelConsumerGroupIamPatterns",
    ),
    "ModelConsumerGroupIamSource": (
        "omnibase_core.models.event_bus.model_consumer_group_iam_source",
        "ModelConsumerGroupIamSource",
    ),
    "ModelConsumerGroupScope": (
        "omnibase_core.models.event_bus.model_consumer_group_scope",
        "ModelConsumerGroupScope",
    ),
    "ModelDeliveryFailureEvidence": (
        "omnibase_core.models.event_bus.model_delivery_failure_evidence",
        "ModelDeliveryFailureEvidence",
    ),
    "ModelDeliveryResult": (
        "omnibase_core.models.event_bus.model_delivery_result",
        "ModelDeliveryResult",
    ),
    "ModelEventBusBootstrapResult": (
        "omnibase_core.models.event_bus.model_event_bus_bootstrap_result",
        "ModelEventBusBootstrapResult",
    ),
    "ModelEventBusInputOutputState": (
        "omnibase_core.models.event_bus.model_event_bus_input_output_state",
        "ModelEventBusInputOutputState",
    ),
    "ModelEventBusInputState": (
        "omnibase_core.models.event_bus.model_event_bus_input_state",
        "ModelEventBusInputState",
    ),
    "ModelEventBusOutputField": (
        "omnibase_core.models.event_bus.model_event_bus_output_field",
        "ModelEventBusOutputField",
    ),
    "ModelEventBusOutputState": (
        "omnibase_core.models.event_bus.model_event_bus_output_state",
        "ModelEventBusOutputState",
    ),
    "ModelEventBusReadiness": (
        "omnibase_core.models.event_bus.model_event_bus_readiness",
        "ModelEventBusReadiness",
    ),
    "ModelEventBusRuntimeState": (
        "omnibase_core.models.event_bus.model_event_bus_runtime_state",
        "ModelEventBusRuntimeState",
    ),
    "ModelEventHeaders": (
        "omnibase_core.models.event_bus.model_event_headers",
        "ModelEventHeaders",
    ),
    "ModelEventMessage": (
        "omnibase_core.models.event_bus.model_event_message",
        "ModelEventMessage",
    ),
    "ModelPrimaryDlqWirePayload": (
        "omnibase_core.models.event_bus.model_primary_dlq_wire_payload",
        "ModelPrimaryDlqWirePayload",
    ),
    "ModelProducerHealthStatus": (
        "omnibase_core.models.event_bus.model_producer_health_status",
        "ModelProducerHealthStatus",
    ),
    "ModelProducerMessage": (
        "omnibase_core.models.event_bus.model_producer_message",
        "ModelProducerMessage",
    ),
    "ModelQuarantineWirePayload": (
        "omnibase_core.models.event_bus.model_quarantine_wire_payload",
        "ModelQuarantineWirePayload",
    ),
    "ModelResolvedBusBindings": (
        "omnibase_core.models.event_bus.model_resolved_bus_bindings",
        "ModelResolvedBusBindings",
    ),
    "ModelTransportPublishAcknowledgement": (
        "omnibase_core.models.event_bus.model_transport_publish_acknowledgement",
        "ModelTransportPublishAcknowledgement",
    ),
}


def __getattr__(name: str) -> object:
    target = _LAZY_IMPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = importlib.import_module(target[0])
    value = module if target[1] is None else getattr(module, target[1])
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted({*globals(), *_LAZY_IMPORTS})
