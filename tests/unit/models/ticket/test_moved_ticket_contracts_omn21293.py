# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Read the two ticket contracts moved into the product repository (OMN-21293).

OMN-20450 and OMN-20499 were moved from onex_change_control into contracts/.
The scheduled closer reads contracts/<ticket>.yaml from the owning repository,
so each moved file must be present, parse as a YAML mapping naming its own
ticket, and load through the production ticket-contract parser.
"""

from pathlib import Path

import pytest
import yaml

from omnibase_core.models.ticket.model_ticket_contract import ModelTicketContract

REPO_ROOT = Path(__file__).resolve().parents[4]

MOVED_TICKET_IDS = ["OMN-20450", "OMN-20499"]

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("ticket_id", MOVED_TICKET_IDS)
def test_moved_contract_is_a_mapping_naming_its_ticket(ticket_id: str) -> None:
    """The moved file exists, loads as a mapping and names its own ticket."""
    path = REPO_ROOT / "contracts" / f"{ticket_id}.yaml"
    assert path.is_file(), f"{ticket_id}: contract missing from the owning repository"

    data = yaml.safe_load(path.read_text(encoding="utf-8"))

    assert isinstance(data, dict), f"{ticket_id}: contract is not a YAML mapping"
    assert data.get("ticket_id") == ticket_id


@pytest.mark.parametrize("ticket_id", MOVED_TICKET_IDS)
def test_moved_contract_loads_through_ticket_contract_model(ticket_id: str) -> None:
    """The moved file validates through ModelTicketContract with populated checks."""
    path = REPO_ROOT / "contracts" / f"{ticket_id}.yaml"
    assert path.is_file(), f"{ticket_id}: contract missing from the owning repository"

    contract = ModelTicketContract.from_yaml(path.read_text(encoding="utf-8"))

    assert contract.ticket_id == ticket_id
    assert contract.dod_evidence
    for item in contract.dod_evidence:
        assert item.checks
        for check in item.checks:
            assert isinstance(check.check_value, str)
            assert check.check_value.strip()
