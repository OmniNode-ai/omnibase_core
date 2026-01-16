"""Hook timeout exception."""

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.error_pipeline import PipelineError


class HookTimeoutError(PipelineError):
    """Raised when a hook exceeds its configured timeout."""

    def __init__(self, hook_name: str, timeout_seconds: float) -> None:
        super().__init__(
            error_code=EnumCoreErrorCode.TIMEOUT,
            message=f"Hook '{hook_name}' exceeded timeout of {timeout_seconds}s",
            context={
                "hook_name": hook_name,
                "timeout_seconds": timeout_seconds,
            },
        )


__all__ = ["HookTimeoutError"]
