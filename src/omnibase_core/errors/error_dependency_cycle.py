"""Dependency cycle exception."""

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.error_pipeline import PipelineError


class DependencyCycleError(PipelineError):
    """Raised when hook dependencies form a cycle."""

    def __init__(self, cycle: list[str]) -> None:
        super().__init__(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"Dependency cycle detected: {' -> '.join(cycle)}",
            context={"cycle": cycle, "validation_kind": "dependency_cycle"},
        )


__all__ = ["DependencyCycleError"]
