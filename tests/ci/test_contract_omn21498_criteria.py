# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OMN-21498: the contract lists only the criteria the ticket carries (AC1, AC2).

The ticket carries two acceptance criteria. A contract that lists more makes the
verifier skip the ticket as CRITERIA_DRIFT, so every listed criterion must be one
the ticket carries and every retired binding must name an item that exists.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

CONTRACT = Path(__file__).resolve().parents[2] / "contracts" / "OMN-21498.yaml"
TICKET_CRITERIA = {"AC1", "AC2"}


@pytest.fixture(scope="module")
def contract() -> dict[str, Any]:
    loaded = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


@pytest.mark.unit
def test_listed_criteria_are_the_ticket_criteria(contract: dict[str, Any]) -> None:
    listed = {ac["id"] for req in contract["requirements"] for ac in req["acceptance"]}
    assert listed == TICKET_CRITERIA


@pytest.mark.unit
def test_retired_bindings_name_existing_items(contract: dict[str, Any]) -> None:
    items = contract["dod_evidence"]
    ids = {item["id"] for item in items}
    for item in items:
        for retired in item.get("supersedes_ac_binding", []):
            assert retired["item"] in ids
