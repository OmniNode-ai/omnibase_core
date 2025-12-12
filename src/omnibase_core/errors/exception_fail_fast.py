from datetime import UTC, datetime

from omnibase_core.models.errors.model_fail_fast_details import ModelFailFastDetails


class ExceptionFailFastError(Exception):
    """Base exception for fail-fast scenarios."""

    def __init__(
        self,
        message: str,
        error_code: str = "FAIL_FAST",
        details: ModelFailFastDetails | None = None,
    ) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.details = details or ModelFailFastDetails()
        self.timestamp = datetime.now(UTC)
