"""Unknown dependency exception."""

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.error_pipeline import PipelineError


class UnknownDependencyError(PipelineError):
    """Raised when a hook references an unknown dependency."""

    def __init__(self, hook_name: str, unknown_dep: str) -> None:
        super().__init__(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"Hook '{hook_name}' references unknown dependency '{unknown_dep}'",
            context={
                "hook_name": hook_name,
                "unknown_dependency": unknown_dep,
                "validation_kind": "unknown_dependency",
            },
        )


__all__ = ["UnknownDependencyError"]
