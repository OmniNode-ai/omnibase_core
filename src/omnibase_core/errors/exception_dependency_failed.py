from .exception_fail_fast import ExceptionFailFastError


class ExceptionDependencyFailedError(ExceptionFailFastError):
    """Raised when a required dependency is not available."""

    def __init__(self, message: str, dependency: str):
        # NOTE(OMN-1302): String error code passed to base class. Safe because base validates code.
        super().__init__(message, "DEPENDENCY_FAILED", {"dependency": dependency})  # type: ignore[arg-type]
