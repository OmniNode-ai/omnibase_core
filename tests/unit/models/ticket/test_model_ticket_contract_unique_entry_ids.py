# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""One id on two entries of a ticket contract section is refused (OMN-22502)."""

from __future__ import annotations

import copy
from typing import Any

import pytest
import yaml

from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.ticket.model_ticket_contract import ModelTicketContract

pytestmark = pytest.mark.unit

CONTRACT: dict[str, Any] = {
    "schema_version": "1.0.0",
    "ticket_id": "OMN-1",
    "title": "A title",
    "summary": "A summary",
    "is_seam_ticket": False,
    "interface_change": False,
    "requirements": [
        {
            "id": "req-a",
            "statement": "A requirement",
            "acceptance": [{"id": "AC1", "statement": "AC1: it holds"}],
        },
        {
            "id": "req-b",
            "statement": "Another requirement",
            "acceptance": [{"id": "AC2", "statement": "AC2: it holds"}],
        },
    ],
    "dod_evidence": [
        {
            "id": "dod-a",
            "description": "An entry",
            "source": "manual",
            "checks": [{"check_type": "test_passes", "check_value": "pytest a.py"}],
        },
        {
            "id": "dod-b",
            "description": "Another entry",
            "source": "manual",
            "checks": [{"check_type": "test_passes", "check_value": "pytest b.py"}],
        },
    ],
}


def _validate(contract: dict[str, Any]) -> ModelTicketContract:
    return ModelTicketContract.from_yaml(yaml.safe_dump(contract, sort_keys=False))


def test_unique_ids_validate() -> None:
    parsed = _validate(CONTRACT)

    assert [item.id for item in parsed.dod_evidence] == ["dod-a", "dod-b"]


@pytest.mark.parametrize(
    ("section", "entry_id"), [("dod_evidence", "dod-a"), ("requirements", "req-a")]
)
def test_one_id_on_two_entries_is_refused_naming_it(
    section: str, entry_id: str
) -> None:
    contract = copy.deepcopy(CONTRACT)
    contract[section][1]["id"] = entry_id

    with pytest.raises(ModelOnexError, match=f"{section}: id '{entry_id}' is on 2"):
        _validate(contract)


def test_one_id_in_two_sections_is_not_a_duplicate() -> None:
    contract = copy.deepcopy(CONTRACT)
    contract["requirements"][0]["id"] = "dod-a"

    assert _validate(contract).requirements[0].id == "dod-a"
