# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pull-request citation facts supplied to the pure checker."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from omnibase_core.enums.enum_receipt_gate_exemption import EnumReceiptGateExemption


class ModelParentTicketCitationFacts(BaseModel):
    """Immutable citations and an optional claimed receipt-gate exemption."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    cited_tickets: tuple[str, ...] = ()
    exemption: EnumReceiptGateExemption | None = None
