# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelEvidenceVerifierResult — outcome of an evidence bundle verification run."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from omnibase_core.enums.ticket.enum_receipt_status import EnumReceiptStatus


class ModelEvidenceVerifierResult(BaseModel):
    """Result produced by a verifier that checked an evidence bundle.

    ``checks`` is an ordered tuple of dicts — each dict records an individual
    check performed by the verifier (e.g. artifact presence, hash match,
    contract compliance). The ``verifier`` field names the agent or system
    that ran the checks.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    correlation_id: str
    status: EnumReceiptStatus
    verifier: str
    checks: tuple[dict[str, object], ...]


__all__ = ["ModelEvidenceVerifierResult"]
