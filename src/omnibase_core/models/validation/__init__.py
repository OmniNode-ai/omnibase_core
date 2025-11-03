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
from .model_migration_conflict_union import ModelMigrationConflictUnion
from .model_validation_base import ModelValidationBase
from .model_validation_container import ModelValidationContainer
from .model_validation_error import ModelValidationError
from .model_validation_value import ModelValidationValue

# Note: Other validation models (ModelAuditResult, DuplicationInfo, ProtocolSignatureExtractor, etc.)
# cause circular imports and should be imported directly from their modules when needed

__all__ = [
    # Pydantic models (safe to import)
    "ModelMigrationConflictUnion",
    "ModelValidationBase",
    "ModelValidationContainer",
    "ModelValidationError",
    "ModelValidationValue",
    # Utility classes (import directly from their modules to avoid circular imports)
    # "ModelAuditResult",  # from .model_audit_result
    # "ModelContractValidationResult",  # from .model_contract_validation_result
    # "ModelDuplicationInfo",  # from .model_duplication_info
    # "ModelDuplicationReport",  # from .model_duplication_report
    # "ModelMigrationPlan",  # from .model_migration_plan
    # "ModelMigrationResult",  # from .model_migration_result
    # "ModelProtocolInfo",  # from .model_protocol_info
    # "ModelProtocolSignatureExtractor",  # from .model_protocol_signature_extractor
    # "ModelUnionPattern",  # from .model_union_pattern
    # "ModelValidationResult",  # from .model_validation_result
]
