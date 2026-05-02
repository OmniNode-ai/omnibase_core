# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Result model for deterministic OCC merge eligibility."""

from __future__ import annotations

import json

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_occ_eligibility_reason import EnumOccEligibilityReason


class ModelOccEligibilityResult(BaseModel):
    """Replayable OCC eligibility decision."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    eligible: bool
    reason: EnumOccEligibilityReason
    ticket_ids: tuple[str, ...] = Field(default_factory=tuple)
    occ_commit_sha: str = Field(default="")
    contract_hashes: dict[str, str] = Field(default_factory=dict)
    receipt_ids: tuple[str, ...] = Field(default_factory=tuple)
    missing_contracts: tuple[str, ...] = Field(default_factory=tuple)
    missing_or_nonpass_receipts: tuple[str, ...] = Field(default_factory=tuple)
    dependency_prs: tuple[str, ...] = Field(default_factory=tuple)
    detail: str = Field(default="")

    def as_dict(self) -> dict[str, object]:
        return {
            "eligible": self.eligible,
            "reason": self.reason.value,
            "ticket_ids": list(self.ticket_ids),
            "occ_commit_sha": self.occ_commit_sha,
            "contract_hashes": dict(sorted(self.contract_hashes.items())),
            "receipt_ids": list(self.receipt_ids),
            "missing_contracts": list(self.missing_contracts),
            "missing_or_nonpass_receipts": list(self.missing_or_nonpass_receipts),
            "dependency_prs": list(self.dependency_prs),
            "detail": self.detail,
        }

    def to_json(self) -> str:
        return json.dumps(self.as_dict(), sort_keys=True, separators=(",", ":"))


__all__ = ["ModelOccEligibilityResult"]
