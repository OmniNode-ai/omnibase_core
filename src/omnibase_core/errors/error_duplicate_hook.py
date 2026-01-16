"""Duplicate hook exception."""

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.error_pipeline import PipelineError


class DuplicateHookError(PipelineError):
    """Raised when registering a hook with duplicate name."""

    def __init__(self, hook_name: str) -> None:
        super().__init__(
            error_code=EnumCoreErrorCode.DUPLICATE_REGISTRATION,
            message=f"Hook with name '{hook_name}' already registered",
            context={"hook_name": hook_name},
        )


__all__ = ["DuplicateHookError"]
