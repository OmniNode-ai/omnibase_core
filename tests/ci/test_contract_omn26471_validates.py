# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""contracts/OMN-26471.yaml validates against ModelTicketContract (the contract-validation gate)."""

from pathlib import Path

import yaml

from omnibase_core.enums.enum_migration_ledger_shape import EnumMigrationLedgerShape
from omnibase_core.models.ticket.model_ticket_contract import ModelTicketContract

_CONTRACT = Path(__file__).resolve().parents[2] / "contracts" / "OMN-26471.yaml"


def test_contract_omn26471_validates() -> None:
    data = yaml.safe_load(_CONTRACT.read_text(encoding="utf-8"))
    contract = ModelTicketContract.model_validate(data)
    assert contract.ticket_id == "OMN-26471"


def test_ledger_shape_enum_names_both_shapes() -> None:
    """Red at the merge base, where the shape enum does not exist yet."""
    assert {shape.value for shape in EnumMigrationLedgerShape} == {
        "stream_domain_version_checksum",
        "version_checksum",
    }
