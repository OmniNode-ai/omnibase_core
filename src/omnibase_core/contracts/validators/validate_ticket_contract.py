# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
validate_ticket_contract — validate a Linear ticket dict against ModelTicketContract.

OMN-8916
"""

from __future__ import annotations

from pydantic import ValidationError

from omnibase_core.contracts.validators.validation_result import ValidationResult
from omnibase_core.models.contracts.ticket.model_linear_ticket_contract import (
    ModelTicketContract,
)


def validate_ticket_contract(ticket: object) -> ValidationResult:
    """Validate a Linear ticket dict against ModelTicketContract.

    Args:
        ticket: Typed dict from Linear API or test fixture.

    Returns:
        ValidationResult with valid=True and empty errors on success,
        or valid=False with a list of human-readable error strings on failure.
    """
    try:
        ModelTicketContract.model_validate(ticket)
        return ValidationResult(valid=True)
    except ValidationError as exc:
        errors = [
            f"{'.'.join(str(loc) for loc in e['loc'])}: {e['msg']}"
            for e in exc.errors()
        ]
        return ValidationResult(valid=False, errors=errors)
    except TypeError as exc:
        return ValidationResult(valid=False, errors=[str(exc)])


__all__ = ["validate_ticket_contract"]
