# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""One receipt attestation contradicted by the PR diff."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from omnibase_core.enums.ticket.enum_diff_attestation import EnumDiffAttestation


class ModelReceiptDiffConsistencyViolation(BaseModel):
    """One contradicted attestation, stamped with its receipt path."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    receipt_path: str
    attestation: EnumDiffAttestation
    detail: str
