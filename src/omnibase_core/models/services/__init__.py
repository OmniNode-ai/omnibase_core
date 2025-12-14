"""
Service domain models for ONEX.
"""

from omnibase_core.models.configuration.model_event_bus_config import (
    ModelEventBusConfig,
)
from omnibase_core.models.configuration.model_monitoring_config import (
    ModelMonitoringConfig,
)
from omnibase_core.models.configuration.model_resource_limits import ModelResourceLimits
from omnibase_core.models.examples.model_security_config import ModelSecurityConfig
from omnibase_core.models.health.model_health_check_config import ModelHealthCheckConfig
from omnibase_core.models.operations.model_workflow_parameters import (
    ModelWorkflowParameters,
)

from .model_custom_field_definition import ModelCustomFieldDefinition
from .model_error_details import ModelErrorDetails
from .model_execution_priority import ModelExecutionPriority
from .model_external_service_config import ModelExternalServiceConfig
from .model_network_config import ModelNetworkConfig
from .model_node_service_config import ModelNodeServiceConfig
from .model_node_weights import ModelNodeWeights
from .model_plan import ModelPlan
from .model_retry_strategy import ModelRetryStrategy
from .model_routing_preferences import ModelRoutingPreferences
from .model_service_configuration import EnumFallbackStrategyType, ModelFallbackStrategy
from .model_service_configuration_single import ModelServiceConfiguration
from .model_service_health import ModelServiceHealth
from .model_service_registry_config import ModelServiceRegistryConfig
from .model_service_type import ModelServiceType

# NOTE: Orchestrator models moved to omnibase_core.models.orchestrator (Phase 3)
# from omnibase_core.models.orchestrator.model_orchestrator_output import (
#     ModelOrchestratorOutput,
# )
# from omnibase_core.models.orchestrator.model_orchestrator import (
#     GraphModel,
#     OrchestratorGraphModel,
#     OrchestratorPlanModel,
#     OrchestratorResultModel,
#     PlanModel,
# )
# from omnibase_core.models.orchestrator.model_orchestrator_graph import (
#     ModelOrchestratorGraph,
# )
# from omnibase_core.models.orchestrator.model_orchestrator_plan import (
#     ModelOrchestratorPlan,
# )
# from omnibase_core.models.orchestrator.model_orchestrator_result import (
#     ModelOrchestratorResult,
# )
# from omnibase_core.models.orchestrator.model_orchestrator_step import (
#     ModelOrchestratorStep,
# )


# NOTE: Models have been reorganized (2025-11-13):
# Phase 1:
# - Docker models moved to: omnibase_core.models.docker
#   (ModelDockerBuildConfig, ModelDockerComposeConfig, etc.)
# - Graph models moved to: omnibase_core.models.graph
#   (ModelGraph, ModelGraphEdge, ModelGraphNode)
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
    "ModelCustomFieldDefinition",
    "ModelErrorDetails",
    "ModelEventBusConfig",
    "ModelExecutionPriority",
    "ModelExternalServiceConfig",
    "ModelFallbackStrategy",
    "ModelHealthCheckConfig",
    "ModelMonitoringConfig",
    "ModelNetworkConfig",
    "ModelNodeServiceConfig",
    "ModelNodeWeights",
    "ModelPlan",
    "ModelResourceLimits",
    "ModelRetryStrategy",
    "ModelRoutingPreferences",
    "ModelSecurityConfig",
    "ModelServiceConfiguration",
    "ModelServiceHealth",
    "ModelServiceRegistryConfig",
    "ModelServiceType",
    "ModelWorkflowParameters",
    # NOTE: Orchestrator models moved to omnibase_core.models.orchestrator
    # (GraphModel, ModelOrchestratorGraph, ModelOrchestratorOutput,
    #  ModelOrchestratorPlan, ModelOrchestratorResult, ModelOrchestratorStep,
    #  OrchestratorGraphModel, OrchestratorPlanModel, OrchestratorResultModel, PlanModel)
]
