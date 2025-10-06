from typing import List

from pydantic import Field

"""
ONEX Mixin Module

Provides reusable mixin classes for ONEX node patterns.
Mixins follow the single responsibility principle and provide specific capabilities
that can be composed into concrete node implementations.
"""

# Import protocols from omnibase_spi
from omnibase_spi.protocols.types import ProtocolLogEmitter as LogEmitter
from omnibase_spi.protocols.types import ProtocolRegistryWithBus as RegistryWithBus

# Core mixins
from omnibase_core.mixins.mixin_canonical_serialization import (
    MixinCanonicalYAMLSerializer,
)
from omnibase_core.mixins.mixin_cli_handler import MixinCLIHandler

# Models and protocols extracted from mixin_event_bus
from omnibase_core.mixins.mixin_completion_data import MixinCompletionData
from omnibase_core.mixins.mixin_contract_metadata import MixinContractMetadata
from omnibase_core.mixins.mixin_contract_state_reducer import MixinContractStateReducer
from omnibase_core.mixins.mixin_debug_discovery_logging import (
    MixinDebugDiscoveryLogging,
)
from omnibase_core.mixins.mixin_discovery_responder import MixinDiscoveryResponder
from omnibase_core.mixins.mixin_event_bus import MixinEventBus
from omnibase_core.mixins.mixin_event_driven_node import MixinEventDrivenNode
from omnibase_core.mixins.mixin_event_handler import MixinEventHandler
from omnibase_core.mixins.mixin_event_listener import MixinEventListener
from omnibase_core.mixins.mixin_fail_fast import MixinFailFast
from omnibase_core.mixins.mixin_hash_computation import MixinHashComputation
from omnibase_core.mixins.mixin_health_check import MixinHealthCheck
from omnibase_core.mixins.mixin_hybrid_execution import MixinHybridExecution
from omnibase_core.mixins.mixin_introspect_from_contract import (
    MixinIntrospectFromContract,
)
from omnibase_core.mixins.mixin_introspection import NodeIntrospectionMixin
from omnibase_core.mixins.mixin_introspection_publisher import (
    MixinIntrospectionPublisher,
)
from omnibase_core.mixins.mixin_lazy_evaluation import MixinLazyEvaluation
from omnibase_core.mixins.mixin_log_data import MixinLogData
from omnibase_core.mixins.mixin_node_executor import MixinNodeExecutor
from omnibase_core.mixins.mixin_node_id_from_contract import MixinNodeIdFromContract
from omnibase_core.mixins.mixin_node_lifecycle import MixinNodeLifecycle
from omnibase_core.mixins.mixin_node_setup import MixinNodeSetup
from omnibase_core.mixins.mixin_redaction import MixinSensitiveFieldRedaction
from omnibase_core.mixins.mixin_registry_injection import MixinRegistryInjection
from omnibase_core.mixins.mixin_request_response_introspection import (
    MixinRequestResponseIntrospection,
)
from omnibase_core.mixins.mixin_serializable import SerializableMixin
from omnibase_core.mixins.mixin_service_registry import MixinServiceRegistry
from omnibase_core.mixins.mixin_tool_execution import MixinToolExecution
from omnibase_core.mixins.mixin_workflow_support import MixinDagSupport
from omnibase_core.mixins.mixin_yaml_serialization import YAMLSerializationMixin
from omnibase_core.mixins.protocol_event_bus import ProtocolEventBus

__all__ = [
    "MixinCanonicalYAMLSerializer",
    "MixinDiscoveryResponder",
    "MixinHashComputation",
    "MixinCLIHandler",
    "MixinContractMetadata",
    "MixinContractStateReducer",
    "MixinDagSupport",
    "MixinDebugDiscoveryLogging",
    "MixinEventDrivenNode",
    "MixinEventHandler",
    "MixinEventListener",
    "MixinFailFast",
    "MixinHealthCheck",
    "MixinHybridExecution",
    "MixinIntrospectFromContract",
    "MixinIntrospectionPublisher",
    "MixinLazyEvaluation",
    "MixinNodeIdFromContract",
    "MixinNodeLifecycle",
    "MixinNodeExecutor",
    "MixinNodeSetup",
    "MixinRegistryInjection",
    "MixinRequestResponseIntrospection",
    "MixinServiceRegistry",
    "MixinToolExecution",
    "MixinEventBus",
    "MixinCompletionData",
    "MixinLogData",
    "ProtocolEventBus",
    "LogEmitter",
    "RegistryWithBus",
    "NodeIntrospectionMixin",
    "MixinSensitiveFieldRedaction",
    "SerializableMixin",
    "YAMLSerializationMixin",
]
