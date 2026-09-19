# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Canonical delegation wire DTOs (graduated from omnibase_compat, OMN-12126)."""

from omnibase_core.enums.enum_delegation_budget_refusal_reason import (
    EnumDelegationBudgetRefusalReason,
)
from omnibase_core.enums.enum_delegation_output_refusal_reason import (
    EnumDelegationOutputRefusalReason,
)
from omnibase_core.enums.enum_delegation_output_shape import EnumDelegationOutputShape
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
from omnibase_core.models.delegation.wire.model_delegation_budget_evidence import (
    ModelDelegationBudgetEvidence,
)
from omnibase_core.models.delegation.wire.model_delegation_budget_refusal import (
    ModelDelegationBudgetRefusal,
)
from omnibase_core.models.delegation.wire.model_delegation_completed import (
    ModelDelegationCompleted,
)
from omnibase_core.models.delegation.wire.model_delegation_contract_evidence import (
    ModelDelegationContractEvidence,
)
from omnibase_core.models.delegation.wire.model_delegation_deliverable_evidence import (
    ModelDelegationDeliverableEvidence,
)
from omnibase_core.models.delegation.wire.model_delegation_failed import (
    ModelDelegationFailed,
)
from omnibase_core.models.delegation.wire.model_delegation_output_refusal import (
    ModelDelegationOutputRefusal,
)
from omnibase_core.models.delegation.wire.model_delegation_provenance import (
    EnumDelegationTrafficClass,
    ModelDelegationProvenance,
)
from omnibase_core.models.delegation.wire.model_delegation_result import (
    EnumCredentialSource,
    EnumDelegationTerminalFailureCause,
    EnumQualityScoreComparison,
    ModelDelegationResult,
)
from omnibase_core.models.delegation.wire.model_delegation_terminal_v2 import (
    EnumDelegationRoutingDisposition,
    EnumDelegationTerminalOutcome,
    EnumDelegationUnroutedReason,
    ModelDelegationProviderFailureCause,
    ModelDelegationQualityGateRejection,
    ModelDelegationTerminalCompletedV2,
    ModelDelegationTerminalFailedRoutedV2,
    ModelDelegationTerminalFailedUnroutedV2,
    ModelQualityBarEvaluation,
    TypeDelegationRoutedFailureCause,
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
    EnumQualityRuleEnforcement,
    ModelQualityGateInput,
    ModelQualityGateResult,
    ModelQualityRuleEvaluation,
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
    "EnumCredentialSource",
    "EnumDelegationTerminalFailureCause",
    "EnumDelegationTrafficClass",
    "EnumDelegationRoutingDisposition",
    "EnumDelegationOutputShape",
    "EnumDelegationOutputRefusalReason",
    "EnumDelegationBudgetRefusalReason",
    "EnumDelegationTerminalOutcome",
    "EnumDelegationUnroutedReason",
    "EnumQualityContractMode",
    "EnumQualityGateCategory",
    "EnumQualityRuleEnforcement",
    "EnumQualityScoreComparison",
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
    "ModelDelegationBudgetEvidence",
    "ModelDelegationBudgetRefusal",
    "ModelDelegationContractEvidence",
    "ModelDelegationDeliverableEvidence",
    "ModelDelegationOutputRefusal",
    "ModelDelegationRequest",
    "ModelDelegationResult",
    "ModelDelegationProviderFailureCause",
    "ModelDelegationProvenance",
    "ModelDelegationQualityGateRejection",
    "ModelDelegationTerminalCompletedV2",
    "ModelDelegationTerminalFailedRoutedV2",
    "ModelDelegationTerminalFailedUnroutedV2",
    "ModelDelegationRoutingRule",
    "ModelDelegationShadowConfig",
    "ModelInferenceIntent",
    "ModelInferenceResponseData",
    "ModelPremiumCounterfactual",
    "ModelQualityGateInput",
    "ModelQualityGateIntent",
    "ModelQualityGateResult",
    "ModelQualityRuleEvaluation",
    "ModelQualityBarEvaluation",
    "ModelRoutingIntent",
    "ModelRoutingTier",
    "ModelTaskDelegatedEvent",
    "ModelTierCost",
    "ModelTierModel",
    "TypeDelegationRoutedFailureCause",
    "validate_acceptance_criteria",
]
