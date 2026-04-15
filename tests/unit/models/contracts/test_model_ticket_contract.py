# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Unit tests for ModelTicketContract.

TDD tests for OMN-8916: ModelTicketContract Pydantic model + Linear DoD validator.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from omnibase_core.contracts.validators.validate_ticket_contract import (
    validate_ticket_contract,
)
from omnibase_core.contracts.validators.validation_result import ValidationResult
from omnibase_core.models.contracts.ticket.model_linear_ticket_contract import (
    ModelTicketContract,
)

VALID_TICKET = {
    "ticket_id": "OMN-1234",
    "title": "Add foo feature",
    "dod_evidence": [
        {
            "id": "dod-001",
            "description": "Test passes",
            "checks": [
                {
                    "check_type": "test_passes",
                    "check_value": "tests/test_foo.py::test_bar",
                }
            ],
        }
    ],
    "golden_path": "Emit event → handler processes → row in DB",
}


class TestModelTicketContractValidField:
    def test_accepts_valid_ticket(self) -> None:
        contract = ModelTicketContract(**VALID_TICKET)
        assert contract.ticket_id == "OMN-1234"
        assert contract.title == "Add foo feature"
        assert len(contract.dod_evidence) == 1
        assert contract.golden_path == "Emit event → handler processes → row in DB"
        assert contract.runtime_change is False
        assert contract.deploy_step is None

    def test_accepts_valid_ticket_with_runtime_change_and_deploy_step(self) -> None:
        contract = ModelTicketContract(
            **VALID_TICKET,
            runtime_change=True,
            deploy_step="trigger deploy-agent rebuild via Kafka",
        )
        assert contract.runtime_change is True
        assert contract.deploy_step == "trigger deploy-agent rebuild via Kafka"

    def test_ticket_id_regex_rejects_invalid(self) -> None:
        with pytest.raises(ValidationError, match="ticket_id"):
            ModelTicketContract(**{**VALID_TICKET, "ticket_id": "LIN-123"})

    def test_ticket_id_regex_rejects_no_prefix(self) -> None:
        with pytest.raises(ValidationError, match="ticket_id"):
            ModelTicketContract(**{**VALID_TICKET, "ticket_id": "8916"})


class TestModelTicketContractRejectsMissingFields:
    def test_rejects_missing_dod_evidence(self) -> None:
        with pytest.raises(ValidationError):
            ModelTicketContract(
                ticket_id="OMN-1234",
                title="Add foo feature",
                golden_path="Emit event → handler processes → row in DB",
            )

    def test_rejects_empty_dod_evidence(self) -> None:
        with pytest.raises(ValidationError, match="dod_evidence"):
            ModelTicketContract(**{**VALID_TICKET, "dod_evidence": []})

    def test_rejects_missing_golden_path(self) -> None:
        with pytest.raises(ValidationError):
            ModelTicketContract(
                ticket_id="OMN-1234",
                title="Add foo feature",
                dod_evidence=VALID_TICKET["dod_evidence"],
            )

    def test_rejects_empty_golden_path(self) -> None:
        with pytest.raises(ValidationError, match="golden_path"):
            ModelTicketContract(**{**VALID_TICKET, "golden_path": ""})

    def test_rejects_runtime_change_true_without_deploy_step(self) -> None:
        with pytest.raises(ValidationError, match="deploy_step"):
            ModelTicketContract(**{**VALID_TICKET, "runtime_change": True})

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError):
            ModelTicketContract(**{**VALID_TICKET, "unknown_field": "value"})

    def test_is_frozen(self) -> None:
        contract = ModelTicketContract(**VALID_TICKET)
        with pytest.raises((ValidationError, TypeError)):
            contract.title = "mutated"  # type: ignore[misc]


class TestValidateTicketContractFunction:
    def test_returns_valid_for_complete_ticket(self) -> None:
        result = validate_ticket_contract(VALID_TICKET)
        assert isinstance(result, ValidationResult)
        assert result.valid is True
        assert result.errors == []

    def test_returns_invalid_for_empty_dod_evidence(self) -> None:
        result = validate_ticket_contract({**VALID_TICKET, "dod_evidence": []})
        assert result.valid is False
        assert len(result.errors) > 0

    def test_returns_invalid_for_missing_golden_path(self) -> None:
        bad = {k: v for k, v in VALID_TICKET.items() if k != "golden_path"}
        result = validate_ticket_contract(bad)
        assert result.valid is False
        assert len(result.errors) > 0

    def test_returns_invalid_for_runtime_change_without_deploy_step(self) -> None:
        result = validate_ticket_contract({**VALID_TICKET, "runtime_change": True})
        assert result.valid is False
        assert any("deploy_step" in e for e in result.errors)

    def test_error_messages_are_strings(self) -> None:
        result = validate_ticket_contract({**VALID_TICKET, "dod_evidence": []})
        assert all(isinstance(e, str) for e in result.errors)
