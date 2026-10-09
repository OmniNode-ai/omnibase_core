# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Validation models for error tracking and validation results.

Note: Most imports are omitted to avoid circular dependencies with validation module.
Import validation models directly when needed:
    from omnibase_core.models.validation.model_audit_result import ModelAuditResult
    from omnibase_core.models.validation.model_duplication_info import ModelDuplicationInfo
    from omnibase_core.models.validation.model_protocol_signature_extractor import ModelProtocolSignatureExtractor
"""

from __future__ import annotations

# Only import non-circular models (Pydantic models that don't import from validation)
# Contract validation event model (OMN-1146)
# Violation baseline models (OMN-1774)
# Aislop rule models (OMN-11132)
import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .model_aislop_config import ModelAislopConfig
    from .model_aislop_rule import ModelAislopRule
    from .model_aislop_rule_override import ModelAislopRuleOverride
    from .model_aislop_rule_set import ModelAislopRuleSet
    from .model_baseline_generator import ModelBaselineGenerator
    from .model_baseline_violation import ModelBaselineViolation
    from .model_contract_validation_event import (
        ContractValidationEventType,
        ModelContractValidationEvent,
    )

    # Cross-repo validation models (OMN-1771)
    from .model_cross_repo_validation_orchestrator_result import (
        ModelResultCrossRepoValidationOrchestrator,
    )

    # Workflow validation models (OMN-176) - safe to import
    from .model_cycle_detection_result import ModelCycleDetectionResult
    from .model_dependency_validation_result import ModelDependencyValidationResult

    # Event destination model (OMN-1151)
    from .model_event_destination import ModelEventDestination
    from .model_execution_shape import ModelExecutionShape
    from .model_execution_shape_validation import ModelExecutionShapeValidation
    from .model_isolated_step_result import ModelIsolatedStepResult
    from .model_lint_statistics import ModelLintStatistics
    from .model_migration_conflict_union import ModelMigrationConflictUnion
    from .model_node_home_ratchet_finding import ModelNodeHomeRatchetFinding
    from .model_node_home_ratchet_request import ModelNodeHomeRatchetRequest
    from .model_node_home_ratchet_result import ModelNodeHomeRatchetResult
    from .model_rule_configs import (
        ModelRuleAsyncPolicyConfig,
        ModelRuleConfigBase,
        ModelRuleContractSchemaConfig,
        ModelRuleDuplicateProtocolsConfig,
        ModelRuleErrorTaxonomyConfig,
        ModelRuleForbiddenImportsConfig,
        ModelRuleObservabilityConfig,
        ModelRulePartitionKeyConfig,
        ModelRuleRepoBoundariesConfig,
        ModelRuleTopicNamingConfig,
    )
    from .model_shape_validation_result import ModelShapeValidationResult

    # Topic suffix validation models (OMN-1537)
    from .model_topic_suffix_parts import (
        KIND_ABBR_CMD,
        KIND_ABBR_DLQ,
        KIND_ABBR_EVT,
        KIND_ABBR_INTENT,
        KIND_ABBR_SNAPSHOT,
        VALID_TOPIC_KINDS,
        ModelTopicSuffixParts,
    )
    from .model_topic_validation_result import ModelTopicValidationResult
    from .model_unique_name_result import ModelUniqueNameResult
    from .model_validation_base import ModelValidationBase
    from .model_validation_container import ModelValidationContainer
    from .model_validation_discovery_config import ModelValidationDiscoveryConfig
    from .model_validation_error import ModelValidationError
    from .model_validation_policy_contract import ModelValidationPolicyContract
    from .model_validation_value import ModelValidationValue
    from .model_violation_baseline import ModelViolationBaseline
    from .model_violation_waiver import ModelViolationWaiver
    from .model_workflow_validation_result import ModelWorkflowValidationResult

# Note: Other validation models (ModelAuditResult, DuplicationInfo, ProtocolSignatureExtractor, etc.)
# cause circular imports and should be imported directly from their modules when needed

__all__ = [
    # Aislop rule models (OMN-11132)
    "ModelAislopConfig",
    "ModelAislopRule",
    "ModelAislopRuleOverride",
    "ModelAislopRuleSet",
    # Contract validation event model (OMN-1146)
    "ContractValidationEventType",
    "ModelContractValidationEvent",
    # Cross-repo validation models (OMN-1771)
    "ModelResultCrossRepoValidationOrchestrator",
    "ModelValidationDiscoveryConfig",
    "ModelRuleAsyncPolicyConfig",
    "ModelRuleConfigBase",
    "ModelRuleContractSchemaConfig",
    "ModelRuleDuplicateProtocolsConfig",
    "ModelRuleErrorTaxonomyConfig",
    "ModelRuleForbiddenImportsConfig",
    "ModelRuleObservabilityConfig",
    "ModelRulePartitionKeyConfig",
    "ModelRuleRepoBoundariesConfig",
    "ModelRuleTopicNamingConfig",
    "ModelValidationPolicyContract",
    # Violation baseline models (OMN-1774)
    "ModelBaselineGenerator",
    "ModelBaselineViolation",
    "ModelViolationBaseline",
    "ModelViolationWaiver",
    # Event destination model (OMN-1151)
    "ModelEventDestination",
    # Node-home ratchet models (OMN-20702)
    "ModelNodeHomeRatchetFinding",
    "ModelNodeHomeRatchetRequest",
    "ModelNodeHomeRatchetResult",
    # Pydantic models (safe to import)
    "ModelLintStatistics",
    "ModelMigrationConflictUnion",
    "ModelValidationBase",
    "ModelValidationContainer",
    "ModelValidationError",
    "ModelValidationValue",
    # Execution shape validation models (OMN-933)
    "ModelExecutionShape",
    "ModelExecutionShapeValidation",
    "ModelShapeValidationResult",
    # Topic suffix validation models (OMN-1537)
    "ModelTopicSuffixParts",
    "ModelTopicValidationResult",
    "KIND_ABBR_CMD",
    "KIND_ABBR_DLQ",
    "KIND_ABBR_EVT",
    "KIND_ABBR_INTENT",
    "KIND_ABBR_SNAPSHOT",
    "VALID_TOPIC_KINDS",
    # Workflow validation models (OMN-176)
    "ModelCycleDetectionResult",
    "ModelDependencyValidationResult",
    "ModelIsolatedStepResult",
    "ModelUniqueNameResult",
    "ModelWorkflowValidationResult",
    # Utility classes (import directly from their modules to avoid circular imports)
    # "ModelAuditResult",  # from .model_audit_result
    # "ModelContractValidationResult",  # from .model_contract_validation_result
    # "ModelDuplicationInfo",  # from .model_duplication_info
    # "ModelDuplicationReport",  # from .model_duplication_report
    # "ModelMigrationPlan",  # from .model_migration_plan
    # "ModelMigrationResult",  # from .model_migration_result
    # "ModelModuleImportResult",  # from .model_module_import_result
    # "ModelProtocolInfo",  # from .model_protocol_info
    # "ModelProtocolSignatureExtractor",  # from .model_protocol_signature_extractor
    # "ModelUnionPattern",  # from .model_union_pattern
    #
    # Circular Import Detection (dataclass, not Pydantic):
    # "ModelImportValidationResult",  # from .model_import_validation_result
    #     ^-- Aggregates results from circular import validation runs.
    #         Tracks successful imports, circular imports, and errors.
    #         Used by import validation tooling, not general validation.
    #     Note: Renamed from ModelValidationResult to avoid collision with
    #           the generic ModelValidationResult[T] in models/common/.
]


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "ModelAislopConfig": (
        "omnibase_core.models.validation.model_aislop_config",
        "ModelAislopConfig",
    ),
    "ModelAislopRule": (
        "omnibase_core.models.validation.model_aislop_rule",
        "ModelAislopRule",
    ),
    "ModelAislopRuleOverride": (
        "omnibase_core.models.validation.model_aislop_rule_override",
        "ModelAislopRuleOverride",
    ),
    "ModelAislopRuleSet": (
        "omnibase_core.models.validation.model_aislop_rule_set",
        "ModelAislopRuleSet",
    ),
    "ModelBaselineGenerator": (
        "omnibase_core.models.validation.model_baseline_generator",
        "ModelBaselineGenerator",
    ),
    "ModelBaselineViolation": (
        "omnibase_core.models.validation.model_baseline_violation",
        "ModelBaselineViolation",
    ),
    "ContractValidationEventType": (
        "omnibase_core.models.validation.model_contract_validation_event",
        "ContractValidationEventType",
    ),
    "ModelContractValidationEvent": (
        "omnibase_core.models.validation.model_contract_validation_event",
        "ModelContractValidationEvent",
    ),
    "ModelResultCrossRepoValidationOrchestrator": (
        "omnibase_core.models.validation.model_cross_repo_validation_orchestrator_result",
        "ModelResultCrossRepoValidationOrchestrator",
    ),
    "ModelCycleDetectionResult": (
        "omnibase_core.models.validation.model_cycle_detection_result",
        "ModelCycleDetectionResult",
    ),
    "ModelDependencyValidationResult": (
        "omnibase_core.models.validation.model_dependency_validation_result",
        "ModelDependencyValidationResult",
    ),
    "ModelEventDestination": (
        "omnibase_core.models.validation.model_event_destination",
        "ModelEventDestination",
    ),
    "ModelExecutionShape": (
        "omnibase_core.models.validation.model_execution_shape",
        "ModelExecutionShape",
    ),
    "ModelExecutionShapeValidation": (
        "omnibase_core.models.validation.model_execution_shape_validation",
        "ModelExecutionShapeValidation",
    ),
    "ModelIsolatedStepResult": (
        "omnibase_core.models.validation.model_isolated_step_result",
        "ModelIsolatedStepResult",
    ),
    "ModelLintStatistics": (
        "omnibase_core.models.validation.model_lint_statistics",
        "ModelLintStatistics",
    ),
    "ModelMigrationConflictUnion": (
        "omnibase_core.models.validation.model_migration_conflict_union",
        "ModelMigrationConflictUnion",
    ),
    "ModelNodeHomeRatchetFinding": (
        "omnibase_core.models.validation.model_node_home_ratchet_finding",
        "ModelNodeHomeRatchetFinding",
    ),
    "ModelNodeHomeRatchetRequest": (
        "omnibase_core.models.validation.model_node_home_ratchet_request",
        "ModelNodeHomeRatchetRequest",
    ),
    "ModelNodeHomeRatchetResult": (
        "omnibase_core.models.validation.model_node_home_ratchet_result",
        "ModelNodeHomeRatchetResult",
    ),
    "ModelRuleAsyncPolicyConfig": (
        "omnibase_core.models.validation.model_rule_configs",
        "ModelRuleAsyncPolicyConfig",
    ),
    "ModelRuleConfigBase": (
        "omnibase_core.models.validation.model_rule_configs",
        "ModelRuleConfigBase",
    ),
    "ModelRuleContractSchemaConfig": (
        "omnibase_core.models.validation.model_rule_configs",
        "ModelRuleContractSchemaConfig",
    ),
    "ModelRuleDuplicateProtocolsConfig": (
        "omnibase_core.models.validation.model_rule_configs",
        "ModelRuleDuplicateProtocolsConfig",
    ),
    "ModelRuleErrorTaxonomyConfig": (
        "omnibase_core.models.validation.model_rule_configs",
        "ModelRuleErrorTaxonomyConfig",
    ),
    "ModelRuleForbiddenImportsConfig": (
        "omnibase_core.models.validation.model_rule_configs",
        "ModelRuleForbiddenImportsConfig",
    ),
    "ModelRuleObservabilityConfig": (
        "omnibase_core.models.validation.model_rule_configs",
        "ModelRuleObservabilityConfig",
    ),
    "ModelRulePartitionKeyConfig": (
        "omnibase_core.models.validation.model_rule_configs",
        "ModelRulePartitionKeyConfig",
    ),
    "ModelRuleRepoBoundariesConfig": (
        "omnibase_core.models.validation.model_rule_configs",
        "ModelRuleRepoBoundariesConfig",
    ),
    "ModelRuleTopicNamingConfig": (
        "omnibase_core.models.validation.model_rule_configs",
        "ModelRuleTopicNamingConfig",
    ),
    "ModelShapeValidationResult": (
        "omnibase_core.models.validation.model_shape_validation_result",
        "ModelShapeValidationResult",
    ),
    "KIND_ABBR_CMD": (
        "omnibase_core.models.validation.model_topic_suffix_parts",
        "KIND_ABBR_CMD",
    ),
    "KIND_ABBR_DLQ": (
        "omnibase_core.models.validation.model_topic_suffix_parts",
        "KIND_ABBR_DLQ",
    ),
    "KIND_ABBR_EVT": (
        "omnibase_core.models.validation.model_topic_suffix_parts",
        "KIND_ABBR_EVT",
    ),
    "KIND_ABBR_INTENT": (
        "omnibase_core.models.validation.model_topic_suffix_parts",
        "KIND_ABBR_INTENT",
    ),
    "KIND_ABBR_SNAPSHOT": (
        "omnibase_core.models.validation.model_topic_suffix_parts",
        "KIND_ABBR_SNAPSHOT",
    ),
    "VALID_TOPIC_KINDS": (
        "omnibase_core.models.validation.model_topic_suffix_parts",
        "VALID_TOPIC_KINDS",
    ),
    "ModelTopicSuffixParts": (
        "omnibase_core.models.validation.model_topic_suffix_parts",
        "ModelTopicSuffixParts",
    ),
    "ModelTopicValidationResult": (
        "omnibase_core.models.validation.model_topic_validation_result",
        "ModelTopicValidationResult",
    ),
    "ModelUniqueNameResult": (
        "omnibase_core.models.validation.model_unique_name_result",
        "ModelUniqueNameResult",
    ),
    "ModelValidationBase": (
        "omnibase_core.models.validation.model_validation_base",
        "ModelValidationBase",
    ),
    "ModelValidationContainer": (
        "omnibase_core.models.validation.model_validation_container",
        "ModelValidationContainer",
    ),
    "ModelValidationDiscoveryConfig": (
        "omnibase_core.models.validation.model_validation_discovery_config",
        "ModelValidationDiscoveryConfig",
    ),
    "ModelValidationError": (
        "omnibase_core.models.validation.model_validation_error",
        "ModelValidationError",
    ),
    "ModelValidationPolicyContract": (
        "omnibase_core.models.validation.model_validation_policy_contract",
        "ModelValidationPolicyContract",
    ),
    "ModelValidationValue": (
        "omnibase_core.models.validation.model_validation_value",
        "ModelValidationValue",
    ),
    "ModelViolationBaseline": (
        "omnibase_core.models.validation.model_violation_baseline",
        "ModelViolationBaseline",
    ),
    "ModelViolationWaiver": (
        "omnibase_core.models.validation.model_violation_waiver",
        "ModelViolationWaiver",
    ),
    "ModelWorkflowValidationResult": (
        "omnibase_core.models.validation.model_workflow_validation_result",
        "ModelWorkflowValidationResult",
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
