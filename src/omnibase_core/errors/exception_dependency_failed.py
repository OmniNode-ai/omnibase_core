from .exception_fail_fast import ExceptionFailFast


class ExceptionDependencyFailed(ExceptionFailFast):
    """Raised when a required dependency is not available."""

    def __init__(self, message: str, dependency: str):
        super().__init__(message, "DEPENDENCY_FAILED", {"dependency": dependency})
