from pydantic import Field

"""
ONEX Mixin Module

Provides reusable mixin classes for ONEX node patterns.
Mixins follow the single responsibility principle and provide specific capabilities
that can be composed into concrete node implementations.
"""

# Core mixins
# Import protocols from omnibase_core (Core-native protocols)
from omnibase_core.protocols import ProtocolEventBusRegistry as RegistryWithBus
from omnibase_core.protocols import ProtocolLogEmitter as LogEmitter

# Protocol name transition: ProtocolRegistryWithBus → ProtocolEventBusRegistry
# omnibase_spi v0.2.0 renamed ProtocolRegistryWithBus to ProtocolEventBusRegistry
# Alias provided for smooth upgrade: use ProtocolEventBusRegistry in new code
# This alias may be removed in future versions
ProtocolEventBusRegistry = RegistryWithBus
ProtocolRegistryWithBus = ProtocolEventBusRegistry  # Legacy name alias

from omnibase_core.mixins.mixin_canonical_serialization import (
    MixinCanonicalYAMLSerializer,
)
from omnibase_core.mixins.mixin_cli_handler import MixinCLIHandler

# Models and protocols extracted from mixin_event_bus
from omnibase_core.mixins.mixin_completion_data import MixinCompletionData
from omnibase_core.mixins.mixin_compute_execution import MixinComputeExecution
from omnibase_core.mixins.mixin_contract_metadata import MixinContractMetadata
from omnibase_core.mixins.mixin_contract_state_reducer import MixinContractStateReducer
from omnibase_core.mixins.mixin_debug_discovery_logging import (
    MixinDebugDiscoveryLogging,
)
from omnibase_core.mixins.mixin_discovery_responder import MixinDiscoveryResponder
from omnibase_core.mixins.mixin_effect_execution import MixinEffectExecution
from omnibase_core.mixins.mixin_event_bus import MixinEventBus
from omnibase_core.mixins.mixin_event_driven_node import MixinEventDrivenNode
from omnibase_core.mixins.mixin_event_handler import MixinEventHandler
from omnibase_core.mixins.mixin_event_listener import MixinEventListener
from omnibase_core.mixins.mixin_fail_fast import MixinFailFast
from omnibase_core.mixins.mixin_fsm_execution import MixinFSMExecution
from omnibase_core.mixins.mixin_hash_computation import MixinHashComputation
from omnibase_core.mixins.mixin_health_check import (
    MixinHealthCheck,
    check_http_service_health,
    check_kafka_health,
    check_postgresql_health,
    check_redis_health,
)
from omnibase_core.mixins.mixin_hybrid_execution import MixinHybridExecution
from omnibase_core.mixins.mixin_intent_publisher import MixinIntentPublisher
from omnibase_core.mixins.mixin_introspect_from_contract import (
    MixinIntrospectFromContract,
)
from omnibase_core.mixins.mixin_introspection import MixinNodeIntrospection
from omnibase_core.mixins.mixin_introspection_publisher import (
    MixinIntrospectionPublisher,
)
from omnibase_core.mixins.mixin_lazy_evaluation import MixinLazyEvaluation
from omnibase_core.mixins.mixin_log_data import MixinLogData
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

__all__ = [
    "MixinCanonicalYAMLSerializer",
    "MixinComputeExecution",
    "MixinEffectExecution",
    "MixinDiscoveryResponder",
    "MixinHashComputation",
    "MixinCLIHandler",
    "MixinContractMetadata",
    "MixinContractStateReducer",
    "MixinDebugDiscoveryLogging",
    "MixinEventDrivenNode",
    "MixinEventHandler",
    "MixinEventListener",
    "MixinFailFast",
    "MixinFSMExecution",
    "MixinHealthCheck",
    "MixinHybridExecution",
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
    "MixinCompletionData",
    "MixinLogData",
    "LogEmitter",
    "RegistryWithBus",
    "ProtocolEventBusRegistry",  # New canonical name (omnibase_spi v0.2.0+)
    "ProtocolRegistryWithBus",  # DEPRECATED: Use ProtocolEventBusRegistry instead
    "MixinNodeIntrospection",
    "MixinSensitiveFieldRedaction",
    "MixinSerializable",
    "MixinYAMLSerialization",
    "MixinIntentPublisher",
    # Health check utility functions
    "check_postgresql_health",
    "check_kafka_health",
    "check_redis_health",
    "check_http_service_health",
]
