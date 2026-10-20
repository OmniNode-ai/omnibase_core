# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OMN-21220: a product-repo ticket contract can retire a binding without OCC.

A merged ``dod_evidence`` item is never edited, so a binding on a criterion the
live ticket no longer carries is withdrawn by a ``supersedes_ac_binding`` entry
appended on a later item. Only onex_change_control's item model declared that
field, so ModelTicketContract refused it as an extra input in every product
repository. These tests pin the field on the core item, the retirement's own
refusals (carried over from OCC unchanged), and that an unknown item key is
still refused.
"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from omnibase_core.enums.ticket.enum_ac_binding_retirement_reason import (
    EnumAcBindingRetirementReason,
)
from omnibase_core.models.ticket.model_contract_ac_binding_retirement import (
    ModelContractAcBindingRetirement,
)
from omnibase_core.models.ticket.model_contract_dod_item import ModelContractDodItem
from omnibase_core.models.ticket.model_ticket_contract import ModelTicketContract

pytestmark = pytest.mark.unit


def _item(item_id: str, binds_ac: list[str], **extra: Any) -> dict[str, Any]:
    item: dict[str, Any] = {
        "id": item_id,
        "description": "the evidence for one criterion",
        "source": "manual",
        "checks": [
            {"check_type": "test_passes", "check_value": "uv run pytest tests -q"}
        ],
        "binds_ac": binds_ac,
    }
    item.update(extra)
    return item


def _retirement(**overrides: Any) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "item": "dod-omn-1-ac5",
        "label": "AC5",
        "reason_kind": "no_longer_applicable",
        "reason": "AC5 was a contract-only criterion the ticket never carried.",
        "retired_by": "a-lane",
        "retired_at": "2026-10-20T21:29:48Z",
    }
    entry.update(overrides)
    return entry


def _contract(*items: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "ticket_id": "OMN-1",
        "title": "retire a drifted binding",
        "dod_evidence": list(items),
    }


def test_a_ticket_contract_carrying_a_retirement_validates() -> None:
    contract = ModelTicketContract.model_validate(
        _contract(
            _item("dod-omn-1-ac5", ["AC5"]),
            _item(
                "dod-omn-1-ac1",
                ["AC1"],
                supersedes_ac_binding=[
                    _retirement(),
                    _retirement(
                        label="AC6",
                        reason_kind="superseded_by",
                        superseded_by="dod-omn-1-ac1",
                        reason="AC6 is now proven by the AC1 item's own tests.",
                    ),
                ],
            ),
        )
    )

    retirements = contract.dod_evidence[1].supersedes_ac_binding
    assert [entry.label for entry in retirements] == ["AC5", "AC6"]
    assert retirements[0].reason_kind is (
        EnumAcBindingRetirementReason.NO_LONGER_APPLICABLE
    )
    assert retirements[1].superseded_by == "dod-omn-1-ac1"


def test_an_item_carries_no_retirement_by_default() -> None:
    item = ModelContractDodItem.model_validate(_item("dod-omn-1-ac1", ["AC1"]))
    assert item.supersedes_ac_binding == ()


def test_a_merged_untyped_retirement_still_parses() -> None:
    entry = ModelContractAcBindingRetirement.model_validate(
        {
            "item": "dod-omn-1-ac5",
            "label": "AC5",
            "reason": "an older retirement with no typed reason",
        }
    )
    assert entry.reason_kind is None
    assert entry.retired_by is None


def test_an_unknown_item_key_is_still_refused() -> None:
    with pytest.raises(ValidationError, match=r"extra_forbidden|Extra inputs"):
        ModelTicketContract.model_validate(
            _contract(_item("dod-omn-1-ac1", ["AC1"], supersedes_binding=[]))
        )


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"label": "criterion five"}, "acceptance-criterion label"),
        ({"reason": "too short"}, "at least 12 characters"),
        ({"reason": "            "}, "must not be blank"),
        ({"reason_kind": "superseded_by"}, "requires `superseded_by`"),
        ({"superseded_by": "dod-omn-1-ac1"}, "only valid with reason_kind"),
        ({"retired_at": "2026-10-20"}, "RFC 3339 UTC"),
        ({"retired_at": None}, "recorded together"),
        (
            {
                "reason_kind": None,
                "retired_by": None,
                "retired_at": "2026-10-20T00:00:00Z",
            },
            "only valid with a typed reason_kind",
        ),
        ({"carried_by": "dod-omn-1-ac1"}, "extra_forbidden|Extra inputs"),
    ],
    ids=[
        "label_shape",
        "reason_floor",
        "blank_reason",
        "superseded_by_needs_a_replacement",
        "replacement_needs_superseded_by",
        "utc_seconds",
        "audit_pair",
        "audit_needs_a_typed_reason",
        "unknown_key",
    ],
)
def test_a_malformed_retirement_is_refused(
    overrides: dict[str, Any], message: str
) -> None:
    with pytest.raises(ValidationError, match=message):
        ModelTicketContract.model_validate(
            _contract(
                _item("dod-omn-1-ac5", ["AC5"]),
                _item(
                    "dod-omn-1-ac1",
                    ["AC1"],
                    supersedes_ac_binding=[_retirement(**overrides)],
                ),
            )
        )
