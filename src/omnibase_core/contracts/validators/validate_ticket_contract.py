# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
validate_ticket_contract — validate a Linear ticket dict against ModelLinearTicketContract.

OMN-8916
"""

from __future__ import annotations

from collections.abc import Sequence

from pydantic import ValidationError

from omnibase_core.contracts.validators.validation_result import ValidationResult
from omnibase_core.enums.ticket.enum_dod_check_type import EnumDodCheckType
from omnibase_core.models.contracts.ticket.model_dod_evidence_item import (
    ModelDodEvidenceItem,
)
from omnibase_core.models.contracts.ticket.model_linear_ticket_contract import (
    ModelLinearTicketContract,
)

# OMN-22969. The integration item: a DoD evidence item with at least one check
# observed against a running system (a live behavior probe, an endpoint, a lab
# receipt or a deployed-SHA match), as opposed to a test that only reads source.
INTEGRATION_ITEM_RULE = "DOD_EVIDENCE_INTEGRATION_ITEM_MISSING"
INTEGRATION_CHECK_TYPES: frozenset[EnumDodCheckType] = frozenset(
    {
        EnumDodCheckType.BEHAVIOR_PROVEN,
        EnumDodCheckType.ENDPOINT,
        EnumDodCheckType.LAB_RECEIPT,
        EnumDodCheckType.RUNTIME_SHA_MATCH,
    }
)


def has_integration_item(dod_evidence: Sequence[ModelDodEvidenceItem]) -> bool:
    """True when any DoD evidence item carries an integration check."""
    return any(
        check.check_type in INTEGRATION_CHECK_TYPES
        for item in dod_evidence
        for check in item.checks
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
        if require_integration_item and not has_integration_item(contract.dod_evidence):
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
    "INTEGRATION_CHECK_TYPES",
    "INTEGRATION_ITEM_RULE",
    "has_integration_item",
    "validate_ticket_contract",
]
