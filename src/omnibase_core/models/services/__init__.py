"""
Service domain models for ONEX.

NOTE: Cross-package imports (examples, health, operations, configuration) have been
removed from this __init__.py to prevent circular imports. Import these directly
from their respective packages:
    - ModelSecurityConfig: from omnibase_core.models.examples import ModelSecurityConfig
    - ModelHealthCheckConfig: from omnibase_core.models.health import ModelHealthCheckConfig
    - ModelEventBusConfig: from omnibase_core.models.configuration import ModelEventBusConfig
    - ModelMonitoringConfig: from omnibase_core.models.configuration import ModelMonitoringConfig
    - ModelResourceLimits: from omnibase_core.models.configuration import ModelResourceLimits
    - ModelWorkflowParameters: from omnibase_core.models.operations import ModelWorkflowParameters
"""

from .model_custom_field_definition import ModelCustomFieldDefinition
from .model_error_details import ErrorContext, ModelErrorDetails, TContext
from .model_execution_priority import ModelExecutionPriority
from .model_external_service_config import ModelExternalServiceConfig
from .model_network_config import ModelNetworkConfig
from .model_node_service_config import ModelNodeServiceConfig
from .model_node_weights import ModelNodeWeights
from .model_retry_strategy import ModelRetryStrategy
from .model_routing_preferences import ModelRoutingPreferences
from .model_service_configuration import EnumFallbackStrategyType, ModelFallbackStrategy
from .model_service_configuration_single import ModelServiceConfiguration
from .model_service_health import ModelServiceHealth
from .model_service_registry_config import ModelServiceRegistryConfig
from .model_service_type import ModelServiceType

# NOTE: Models have been reorganized (2025-11-13):
# Phase 1:
# - Docker models moved to: omnibase_core.models.docker
#   (ModelDockerBuildConfig, ModelDockerComposeConfig, etc.)
# - Graph models moved to: omnibase_core.models.graph
#   (ModelGraphEdge, ModelGraphNode, etc.)
#
# Phase 2:
# - Event Bus models moved to: omnibase_core.models.event_bus
#   (ModelEventBusInputState, ModelEventBusOutputState, etc.)
#
# Phase 3:
# - Orchestrator models moved to: omnibase_core.models.orchestrator
#   (ModelOrchestratorGraph, ModelOrchestratorOutput, ModelOrchestratorPlan,
#    ModelOrchestratorResult, ModelOrchestratorStep)
#
# Phase 4:
# - Workflow models moved to: omnibase_core.models.workflow
#   (ModelWorkflowExecutionArgs, ModelWorkflowListResult, ModelWorkflowOutputs,
#    ModelWorkflowStatusResult, ModelWorkflowStopArgs)
#
# Please update your imports to use the new locations.
# Example:
#   OLD: from omnibase_core.models.services import ModelDockerBuildConfig
#   NEW: from omnibase_core.models.docker import ModelDockerBuildConfig
#   OLD: from omnibase_core.models.services import ModelEventBusInputState
#   NEW: from omnibase_core.models.event_bus import ModelEventBusInputState
#   OLD: from omnibase_core.models.services import ModelOrchestratorOutput
#   NEW: from omnibase_core.models.orchestrator import ModelOrchestratorOutput
#   OLD: from omnibase_core.models.services import ModelWorkflowExecutionArgs
#   NEW: from omnibase_core.models.workflow import ModelWorkflowExecutionArgs

__all__ = [
    "EnumFallbackStrategyType",
    "ErrorContext",
    "ModelCustomFieldDefinition",
    "ModelErrorDetails",
    "TContext",
    "ModelExecutionPriority",
    "ModelExternalServiceConfig",
    "ModelFallbackStrategy",
    "ModelNetworkConfig",
    "ModelNodeServiceConfig",
    "ModelNodeWeights",
    "ModelRetryStrategy",
    "ModelRoutingPreferences",
    "ModelServiceConfiguration",
    "ModelServiceHealth",
    "ModelServiceRegistryConfig",
    "ModelServiceType",
]
