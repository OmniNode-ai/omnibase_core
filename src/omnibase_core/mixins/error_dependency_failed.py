from .error_fail_fast import FailFastError


class DependencyFailedError(FailFastError):
    """Raised when a required dependency is not available."""

    def __init__(self, message: str, dependency: str):
        super().__init__(message, "DEPENDENCY_FAILED", {"dependency": dependency})
