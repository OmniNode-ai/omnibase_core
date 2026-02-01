"""Callable not found exception."""

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.error_pipeline import PipelineError


class CallableNotFoundError(PipelineError):
    """Raised when a callable reference is not found in the registry."""

    def __init__(self, callable_ref: str) -> None:
        super().__init__(
            error_code=EnumCoreErrorCode.NOT_FOUND,
            message=f"Callable not found in registry: {callable_ref}",
            context={"callable_ref": callable_ref},
        )


__all__ = ["CallableNotFoundError"]
