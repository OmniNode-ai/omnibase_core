# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Canonical delegation wire DTOs (graduated from omnibase_compat, OMN-12126)."""

from omnibase_core.models.delegation.wire.model_bifrost_delegation_config import (
    ModelBifrostDelegationConfig,
    ModelDelegationBackendConfig,
    ModelDelegationCircuitBreakerConfig,
    ModelDelegationFailoverConfig,
    ModelDelegationFallbackPolicy,
    ModelDelegationRoutingRule,
    ModelDelegationShadowConfig,
)
from omnibase_core.models.delegation.wire.model_budget import (
    EnumBudgetAction,
    ModelBudgetLimits,
)
from omnibase_core.models.delegation.wire.model_delegation_result import (
    ModelDelegationCompleted,
    ModelDelegationFailed,
    ModelDelegationResult,
)
from omnibase_core.models.delegation.wire.model_delegation_wire_envelope import (
    ModelDelegationEventEnvelope,
)
from omnibase_core.models.delegation.wire.model_delegation_wire_request import (
    MAX_WORDS_PER_SENTENCE_RE,
    SUPPORTED_ACCEPTANCE_CRITERIA,
    EnumQualityContractMode,
    ModelDelegationRequest,
    validate_acceptance_criteria,
)
from omnibase_core.models.delegation.wire.model_orchestrator_intents import (
    ModelBaselineIntent,
    ModelComplianceLoopResult,
    ModelInferenceIntent,
    ModelInferenceResponseData,
    ModelQualityGateIntent,
    ModelRoutingIntent,
)
from omnibase_core.models.delegation.wire.model_premium_counterfactual import (
    ModelPremiumCounterfactual,
)
from omnibase_core.models.delegation.wire.model_quality_gate import (
    EnumQualityGateCategory,
    ModelQualityGateInput,
    ModelQualityGateResult,
)
from omnibase_core.models.delegation.wire.model_routing_config import (
    EnumTierCostType,
    ModelDelegationConfig,
    ModelRoutingTier,
    ModelTierCost,
    ModelTierModel,
)
from omnibase_core.models.delegation.wire.model_task_delegated_event import (
    TASK_DELEGATED_TOPIC_V1,
    ModelTaskDelegatedEvent,
)

__all__: list[str] = [
    "MAX_WORDS_PER_SENTENCE_RE",
    "SUPPORTED_ACCEPTANCE_CRITERIA",
    "TASK_DELEGATED_TOPIC_V1",
    "EnumBudgetAction",
    "EnumQualityContractMode",
    "EnumQualityGateCategory",
    "EnumTierCostType",
    "ModelBaselineIntent",
    "ModelBifrostDelegationConfig",
    "ModelBudgetLimits",
    "ModelComplianceLoopResult",
    "ModelDelegationBackendConfig",
    "ModelDelegationCircuitBreakerConfig",
    "ModelDelegationCompleted",
    "ModelDelegationConfig",
    "ModelDelegationEventEnvelope",
    "ModelDelegationFailed",
    "ModelDelegationFailoverConfig",
    "ModelDelegationFallbackPolicy",
    "ModelDelegationRequest",
    "ModelDelegationResult",
    "ModelDelegationRoutingRule",
    "ModelDelegationShadowConfig",
    "ModelInferenceIntent",
    "ModelInferenceResponseData",
    "ModelPremiumCounterfactual",
    "ModelQualityGateInput",
    "ModelQualityGateIntent",
    "ModelQualityGateResult",
    "ModelRoutingIntent",
    "ModelRoutingTier",
    "ModelTaskDelegatedEvent",
    "ModelTierCost",
    "ModelTierModel",
    "validate_acceptance_criteria",
]
