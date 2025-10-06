from datetime import datetime
from typing import Any


class FailFastError(Exception):
    """Base exception for fail-fast scenarios."""

    def __init__(
        self,
        message: str,
        error_code: str = "FAIL_FAST",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.error_code = error_code
        self.details = details or {}
        self.timestamp = datetime.utcnow()
