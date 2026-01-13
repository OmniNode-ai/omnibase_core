from .exception_fail_fast import ExceptionFailFastError


class ExceptionContractViolationError(ExceptionFailFastError):
    """Raised when contract requirements are violated."""

    def __init__(self, message: str, contract_field: str):
        # NOTE(OMN-1302): String error code passed to base class. Safe because base validates code.
        super().__init__(
            message,
            "CONTRACT_VIOLATION",
            {"contract_field": contract_field},  # type: ignore[arg-type]
        )
