"""
Validation models for error tracking and validation results.

Note: Most imports are omitted to avoid circular dependencies with validation module.
Import validation models directly when needed:
    from omnibase_core.models.validation.model_audit_result import ModelAuditResult
    from omnibase_core.models.validation.model_duplication_info import ModelDuplicationInfo
    from omnibase_core.models.validation.model_protocol_signature_extractor import ModelProtocolSignatureExtractor
"""

# Only import non-circular models (Pydantic models that don't import from validation)
# Contract validation event model (OMN-1146)
from .model_contract_validation_event import (
    ContractValidationEventType,
    ModelContractValidationEvent,
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
from .model_shape_validation_result import ModelShapeValidationResult

# Topic suffix validation models (OMN-1537)
from .model_topic_suffix_parts import (
    TOPIC_KIND_CMD,
    TOPIC_KIND_DLQ,
    TOPIC_KIND_EVT,
    TOPIC_KIND_INTENT,
    TOPIC_KIND_SNAPSHOT,
    VALID_TOPIC_KINDS,
    ModelTopicSuffixParts,
)
from .model_topic_validation_result import ModelTopicValidationResult
from .model_unique_name_result import ModelUniqueNameResult
from .model_validation_base import ModelValidationBase
from .model_validation_container import ModelValidationContainer
from .model_validation_error import ModelValidationError
from .model_validation_value import ModelValidationValue
from .model_workflow_validation_result import ModelWorkflowValidationResult

# Note: Other validation models (ModelAuditResult, DuplicationInfo, ProtocolSignatureExtractor, etc.)
# cause circular imports and should be imported directly from their modules when needed

__all__ = [
    # Contract validation event model (OMN-1146)
    "ContractValidationEventType",
    "ModelContractValidationEvent",
    # Event destination model (OMN-1151)
    "ModelEventDestination",
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
    "TOPIC_KIND_CMD",
    "TOPIC_KIND_DLQ",
    "TOPIC_KIND_EVT",
    "TOPIC_KIND_INTENT",
    "TOPIC_KIND_SNAPSHOT",
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
