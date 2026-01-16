"""Hook type mismatch exception."""

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.error_pipeline import PipelineError


class HookTypeMismatchError(PipelineError):
    """Raised when hook type doesn't match contract type (when enforced)."""

    def __init__(
        self, hook_name: str, hook_category: str, contract_category: str
    ) -> None:
        super().__init__(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"Hook '{hook_name}' category '{hook_category}' doesn't match contract category '{contract_category}'",
            context={
                "hook_name": hook_name,
                "hook_category": hook_category,
                "contract_category": contract_category,
                "validation_kind": "hook_type_mismatch",
            },
        )


__all__ = ["HookTypeMismatchError"]
