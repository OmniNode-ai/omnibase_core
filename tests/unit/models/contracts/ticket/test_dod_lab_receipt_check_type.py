# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The typed lab_receipt DoD check type of the ticket contract model (OMN-21831)."""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from omnibase_core.enums.ticket.enum_dod_check_type import EnumDodCheckType
from omnibase_core.models.contracts.ticket.model_dod_evidence_check import (
    ModelDodEvidenceCheck,
)
from omnibase_core.models.ticket.model_contract_dod_item import ModelContractDodItem

pytestmark = pytest.mark.unit

SHAPE = {
    "installer": "onex-host-install",
    "observation": "the unit's next tick fired and printed its output line",
}


def test_lab_receipt_check_type_is_a_member_of_the_check_type_enum() -> None:
    assert EnumDodCheckType("lab_receipt") is EnumDodCheckType.LAB_RECEIPT


def test_lab_receipt_check_type_accepts_the_typed_shape() -> None:
    check = ModelDodEvidenceCheck(check_type="lab_receipt", check_value=dict(SHAPE))
    assert check.check_type is EnumDodCheckType.LAB_RECEIPT
    assert check.check_value == SHAPE


def test_lab_receipt_check_type_is_accepted_inside_a_contract_dod_item() -> None:
    item = ModelContractDodItem(
        id="dod-001",
        description="installed on the lab and observed running",
        checks=[{"check_type": "lab_receipt", "check_value": dict(SHAPE)}],
    )
    assert item.checks[0].check_type is EnumDodCheckType.LAB_RECEIPT


@pytest.mark.parametrize("missing", sorted(SHAPE))
def test_lab_receipt_check_type_refuses_a_missing_field(missing: str) -> None:
    value = {k: v for k, v in SHAPE.items() if k != missing}
    with pytest.raises(ValidationError, match=missing):
        ModelDodEvidenceCheck(check_type="lab_receipt", check_value=value)


def test_lab_receipt_check_type_refuses_an_unknown_field() -> None:
    with pytest.raises(ValidationError, match="surprise"):
        ModelDodEvidenceCheck(
            check_type="lab_receipt", check_value={**SHAPE, "surprise": "x"}
        )


@pytest.mark.parametrize("blank", ["", "   "])
def test_lab_receipt_check_type_refuses_a_blank_field(blank: str) -> None:
    with pytest.raises(ValidationError):
        ModelDodEvidenceCheck(
            check_type="lab_receipt", check_value={**SHAPE, "installer": blank}
        )


@pytest.mark.parametrize("value", ["uv run pytest", "", {}])
def test_lab_receipt_check_type_refuses_a_value_without_the_shape(value: Any) -> None:
    with pytest.raises(ValidationError):
        ModelDodEvidenceCheck(check_type="lab_receipt", check_value=value)


def test_other_check_types_keep_their_free_form_values() -> None:
    check = ModelDodEvidenceCheck(check_type="command", check_value="true")
    assert check.check_value == "true"
