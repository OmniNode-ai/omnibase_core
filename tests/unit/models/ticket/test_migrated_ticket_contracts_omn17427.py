# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Read the migrated ticket contracts from the product repository (OMN-17427).

The scheduled closer looks up contracts/<ticket>.yaml in the owning repository.
These cases exercise that layout and the production ticket-contract parser without
an onex_change_control checkout or any remote calls. Evidence may be appended as
work continues; the migrated evidence must remain available to consumers.
"""

from pathlib import Path

import pytest

from omnibase_core.models.ticket.model_ticket_contract import ModelTicketContract

REPO_ROOT = Path(__file__).resolve().parents[4]

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("ticket_id", "minimum_evidence_count"),
    [
        ("OMN-14750", 3),
        ("OMN-15392", 5),
        ("OMN-15622", 5),
        ("OMN-15664", 4),
        ("OMN-15667", 3),
        ("OMN-15692", 5),
        ("OMN-15911", 9),
        ("OMN-16321", 3),
        ("OMN-16359", 10),
        ("OMN-16451", 18),
        ("OMN-16641", 3),
        ("OMN-17159", 3),
        ("OMN-17538", 3),
        ("OMN-17744", 4),
        ("OMN-18163", 4),
        ("OMN-18219", 3),
        ("OMN-18712", 1),
        ("OMN-19041", 1),
        ("OMN-19059", 3),
        ("OMN-20334", 4),
        ("OMN-20450", 1),
        ("OMN-20499", 1),
    ],
)
def test_migrated_contract_loads_with_evidence(
    ticket_id: str, minimum_evidence_count: int
) -> None:
    """A repo-local lookup returns the requested ticket with populated checks."""
    path = REPO_ROOT / "contracts" / f"{ticket_id}.yaml"
    assert path.is_file(), f"{ticket_id}: contract missing from the owning repository"

    contract = ModelTicketContract.from_yaml(path.read_text(encoding="utf-8"))

    assert contract.ticket_id == ticket_id
    assert len(contract.dod_evidence) >= minimum_evidence_count
    assert any(item.checks for item in contract.dod_evidence)
    for item in contract.dod_evidence:
        assert item.id
        # A disclosed supersession is retained as metadata, not executable proof.
        assert item.checks or (item.status == "skipped" and item.evidence_artifact)
        for check in item.checks:
            assert isinstance(check.check_value, str)
            assert check.check_value.strip()
