# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Canonical delegation wire DTOs (graduated from omnibase_compat, OMN-12126)."""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.enums.enum_delegation_budget_refusal_reason import (
        EnumDelegationBudgetRefusalReason,
    )
    from omnibase_core.enums.enum_delegation_content_verdict import (
        EnumDelegationContentVerdict,
    )
    from omnibase_core.enums.enum_delegation_operational_outcome import (
        EnumDelegationOperationalOutcome,
    )
    from omnibase_core.enums.enum_delegation_output_refusal_reason import (
        EnumDelegationOutputRefusalReason,
    )
    from omnibase_core.enums.enum_delegation_output_shape import (
        EnumDelegationOutputShape,
    )
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
    from omnibase_core.models.delegation.wire.model_delegation_dispatch_request import (
        ModelDelegationDispatchRequest,
    )
    from omnibase_core.models.delegation.wire.model_delegation_dispatch_result import (
        ModelDelegationDispatchResult,
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
    from omnibase_core.models.delegation.wire.model_delegation_raw_response import (
        MAX_RAW_RESPONSE_UTF8_BYTES,
        ModelDelegationRawResponse,
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
    "MAX_RAW_RESPONSE_UTF8_BYTES",
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
    "EnumDelegationContentVerdict",
    "EnumDelegationOperationalOutcome",
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
    "ModelDelegationDispatchRequest",
    "ModelDelegationDispatchResult",
    "ModelDelegationEventEnvelope",
    "ModelDelegationFailed",
    "ModelDelegationFailoverConfig",
    "ModelDelegationFallbackPolicy",
    "ModelDelegationBudgetEvidence",
    "ModelDelegationBudgetRefusal",
    "ModelDelegationContractEvidence",
    "ModelDelegationDeliverableEvidence",
    "ModelDelegationRawResponse",
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


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "EnumDelegationBudgetRefusalReason": (
        "omnibase_core.enums.enum_delegation_budget_refusal_reason",
        "EnumDelegationBudgetRefusalReason",
    ),
    "EnumDelegationContentVerdict": (
        "omnibase_core.enums.enum_delegation_content_verdict",
        "EnumDelegationContentVerdict",
    ),
    "EnumDelegationOperationalOutcome": (
        "omnibase_core.enums.enum_delegation_operational_outcome",
        "EnumDelegationOperationalOutcome",
    ),
    "EnumDelegationOutputRefusalReason": (
        "omnibase_core.enums.enum_delegation_output_refusal_reason",
        "EnumDelegationOutputRefusalReason",
    ),
    "EnumDelegationOutputShape": (
        "omnibase_core.enums.enum_delegation_output_shape",
        "EnumDelegationOutputShape",
    ),
    "ModelBifrostDelegationConfig": (
        "omnibase_core.models.delegation.wire.model_bifrost_delegation_config",
        "ModelBifrostDelegationConfig",
    ),
    "ModelDelegationBackendConfig": (
        "omnibase_core.models.delegation.wire.model_bifrost_delegation_config",
        "ModelDelegationBackendConfig",
    ),
    "ModelDelegationCircuitBreakerConfig": (
        "omnibase_core.models.delegation.wire.model_bifrost_delegation_config",
        "ModelDelegationCircuitBreakerConfig",
    ),
    "ModelDelegationFailoverConfig": (
        "omnibase_core.models.delegation.wire.model_bifrost_delegation_config",
        "ModelDelegationFailoverConfig",
    ),
    "ModelDelegationFallbackPolicy": (
        "omnibase_core.models.delegation.wire.model_bifrost_delegation_config",
        "ModelDelegationFallbackPolicy",
    ),
    "ModelDelegationRoutingRule": (
        "omnibase_core.models.delegation.wire.model_bifrost_delegation_config",
        "ModelDelegationRoutingRule",
    ),
    "ModelDelegationShadowConfig": (
        "omnibase_core.models.delegation.wire.model_bifrost_delegation_config",
        "ModelDelegationShadowConfig",
    ),
    "EnumBudgetAction": (
        "omnibase_core.models.delegation.wire.model_budget",
        "EnumBudgetAction",
    ),
    "ModelBudgetLimits": (
        "omnibase_core.models.delegation.wire.model_budget",
        "ModelBudgetLimits",
    ),
    "ModelDelegationBudgetEvidence": (
        "omnibase_core.models.delegation.wire.model_delegation_budget_evidence",
        "ModelDelegationBudgetEvidence",
    ),
    "ModelDelegationBudgetRefusal": (
        "omnibase_core.models.delegation.wire.model_delegation_budget_refusal",
        "ModelDelegationBudgetRefusal",
    ),
    "ModelDelegationCompleted": (
        "omnibase_core.models.delegation.wire.model_delegation_completed",
        "ModelDelegationCompleted",
    ),
    "ModelDelegationContractEvidence": (
        "omnibase_core.models.delegation.wire.model_delegation_contract_evidence",
        "ModelDelegationContractEvidence",
    ),
    "ModelDelegationDeliverableEvidence": (
        "omnibase_core.models.delegation.wire.model_delegation_deliverable_evidence",
        "ModelDelegationDeliverableEvidence",
    ),
    "ModelDelegationDispatchRequest": (
        "omnibase_core.models.delegation.wire.model_delegation_dispatch_request",
        "ModelDelegationDispatchRequest",
    ),
    "ModelDelegationDispatchResult": (
        "omnibase_core.models.delegation.wire.model_delegation_dispatch_result",
        "ModelDelegationDispatchResult",
    ),
    "ModelDelegationFailed": (
        "omnibase_core.models.delegation.wire.model_delegation_failed",
        "ModelDelegationFailed",
    ),
    "ModelDelegationOutputRefusal": (
        "omnibase_core.models.delegation.wire.model_delegation_output_refusal",
        "ModelDelegationOutputRefusal",
    ),
    "EnumDelegationTrafficClass": (
        "omnibase_core.models.delegation.wire.model_delegation_provenance",
        "EnumDelegationTrafficClass",
    ),
    "ModelDelegationProvenance": (
        "omnibase_core.models.delegation.wire.model_delegation_provenance",
        "ModelDelegationProvenance",
    ),
    "MAX_RAW_RESPONSE_UTF8_BYTES": (
        "omnibase_core.models.delegation.wire.model_delegation_raw_response",
        "MAX_RAW_RESPONSE_UTF8_BYTES",
    ),
    "ModelDelegationRawResponse": (
        "omnibase_core.models.delegation.wire.model_delegation_raw_response",
        "ModelDelegationRawResponse",
    ),
    "EnumCredentialSource": (
        "omnibase_core.models.delegation.wire.model_delegation_result",
        "EnumCredentialSource",
    ),
    "EnumDelegationTerminalFailureCause": (
        "omnibase_core.models.delegation.wire.model_delegation_result",
        "EnumDelegationTerminalFailureCause",
    ),
    "EnumQualityScoreComparison": (
        "omnibase_core.models.delegation.wire.model_delegation_result",
        "EnumQualityScoreComparison",
    ),
    "ModelDelegationResult": (
        "omnibase_core.models.delegation.wire.model_delegation_result",
        "ModelDelegationResult",
    ),
    "EnumDelegationRoutingDisposition": (
        "omnibase_core.models.delegation.wire.model_delegation_terminal_v2",
        "EnumDelegationRoutingDisposition",
    ),
    "EnumDelegationTerminalOutcome": (
        "omnibase_core.models.delegation.wire.model_delegation_terminal_v2",
        "EnumDelegationTerminalOutcome",
    ),
    "EnumDelegationUnroutedReason": (
        "omnibase_core.models.delegation.wire.model_delegation_terminal_v2",
        "EnumDelegationUnroutedReason",
    ),
    "ModelDelegationProviderFailureCause": (
        "omnibase_core.models.delegation.wire.model_delegation_terminal_v2",
        "ModelDelegationProviderFailureCause",
    ),
    "ModelDelegationQualityGateRejection": (
        "omnibase_core.models.delegation.wire.model_delegation_terminal_v2",
        "ModelDelegationQualityGateRejection",
    ),
    "ModelDelegationTerminalCompletedV2": (
        "omnibase_core.models.delegation.wire.model_delegation_terminal_v2",
        "ModelDelegationTerminalCompletedV2",
    ),
    "ModelDelegationTerminalFailedRoutedV2": (
        "omnibase_core.models.delegation.wire.model_delegation_terminal_v2",
        "ModelDelegationTerminalFailedRoutedV2",
    ),
    "ModelDelegationTerminalFailedUnroutedV2": (
        "omnibase_core.models.delegation.wire.model_delegation_terminal_v2",
        "ModelDelegationTerminalFailedUnroutedV2",
    ),
    "ModelQualityBarEvaluation": (
        "omnibase_core.models.delegation.wire.model_delegation_terminal_v2",
        "ModelQualityBarEvaluation",
    ),
    "TypeDelegationRoutedFailureCause": (
        "omnibase_core.models.delegation.wire.model_delegation_terminal_v2",
        "TypeDelegationRoutedFailureCause",
    ),
    "ModelDelegationEventEnvelope": (
        "omnibase_core.models.delegation.wire.model_delegation_wire_envelope",
        "ModelDelegationEventEnvelope",
    ),
    "MAX_WORDS_PER_SENTENCE_RE": (
        "omnibase_core.models.delegation.wire.model_delegation_wire_request",
        "MAX_WORDS_PER_SENTENCE_RE",
    ),
    "SUPPORTED_ACCEPTANCE_CRITERIA": (
        "omnibase_core.models.delegation.wire.model_delegation_wire_request",
        "SUPPORTED_ACCEPTANCE_CRITERIA",
    ),
    "EnumQualityContractMode": (
        "omnibase_core.models.delegation.wire.model_delegation_wire_request",
        "EnumQualityContractMode",
    ),
    "ModelDelegationRequest": (
        "omnibase_core.models.delegation.wire.model_delegation_wire_request",
        "ModelDelegationRequest",
    ),
    "validate_acceptance_criteria": (
        "omnibase_core.models.delegation.wire.model_delegation_wire_request",
        "validate_acceptance_criteria",
    ),
    "ModelBaselineIntent": (
        "omnibase_core.models.delegation.wire.model_orchestrator_intents",
        "ModelBaselineIntent",
    ),
    "ModelComplianceLoopResult": (
        "omnibase_core.models.delegation.wire.model_orchestrator_intents",
        "ModelComplianceLoopResult",
    ),
    "ModelInferenceIntent": (
        "omnibase_core.models.delegation.wire.model_orchestrator_intents",
        "ModelInferenceIntent",
    ),
    "ModelInferenceResponseData": (
        "omnibase_core.models.delegation.wire.model_orchestrator_intents",
        "ModelInferenceResponseData",
    ),
    "ModelQualityGateIntent": (
        "omnibase_core.models.delegation.wire.model_orchestrator_intents",
        "ModelQualityGateIntent",
    ),
    "ModelRoutingIntent": (
        "omnibase_core.models.delegation.wire.model_orchestrator_intents",
        "ModelRoutingIntent",
    ),
    "ModelPremiumCounterfactual": (
        "omnibase_core.models.delegation.wire.model_premium_counterfactual",
        "ModelPremiumCounterfactual",
    ),
    "EnumQualityGateCategory": (
        "omnibase_core.models.delegation.wire.model_quality_gate",
        "EnumQualityGateCategory",
    ),
    "EnumQualityRuleEnforcement": (
        "omnibase_core.models.delegation.wire.model_quality_gate",
        "EnumQualityRuleEnforcement",
    ),
    "ModelQualityGateInput": (
        "omnibase_core.models.delegation.wire.model_quality_gate",
        "ModelQualityGateInput",
    ),
    "ModelQualityGateResult": (
        "omnibase_core.models.delegation.wire.model_quality_gate",
        "ModelQualityGateResult",
    ),
    "ModelQualityRuleEvaluation": (
        "omnibase_core.models.delegation.wire.model_quality_gate",
        "ModelQualityRuleEvaluation",
    ),
    "EnumTierCostType": (
        "omnibase_core.models.delegation.wire.model_routing_config",
        "EnumTierCostType",
    ),
    "ModelDelegationConfig": (
        "omnibase_core.models.delegation.wire.model_routing_config",
        "ModelDelegationConfig",
    ),
    "ModelRoutingTier": (
        "omnibase_core.models.delegation.wire.model_routing_config",
        "ModelRoutingTier",
    ),
    "ModelTierCost": (
        "omnibase_core.models.delegation.wire.model_routing_config",
        "ModelTierCost",
    ),
    "ModelTierModel": (
        "omnibase_core.models.delegation.wire.model_routing_config",
        "ModelTierModel",
    ),
    "TASK_DELEGATED_TOPIC_V1": (
        "omnibase_core.models.delegation.wire.model_task_delegated_event",
        "TASK_DELEGATED_TOPIC_V1",
    ),
    "ModelTaskDelegatedEvent": (
        "omnibase_core.models.delegation.wire.model_task_delegated_event",
        "ModelTaskDelegatedEvent",
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
