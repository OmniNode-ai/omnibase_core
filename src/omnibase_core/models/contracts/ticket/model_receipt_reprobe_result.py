# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Per-receipt result model for the re-probe verification mode (OMN-9789).

Emitted by
:func:`omnibase_core.validation.validator_receipt_reprobe.verify_receipts_by_reexecuting_probes`
to describe the outcome of re-running a single receipt's recorded
``probe_command`` against current external state. Frozen — once produced
it is an audit artifact.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_reprobe_status import EnumReprobeStatus as ReprobeStatus


class ModelReceiptReprobeResult(BaseModel):
    """Outcome of re-running a single receipt's recorded ``probe_command``."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )

    receipt_path: str = Field(
        ...,
        min_length=1,
        description="Filesystem path to the receipt that was re-probed.",
    )
    ticket_id: str = Field(
        ...,
        min_length=1,
        description=(
            "Linear ticket ID parsed from the receipt, or '*' if the receipt "
            "could not be parsed."
        ),
    )
    # string-id-ok: evidence item IDs are human-readable contract slugs (e.g., 'dod-001'), not UUIDs
    evidence_item_id: str = Field(
        ...,
        min_length=1,
        description="dod_evidence[].id from the receipt, or '*' if unparseable.",
    )
    check_type: str = Field(
        ...,
        min_length=1,
        description="dod_evidence check_type from the receipt, or '*' if unparseable.",
    )
    status: ReprobeStatus = Field(
        ...,
        description=(
            "PASS iff the recorded probe re-executed and exited with the "
            "recorded exit_code; FAIL otherwise."
        ),
    )
    detail: str = Field(
        ...,
        description=(
            "Human-readable explanation. Always identifies the failure mode "
            "(probe_command/allowlist/exit_code/timeout/etc.) on FAIL."
        ),
    )


__all__ = [
    "ModelReceiptReprobeResult",
    "ReprobeStatus",
]
