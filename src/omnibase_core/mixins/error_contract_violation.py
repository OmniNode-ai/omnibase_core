from .error_fail_fast import FailFastError


class ContractViolationError(FailFastError):
    """Raised when contract requirements are violated."""

    def __init__(self, message: str, contract_field: str):
        super().__init__(
            message,
            "CONTRACT_VIOLATION",
            {"contract_field": contract_field},
        )
