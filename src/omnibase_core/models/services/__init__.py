# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

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

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .model_custom_field_definition import ModelCustomFieldDefinition
    from .model_execution_priority import ModelExecutionPriority
    from .model_external_service_config import ModelExternalServiceConfig
    from .model_network_config import ModelNetworkConfig
    from .model_node_service_config import ModelNodeServiceConfig
    from .model_node_weights import ModelNodeWeights
    from .model_retry_strategy import ModelRetryStrategy
    from .model_routing_preferences import ModelRoutingPreferences
    from .model_service_configuration import (
        EnumFallbackStrategyType,
        ModelFallbackStrategy,
    )
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
# Phase 5 (OMN-3210 import-layering burn-down, OMN-14291):
# - Node + mixin service-wrapper classes moved to: omnibase_core.nodes
#   (ModelServiceCompute, ModelServiceEffect, ModelServiceOrchestrator,
#    ModelServiceReducer) — these subclass Node* base classes and were never
#    domain models; keeping them under models/ created a models -> nodes
#    import-layering back-edge (.importlinter core-models-no-upward).
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


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "ModelCustomFieldDefinition": (
        "omnibase_core.models.services.model_custom_field_definition",
        "ModelCustomFieldDefinition",
    ),
    "ModelExecutionPriority": (
        "omnibase_core.models.services.model_execution_priority",
        "ModelExecutionPriority",
    ),
    "ModelExternalServiceConfig": (
        "omnibase_core.models.services.model_external_service_config",
        "ModelExternalServiceConfig",
    ),
    "ModelNetworkConfig": (
        "omnibase_core.models.services.model_network_config",
        "ModelNetworkConfig",
    ),
    "ModelNodeServiceConfig": (
        "omnibase_core.models.services.model_node_service_config",
        "ModelNodeServiceConfig",
    ),
    "ModelNodeWeights": (
        "omnibase_core.models.services.model_node_weights",
        "ModelNodeWeights",
    ),
    "ModelRetryStrategy": (
        "omnibase_core.models.services.model_retry_strategy",
        "ModelRetryStrategy",
    ),
    "ModelRoutingPreferences": (
        "omnibase_core.models.services.model_routing_preferences",
        "ModelRoutingPreferences",
    ),
    "EnumFallbackStrategyType": (
        "omnibase_core.models.services.model_service_configuration",
        "EnumFallbackStrategyType",
    ),
    "ModelFallbackStrategy": (
        "omnibase_core.models.services.model_service_configuration",
        "ModelFallbackStrategy",
    ),
    "ModelServiceConfiguration": (
        "omnibase_core.models.services.model_service_configuration_single",
        "ModelServiceConfiguration",
    ),
    "ModelServiceHealth": (
        "omnibase_core.models.services.model_service_health",
        "ModelServiceHealth",
    ),
    "ModelServiceRegistryConfig": (
        "omnibase_core.models.services.model_service_registry_config",
        "ModelServiceRegistryConfig",
    ),
    "ModelServiceType": (
        "omnibase_core.models.services.model_service_type",
        "ModelServiceType",
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
