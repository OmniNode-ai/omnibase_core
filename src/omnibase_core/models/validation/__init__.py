from typing import Union

"""
Validation models for error tracking and validation results.

Note: Most imports are omitted to avoid circular dependencies with validation module.
Import validation models directly when needed:
    from omnibase_core.models.validation.model_audit_result import ModelAuditResult
    from omnibase_core.models.validation.model_duplication_info import ModelDuplicationInfo
    from omnibase_core.models.validation.model_protocol_signature_extractor import ModelProtocolSignatureExtractor
"""

# Only import non-circular models (Pydantic models that don't import from validation)
# Workflow validation models (OMN-176) - safe to import
from .model_cycle_detection_result import ModelCycleDetectionResult
from .model_dependency_validation_result import ModelDependencyValidationResult
from .model_isolated_step_result import ModelIsolatedStepResult
from .model_lint_statistics import ModelLintStatistics
from .model_migration_conflict_union import ModelMigrationConflictUnion
from .model_unique_name_result import ModelUniqueNameResult
from .model_validation_base import ModelValidationBase
from .model_validation_container import ModelValidationContainer
from .model_validation_error import ModelValidationError
from .model_validation_value import ModelValidationValue
from .model_workflow_validation_result import ModelWorkflowValidationResult

# Note: Other validation models (ModelAuditResult, DuplicationInfo, ProtocolSignatureExtractor, etc.)
# cause circular imports and should be imported directly from their modules when needed

__all__ = [
    # Pydantic models (safe to import)
    "ModelLintStatistics",
    "ModelMigrationConflictUnion",
    "ModelValidationBase",
    "ModelValidationContainer",
    "ModelValidationError",
    "ModelValidationValue",
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
    # "ModelValidationResult",  # from .model_import_validation_result
    #     ^-- Aggregates results from circular import validation runs.
    #         Tracks successful imports, circular imports, and errors.
    #         Used by import validation tooling, not general validation.
]
