from .exception_fail_fast import ExceptionFailFast


class ExceptionContractViolation(ExceptionFailFast):
    """Raised when contract requirements are violated."""

    def __init__(self, message: str, contract_field: str):
        super().__init__(
            message,
            "CONTRACT_VIOLATION",
            {"contract_field": contract_field},
        )
