from typing import Any

from .error_fail_fast import FailFastError


class ValidationFailedError(FailFastError):
    """Raised when validation fails."""

    def __init__(
        self,
        message: str,
        field: str | None = None,
        value: Any = None,
    ):
        details = {}
        if field:
            details["field"] = field
        if value is not None:
            details["value"] = str(value)

        super().__init__(message, "VALIDATION_FAILED", details)
