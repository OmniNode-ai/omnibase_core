# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""A ticket contract without the integration item is refused (OMN-22969)."""

from __future__ import annotations

import copy

import pytest

from omnibase_core.contracts.validators.validate_ticket_contract import (
    INTEGRATION_ITEM_RULE,
    validate_ticket_contract,
)

_UNIT_DOD_EVIDENCE: list[dict[str, object]] = [
    {
        "id": "dod-001",
        "description": "Unit test passes",
        "checks": [{"check_type": "test_passes", "check_value": "tests/test_foo.py"}],
    }
]
_UNIT_ONLY: dict[str, object] = {
    "ticket_id": "OMN-22969",
    "title": "Unit-only ticket",
    "dod_evidence": _UNIT_DOD_EVIDENCE,
    "golden_path": "Emit event, handler processes, row in DB",
}


def _with_integration_item() -> dict[str, object]:
    ticket = copy.deepcopy(_UNIT_ONLY)
    ticket["dod_evidence"] = [
        *_UNIT_DOD_EVIDENCE,
        {
            "id": "dod-002",
            "description": "Observed on a running system",
            "checks": [{"check_type": "endpoint", "check_value": "http://host/health"}],
        },
    ]
    return ticket


@pytest.mark.unit
def test_contract_without_integration_item_is_refused() -> None:
    result = validate_ticket_contract(_UNIT_ONLY, require_integration_item=True)
    assert result.valid is False
    assert any(INTEGRATION_ITEM_RULE in e for e in result.errors)


@pytest.mark.unit
def test_contract_with_integration_item_is_accepted() -> None:
    result = validate_ticket_contract(
        _with_integration_item(), require_integration_item=True
    )
    assert result.valid is True
    assert result.errors == []


@pytest.mark.unit
def test_default_does_not_require_integration_item() -> None:
    """Strict mode lands behind the parameter until consumers comply."""
    assert validate_ticket_contract(_UNIT_ONLY).valid is True
