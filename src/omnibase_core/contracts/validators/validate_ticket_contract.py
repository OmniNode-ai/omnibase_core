# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
validate_ticket_contract — validate a Linear ticket dict against ModelLinearTicketContract.

OMN-8916
"""

from __future__ import annotations

from pydantic import ValidationError

from omnibase_core.contracts.validators.validation_result import ValidationResult
from omnibase_core.models.contracts.ticket.model_linear_ticket_contract import (
    ModelLinearTicketContract,
)
from omnibase_core.models.ticket.model_contract_dod_item import (
    INTEGRATION_ITEM_RULE,
    is_integration_check_type,
)


def validate_ticket_contract(
    ticket: object, *, require_integration_item: bool = False
) -> ValidationResult:
    """Validate a Linear ticket dict against ModelLinearTicketContract.

    Args:
        ticket: Typed dict from Linear API or test fixture.
        require_integration_item: Refuse a ticket whose dod_evidence has no
            integration item. Default False: a stricter acceptance lands after
            every consumer is compliant, then the default flips in its own PR.

    Returns:
        ValidationResult with valid=True and empty errors on success,
        or valid=False with a list of human-readable error strings on failure.
    """
    try:
        contract = ModelLinearTicketContract.model_validate(ticket)
        has_integration_item = any(
            is_integration_check_type(check.check_type)
            for item in contract.dod_evidence
            for check in item.checks
        )
        if require_integration_item and not has_integration_item:
            return ValidationResult(
                valid=False,
                errors=[
                    f"dod_evidence: {INTEGRATION_ITEM_RULE}: no item carries an "
                    "integration check (behavior_proven, endpoint, lab_receipt "
                    "or runtime_sha_match)"
                ],
            )
        return ValidationResult(valid=True)
    except ValidationError as exc:
        errors = [
            f"{'.'.join(str(loc) for loc in e['loc'])}: {e['msg']}"
            for e in exc.errors()
        ]
        return ValidationResult(valid=False, errors=errors)
    except TypeError as exc:
        return ValidationResult(valid=False, errors=[str(exc)])


__all__ = [
    "INTEGRATION_ITEM_RULE",
    "validate_ticket_contract",
]
