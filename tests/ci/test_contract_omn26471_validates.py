# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""contracts/OMN-26471.yaml validates against ModelTicketContract (the contract-validation gate)."""

from pathlib import Path

import yaml

from omnibase_core.models.ticket.model_ticket_contract import ModelTicketContract

_CONTRACT = Path(__file__).resolve().parents[2] / "contracts" / "OMN-26471.yaml"


def test_contract_omn26471_validates() -> None:
    data = yaml.safe_load(_CONTRACT.read_text(encoding="utf-8"))
    contract = ModelTicketContract.model_validate(data)
    assert contract.ticket_id == "OMN-26471"
