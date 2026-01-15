from typing import Any

from omnibase_core.errors.exception_fail_fast import ExceptionFailFastError


class ExceptionValidationFailedError(ExceptionFailFastError):
    """Raised when validation fails."""

    def __init__(
        self,
        message: str,
        field: str | None = None,
        value: Any = None,
    ) -> None:
        details = {}
        if field:
            details["field"] = field
        if value is not None:
            details["value"] = str(value)

        # NOTE(OMN-1302): String error code passed to base class. Safe because base validates code.
        super().__init__(message, "VALIDATION_FAILED", details)  # type: ignore[arg-type]
