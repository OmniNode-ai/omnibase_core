# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
ONEX Mixin Module

Provides reusable mixin classes for ONEX node patterns.
Mixins follow the single responsibility principle and provide specific capabilities
that can be composed into concrete node implementations.
"""

from __future__ import annotations

# NOTE(OMN-1302): I001 (import order) disabled - intentional ordering to avoid circular dependencies.

# UtilStrValueHelper is re-exported from utils for convenience. The actual class lives
# in utils.util_str_enum_base to avoid circular imports with enums.
import importlib.util
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.utils.util_str_enum_base import UtilStrValueHelper

    # Core mixins
    # Import protocols from omnibase_core (Core-native protocols)
    from omnibase_core.protocols import ProtocolEventBusRegistry
    from omnibase_core.protocols import ProtocolLogEmitter as LogEmitter

    from omnibase_core.mixins.mixin_canonical_serialization import (
        MixinCanonicalYAMLSerializer,
    )
    from omnibase_core.mixins.mixin_cli_handler import MixinCLIHandler

    # Models and protocols extracted from mixin_event_bus
    from omnibase_core.models.mixins.model_completion_data import ModelCompletionData
    from omnibase_core.mixins.mixin_compute_execution import MixinComputeExecution
    from omnibase_core.mixins.mixin_contract_metadata import MixinContractMetadata
    from omnibase_core.mixins.mixin_contract_publisher import MixinContractPublisher
    from omnibase_core.mixins.mixin_contract_state_reducer import (
        MixinContractStateReducer,
    )
    from omnibase_core.mixins.mixin_debug_discovery_logging import (
        MixinDebugDiscoveryLogging,
    )
    from omnibase_core.mixins.mixin_discovery_responder import MixinDiscoveryResponder
    from omnibase_core.mixins.mixin_effect_execution import MixinEffectExecution
    from omnibase_core.mixins.mixin_event_bus import MixinEventBus
    from omnibase_core.mixins.mixin_event_driven_node import MixinEventDrivenNode
    from omnibase_core.mixins.mixin_event_handler import MixinEventHandler
    from omnibase_core.mixins.mixin_fail_fast import MixinFailFast
    from omnibase_core.mixins.mixin_fsm_execution import MixinFSMExecution
    from omnibase_core.mixins.mixin_handler_routing import MixinHandlerRouting
    from omnibase_core.mixins.mixin_hash_computation import MixinHashComputation
    from omnibase_core.mixins.mixin_health_check import (
        MixinHealthCheck,
        check_http_service_health,
        check_kafka_health,
        check_postgresql_health,
        check_redis_health,
    )
    from omnibase_core.mixins.mixin_introspect_from_contract import (
        MixinIntrospectFromContract,
    )
    from omnibase_core.mixins.mixin_introspection import MixinNodeIntrospection
    from omnibase_core.mixins.mixin_introspection_publisher import (
        MixinIntrospectionPublisher,
    )
    from omnibase_core.mixins.mixin_lazy_evaluation import MixinLazyEvaluation
    from omnibase_core.models.mixins.model_log_data import ModelLogData
    from omnibase_core.models.mixins.model_node_introspection_data import (
        ModelNodeIntrospectionData,
    )
    from omnibase_core.mixins.mixin_node_executor import MixinNodeExecutor
    from omnibase_core.mixins.mixin_node_id_from_contract import MixinNodeIdFromContract
    from omnibase_core.mixins.mixin_node_lifecycle import MixinNodeLifecycle
    from omnibase_core.mixins.mixin_node_setup import MixinNodeSetup
    from omnibase_core.mixins.mixin_node_type_validator import MixinNodeTypeValidator
    from omnibase_core.mixins.mixin_redaction import MixinSensitiveFieldRedaction
    from omnibase_core.mixins.mixin_request_response_introspection import (
        MixinRequestResponseIntrospection,
    )
    from omnibase_core.mixins.mixin_serializable import MixinSerializable
    from omnibase_core.mixins.mixin_service_registry import MixinServiceRegistry
    from omnibase_core.mixins.mixin_tool_execution import MixinToolExecution
    from omnibase_core.mixins.mixin_workflow_execution import MixinWorkflowExecution
    from omnibase_core.mixins.mixin_yaml_serialization import MixinYAMLSerialization
    from omnibase_core.mixins.mixin_caching import MixinCaching
    from omnibase_core.mixins.mixin_trace_capture import MixinTraceCapture
    from omnibase_core.mixins.mixin_truncation_validation import (
        MixinTruncationValidation,
    )

__all__ = [
    # UtilStrValueHelper - provides __str__ for enums, must be available early
    "UtilStrValueHelper",
    "MixinCanonicalYAMLSerializer",
    "MixinComputeExecution",
    "MixinEffectExecution",
    "MixinDiscoveryResponder",
    "MixinHashComputation",
    "MixinCLIHandler",
    "MixinContractMetadata",
    "MixinContractPublisher",
    "MixinContractStateReducer",
    "MixinDebugDiscoveryLogging",
    "MixinEventDrivenNode",
    "MixinEventHandler",
    "MixinFailFast",
    "MixinFSMExecution",
    "MixinHandlerRouting",
    "MixinHealthCheck",
    "MixinIntrospectFromContract",
    "MixinIntrospectionPublisher",
    "MixinLazyEvaluation",
    "MixinNodeIdFromContract",
    "MixinNodeLifecycle",
    "MixinNodeTypeValidator",
    "MixinNodeExecutor",
    "MixinNodeSetup",
    "MixinRequestResponseIntrospection",
    "MixinServiceRegistry",
    "MixinToolExecution",
    "MixinWorkflowExecution",
    "MixinEventBus",
    "ModelCompletionData",
    "ModelLogData",
    "ModelNodeIntrospectionData",
    "LogEmitter",
    "ProtocolEventBusRegistry",
    "MixinNodeIntrospection",
    "MixinSensitiveFieldRedaction",
    "MixinSerializable",
    "MixinYAMLSerialization",
    # Health check utility functions
    "check_postgresql_health",
    "check_kafka_health",
    "check_redis_health",
    "check_http_service_health",
    # Caching mixin
    "MixinCaching",
    # Trace capture mixin - wires existing trace infrastructure to node execution
    "MixinTraceCapture",
    # Truncation validation mixin
    "MixinTruncationValidation",
]


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "UtilStrValueHelper": (
        "omnibase_core.utils.util_str_enum_base",
        "UtilStrValueHelper",
    ),
    "ProtocolEventBusRegistry": ("omnibase_core.protocols", "ProtocolEventBusRegistry"),
    "LogEmitter": ("omnibase_core.protocols", "ProtocolLogEmitter"),
    "MixinCanonicalYAMLSerializer": (
        "omnibase_core.mixins.mixin_canonical_serialization",
        "MixinCanonicalYAMLSerializer",
    ),
    "MixinCLIHandler": ("omnibase_core.mixins.mixin_cli_handler", "MixinCLIHandler"),
    "ModelCompletionData": (
        "omnibase_core.models.mixins.model_completion_data",
        "ModelCompletionData",
    ),
    "MixinComputeExecution": (
        "omnibase_core.mixins.mixin_compute_execution",
        "MixinComputeExecution",
    ),
    "MixinContractMetadata": (
        "omnibase_core.mixins.mixin_contract_metadata",
        "MixinContractMetadata",
    ),
    "MixinContractPublisher": (
        "omnibase_core.mixins.mixin_contract_publisher",
        "MixinContractPublisher",
    ),
    "MixinContractStateReducer": (
        "omnibase_core.mixins.mixin_contract_state_reducer",
        "MixinContractStateReducer",
    ),
    "MixinDebugDiscoveryLogging": (
        "omnibase_core.mixins.mixin_debug_discovery_logging",
        "MixinDebugDiscoveryLogging",
    ),
    "MixinDiscoveryResponder": (
        "omnibase_core.mixins.mixin_discovery_responder",
        "MixinDiscoveryResponder",
    ),
    "MixinEffectExecution": (
        "omnibase_core.mixins.mixin_effect_execution",
        "MixinEffectExecution",
    ),
    "MixinEventBus": ("omnibase_core.mixins.mixin_event_bus", "MixinEventBus"),
    "MixinEventDrivenNode": (
        "omnibase_core.mixins.mixin_event_driven_node",
        "MixinEventDrivenNode",
    ),
    "MixinEventHandler": (
        "omnibase_core.mixins.mixin_event_handler",
        "MixinEventHandler",
    ),
    "MixinFailFast": ("omnibase_core.mixins.mixin_fail_fast", "MixinFailFast"),
    "MixinFSMExecution": (
        "omnibase_core.mixins.mixin_fsm_execution",
        "MixinFSMExecution",
    ),
    "MixinHandlerRouting": (
        "omnibase_core.mixins.mixin_handler_routing",
        "MixinHandlerRouting",
    ),
    "MixinHashComputation": (
        "omnibase_core.mixins.mixin_hash_computation",
        "MixinHashComputation",
    ),
    "MixinHealthCheck": ("omnibase_core.mixins.mixin_health_check", "MixinHealthCheck"),
    "check_http_service_health": (
        "omnibase_core.mixins.mixin_health_check",
        "check_http_service_health",
    ),
    "check_kafka_health": (
        "omnibase_core.mixins.mixin_health_check",
        "check_kafka_health",
    ),
    "check_postgresql_health": (
        "omnibase_core.mixins.mixin_health_check",
        "check_postgresql_health",
    ),
    "check_redis_health": (
        "omnibase_core.mixins.mixin_health_check",
        "check_redis_health",
    ),
    "MixinIntrospectFromContract": (
        "omnibase_core.mixins.mixin_introspect_from_contract",
        "MixinIntrospectFromContract",
    ),
    "MixinNodeIntrospection": (
        "omnibase_core.mixins.mixin_introspection",
        "MixinNodeIntrospection",
    ),
    "MixinIntrospectionPublisher": (
        "omnibase_core.mixins.mixin_introspection_publisher",
        "MixinIntrospectionPublisher",
    ),
    "MixinLazyEvaluation": (
        "omnibase_core.mixins.mixin_lazy_evaluation",
        "MixinLazyEvaluation",
    ),
    "ModelLogData": ("omnibase_core.models.mixins.model_log_data", "ModelLogData"),
    "ModelNodeIntrospectionData": (
        "omnibase_core.models.mixins.model_node_introspection_data",
        "ModelNodeIntrospectionData",
    ),
    "MixinNodeExecutor": (
        "omnibase_core.mixins.mixin_node_executor",
        "MixinNodeExecutor",
    ),
    "MixinNodeIdFromContract": (
        "omnibase_core.mixins.mixin_node_id_from_contract",
        "MixinNodeIdFromContract",
    ),
    "MixinNodeLifecycle": (
        "omnibase_core.mixins.mixin_node_lifecycle",
        "MixinNodeLifecycle",
    ),
    "MixinNodeSetup": ("omnibase_core.mixins.mixin_node_setup", "MixinNodeSetup"),
    "MixinNodeTypeValidator": (
        "omnibase_core.mixins.mixin_node_type_validator",
        "MixinNodeTypeValidator",
    ),
    "MixinSensitiveFieldRedaction": (
        "omnibase_core.mixins.mixin_redaction",
        "MixinSensitiveFieldRedaction",
    ),
    "MixinRequestResponseIntrospection": (
        "omnibase_core.mixins.mixin_request_response_introspection",
        "MixinRequestResponseIntrospection",
    ),
    "MixinSerializable": (
        "omnibase_core.mixins.mixin_serializable",
        "MixinSerializable",
    ),
    "MixinServiceRegistry": (
        "omnibase_core.mixins.mixin_service_registry",
        "MixinServiceRegistry",
    ),
    "MixinToolExecution": (
        "omnibase_core.mixins.mixin_tool_execution",
        "MixinToolExecution",
    ),
    "MixinWorkflowExecution": (
        "omnibase_core.mixins.mixin_workflow_execution",
        "MixinWorkflowExecution",
    ),
    "MixinYAMLSerialization": (
        "omnibase_core.mixins.mixin_yaml_serialization",
        "MixinYAMLSerialization",
    ),
    "MixinCaching": ("omnibase_core.mixins.mixin_caching", "MixinCaching"),
    "MixinTraceCapture": (
        "omnibase_core.mixins.mixin_trace_capture",
        "MixinTraceCapture",
    ),
    "MixinTruncationValidation": (
        "omnibase_core.mixins.mixin_truncation_validation",
        "MixinTruncationValidation",
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
