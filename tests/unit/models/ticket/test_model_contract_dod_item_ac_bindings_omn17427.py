# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OMN-17427: a product-repo ticket contract can carry ``ac_bindings``.

Only onex_change_control's item model declared ``dod_evidence[].ac_bindings``,
so ModelTicketContract refused every contract that carried it as an extra
input, while the DoD verifier reads the field. These tests pin the field on the
core item, validate three contracts copied unchanged from onex_change_control,
keep the binding's own refusals (carried over from OCC unchanged), and check
that a contract with no bindings is unchanged.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from omnibase_core.models.ticket.model_ac_binding import ModelAcBinding
from omnibase_core.models.ticket.model_contract_dod_item import ModelContractDodItem
from omnibase_core.models.ticket.model_ticket_contract import ModelTicketContract

pytestmark = pytest.mark.unit

FIXTURES = (
    Path(__file__).resolve().parents[3] / "fixtures" / "ticket_contracts_ac_bindings"
)
_HASH = hashlib.sha256(b"the text of criterion AC1").hexdigest()


def _binding(**overrides: Any) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "label": "AC1",
        "criterion_hash": _HASH,
        "proposed_by": "occ-autobind",
        "accepted_by": "a-reviewer",
        "accepted_at": "2026-09-17T09:15:00Z",
    }
    entry.update(overrides)
    return entry


def _item(**extra: Any) -> dict[str, Any]:
    item: dict[str, Any] = {
        "id": "dod-omn-1-ac1",
        "description": "the evidence for one criterion",
        "source": "manual",
        "checks": [
            {"check_type": "test_passes", "check_value": "uv run pytest tests -q"}
        ],
        "binds_ac": ["AC1"],
    }
    item.update(extra)
    return item


def _contract(*items: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "ticket_id": "OMN-1",
        "title": "record an accepted binding",
        "dod_evidence": list(items),
    }


@pytest.mark.parametrize("ticket_id", ["OMN-18565", "OMN-19617", "OMN-20481"])
def test_an_occ_contract_carrying_ac_bindings_validates(ticket_id: str) -> None:
    text = (FIXTURES / f"{ticket_id}.yaml").read_text(encoding="utf-8")
    contract = ModelTicketContract.from_yaml(text)

    assert contract.ticket_id == ticket_id
    bindings = [b for item in contract.dod_evidence for b in item.ac_bindings]
    assert bindings, f"{ticket_id}: expected the fixture to carry ac_bindings"
    for item in contract.dod_evidence:
        for binding in item.ac_bindings:
            assert binding.label in item.binds_ac
            assert binding.is_accepted


def test_a_binding_round_trips_on_the_item() -> None:
    item = ModelContractDodItem.model_validate(
        _item(
            ac_bindings=[
                _binding(),
                _binding(label="AC2", accepted_by="", accepted_at=""),
            ]
        )
    )

    assert [b.label for b in item.ac_bindings] == ["AC1", "AC2"]
    assert item.ac_bindings[0].is_accepted
    assert not item.ac_bindings[1].is_accepted
    assert isinstance(item.ac_bindings[0], ModelAcBinding)


def test_a_contract_with_no_ac_bindings_is_unchanged() -> None:
    raw = _contract(_item())
    contract = ModelTicketContract.model_validate(raw)

    assert contract.dod_evidence[0].ac_bindings == []
    dumped = contract.model_dump(exclude_defaults=True)
    assert "ac_bindings" not in dumped["dod_evidence"][0]


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"carried_by": "a-reviewer"}, "extra_forbidden|Extra inputs"),
        ({"criterion_hash": 42}, "string_type|valid string"),
        ({"accepted_by": ["a-reviewer"]}, "string_type|valid string"),
        ({"label": "criterion one"}, "acceptance-criterion label"),
        ({"criterion_hash": _HASH[:12]}, "full lowercase sha256"),
        ({"accepted_at": ""}, "BOTH `accepted_by` and"),
        ({"accepted_at": "2026-09-17"}, "RFC 3339 UTC"),
    ],
    ids=[
        "unknown_key",
        "hash_wrong_type",
        "actor_wrong_type",
        "label_shape",
        "short_hash",
        "acceptance_pair",
        "utc_seconds",
    ],
)
def test_a_malformed_binding_is_refused(
    overrides: dict[str, Any], message: str
) -> None:
    with pytest.raises(ValidationError, match=message):
        ModelTicketContract.model_validate(
            _contract(_item(ac_bindings=[_binding(**overrides)]))
        )


def test_ac_bindings_of_the_wrong_type_are_refused() -> None:
    with pytest.raises(ValidationError, match=r"list_type|valid list"):
        ModelTicketContract.model_validate(_contract(_item(ac_bindings="AC1")))
