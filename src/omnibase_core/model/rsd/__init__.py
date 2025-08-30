#!/usr/bin/env python3
"""
RSD (Risk-Surface-Dependency) Algorithm Models - ONEX Standards Compliant.

Strongly-typed Pydantic models for RSD ticket prioritization algorithm.
"""

from omnibase_core.model.rsd.model_agent_request import ModelAgentRequest
# Contract Model Specialization - 4-Node Architecture
from omnibase_core.model.rsd.model_contract_base import (
    ModelContractBase, ModelLifecycleConfig, ModelPerformanceRequirements,
    ModelValidationRules)
from omnibase_core.model.rsd.model_contract_compute import (
    ModelAlgorithmConfig, ModelAlgorithmFactorConfig, ModelCachingConfig,
    ModelContractCompute, ModelInputValidationConfig,
    ModelOutputTransformationConfig, ModelParallelConfig)
from omnibase_core.model.rsd.model_contract_effect import (
    ModelBackupConfig, ModelContractEffect, ModelExternalServiceConfig,
    ModelIOOperationConfig, ModelRetryConfig, ModelTransactionConfig)
from omnibase_core.model.rsd.model_contract_orchestrator import (
    ModelBranchingConfig, ModelContractOrchestrator,
    ModelEventCoordinationConfig, ModelEventDescriptor,
    ModelEventRegistryConfig, ModelEventSubscription, ModelThunkEmissionConfig,
    ModelWorkflowConfig)
from omnibase_core.model.rsd.model_contract_reducer import (
    ModelAggregationConfig, ModelConflictResolutionConfig,
    ModelContractReducer, ModelMemoryManagementConfig, ModelReductionConfig,
    ModelStreamingConfig)
from omnibase_core.model.rsd.model_event_data import ModelEventData
from omnibase_core.model.rsd.model_factor_detail import ModelFactorDetail
from omnibase_core.model.rsd.model_failure_surface import ModelFailureSurface
from omnibase_core.model.rsd.model_plan_override import ModelPlanOverride
from omnibase_core.model.rsd.model_priority_factor_breakdown import \
    ModelPriorityFactorBreakdown
from omnibase_core.model.rsd.model_rsd_metrics import ModelRSDMetrics
from omnibase_core.model.rsd.model_rsd_prioritization_result import \
    ModelRSDPrioritizationResult
from omnibase_core.model.rsd.model_ticket_cluster import ModelTicketCluster
from omnibase_core.model.rsd.model_ticket_edge import ModelTicketEdge
from omnibase_core.model.rsd.model_ticket_metadata import ModelTicketMetadata
from omnibase_core.model.rsd.model_ticket_node import ModelTicketNode
from omnibase_core.model.rsd.model_trigger_context import ModelTriggerContext

__all__ = [
    # Original RSD Models
    "ModelAgentRequest",
    "ModelEventData",
    "ModelFactorDetail",
    "ModelFailureSurface",
    "ModelPlanOverride",
    "ModelPriorityFactorBreakdown",
    "ModelRSDMetrics",
    "ModelRSDPrioritizationResult",
    "ModelTicketCluster",
    "ModelTicketEdge",
    "ModelTicketMetadata",
    "ModelTicketNode",
    "ModelTriggerContext",
    # Contract Model Specialization - Base
    "ModelContractBase",
    "ModelPerformanceRequirements",
    "ModelLifecycleConfig",
    "ModelValidationRules",
    # Contract Model Specialization - Compute
    "ModelContractCompute",
    "ModelAlgorithmConfig",
    "ModelAlgorithmFactorConfig",
    "ModelParallelConfig",
    "ModelCachingConfig",
    "ModelInputValidationConfig",
    "ModelOutputTransformationConfig",
    # Contract Model Specialization - Effect
    "ModelContractEffect",
    "ModelIOOperationConfig",
    "ModelTransactionConfig",
    "ModelRetryConfig",
    "ModelExternalServiceConfig",
    "ModelBackupConfig",
    # Contract Model Specialization - Reducer
    "ModelContractReducer",
    "ModelReductionConfig",
    "ModelStreamingConfig",
    "ModelConflictResolutionConfig",
    "ModelMemoryManagementConfig",
    "ModelAggregationConfig",
    # Contract Model Specialization - Orchestrator
    "ModelContractOrchestrator",
    "ModelThunkEmissionConfig",
    "ModelWorkflowConfig",
    "ModelBranchingConfig",
    "ModelEventDescriptor",
    "ModelEventSubscription",
    "ModelEventCoordinationConfig",
    "ModelEventRegistryConfig",
]
