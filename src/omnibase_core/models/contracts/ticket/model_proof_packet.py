# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelProofPacket — tiered (L0-L3) evidence-depth packet for a DoD receipt.

A proof packet attaches a *graded* evidence claim to a :class:`ModelDodReceipt`
so a weak receipt and a strong one are no longer indistinguishable. The packet
declares a :class:`EnumProofTier` and carries the fields that tier requires;
the model validator rejects a packet whose tier claims more depth than its
populated fields support (e.g. ``tier=L2`` with no ``runtime_sha``).

Tier field requirements (cumulative — each tier requires all lower-tier fields)
-------------------------------------------------------------------------------
L0 (docs)     : pr_url, ci_status
L1 (code)     : + merged_pr_url, test_evidence
L2 (runtime)  : + runtime_sha, image_digest, correlation_id, terminal_event,
                projection_ref
L3 (customer) : + dashboard_ref, network_evidence, replay_class

Source fields (``evidence_source_sha``, ``evidence_ticket``, ``verifier``) are
filled by F1 autobind (OMN-13317) from the Evidence-Source line; they are
optional on the model so a packet can be constructed before autobind runs, but
the validator requires ``verifier`` from L1 upward (anything beyond a docs PR
needs an attributed verifier).
"""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from omnibase_core.enums.ticket.enum_proof_tier import EnumProofTier

_SHA_RE = re.compile(r"^[0-9a-fA-F]{7,40}$")
_TICKET_ID_RE = re.compile(r"^OMN-\d+$")

# Per-tier *additional* required field names (the fields that tier introduces).
# Cumulative requirement is computed by unioning this tier's set with every
# lower tier's set, so the policy stays single-sourced and a new tier only
# needs one entry here. Listed as a module constant (not inline in the
# validator) so the required-field policy is grep-able and testable.
_TIER_ADDED_FIELDS: dict[EnumProofTier, tuple[str, ...]] = {
    EnumProofTier.L0: ("pr_url", "ci_status"),
    EnumProofTier.L1: ("merged_pr_url", "test_evidence"),
    EnumProofTier.L2: (
        "runtime_sha",
        "image_digest",
        "correlation_id",
        "terminal_event",
        "projection_ref",
    ),
    EnumProofTier.L3: ("dashboard_ref", "network_evidence", "replay_class"),
}


def required_fields_for_tier(tier: EnumProofTier) -> tuple[str, ...]:
    """Return the cumulative set of fields required at ``tier`` (this tier + all below)."""
    fields: list[str] = []
    for candidate in (
        EnumProofTier.L0,
        EnumProofTier.L1,
        EnumProofTier.L2,
        EnumProofTier.L3,
    ):
        fields.extend(_TIER_ADDED_FIELDS[candidate])
        if candidate is tier:
            break
    return tuple(fields)


class ModelProofPacket(BaseModel):
    """Graded L0-L3 evidence packet attached to a :class:`ModelDodReceipt`.

    Frozen. The declared ``tier`` is a claim; the model validator enforces
    that every field the tier requires is populated, so a packet cannot claim
    a higher tier than its evidence supports.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )

    tier: EnumProofTier = Field(
        ...,
        description=(
            "Declared evidence-depth tier (L0-L3). The validator rejects a "
            "tier whose required fields are not all populated."
        ),
    )

    # --- L0: docs floor -----------------------------------------------------
    pr_url: str | None = Field(
        default=None, description="URL of the PR carrying the change (L0+)."
    )
    ci_status: str | None = Field(
        default=None,
        description="Terminal CI status string for the PR (e.g. 'success') (L0+).",
    )

    # --- L1: merged code + test --------------------------------------------
    merged_pr_url: str | None = Field(
        default=None, description="URL of the merged PR (L1+)."
    )
    test_evidence: str | None = Field(
        default=None,
        description="Reference to the test that exercised the change (L1+).",
    )

    # --- L2: runtime --------------------------------------------------------
    runtime_sha: str | None = Field(
        default=None,
        description="Git SHA of the running binary (7-40 hex) (L2+).",
    )
    image_digest: str | None = Field(
        default=None,
        description="Container image digest of the deployed image (L2+).",
    )
    correlation_id: str | None = Field(
        default=None,
        description="Correlation id of the proving workflow run (L2+).",
    )
    terminal_event: str | None = Field(
        default=None,
        description="Terminal bus event topic/id proving transit (L2+).",
    )
    projection_ref: str | None = Field(
        default=None,
        description="Reference to the materialized projection row (L2+).",
    )

    # --- L3: customer-visible ----------------------------------------------
    dashboard_ref: str | None = Field(
        default=None,
        description="Reference to the customer-visible dashboard surface (L3).",
    )
    network_evidence: str | None = Field(
        default=None,
        description="Captured network request/response proving render (L3).",
    )
    replay_class: str | None = Field(
        default=None,
        description="Replay class / fixture id making the run replayable (L3).",
    )

    # --- Source fields (F1 autobind, OMN-13317) ----------------------------
    evidence_source_sha: str | None = Field(
        default=None,
        description=(
            "Evidence-Source commit SHA, filled by F1 autobind from the "
            "Evidence-Source PR-body line (OMN-13317)."
        ),
    )
    evidence_ticket: str | None = Field(
        default=None,
        description="Evidence-Ticket id (OMN-XXXX), filled by F1 autobind.",
    )
    verifier: str | None = Field(
        default=None,
        description=(
            "Identity that verified the proof, filled by F1 autobind. Required "
            "from tier L1 upward — only a docs (L0) packet may omit it."
        ),
    )

    @field_validator("evidence_source_sha", "runtime_sha")
    @classmethod
    def _validate_sha(cls, v: str | None) -> str | None:
        if v is None:
            return None
        if not _SHA_RE.match(v):
            raise ValueError(f"must be a 7-40 char hex git SHA, got: {v!r}")
        return v

    @field_validator("evidence_ticket")
    @classmethod
    def _validate_ticket(cls, v: str | None) -> str | None:
        if v is None:
            return None
        if not _TICKET_ID_RE.match(v):
            raise ValueError(f"evidence_ticket must match OMN-\\d+, got: {v!r}")
        return v

    @model_validator(mode="after")
    def enforce_tier_required_fields(self) -> ModelProofPacket:
        """Reject a packet whose declared tier has unpopulated required fields.

        A "required" field here means non-None and, for strings, non-blank
        after stripping. This is what prevents a packet from claiming ``L2``
        while carrying only the L0 docs fields — the claim of depth must be
        backed by the fields that depth requires.

        ``verifier`` is required from L1 upward: anything past a docs PR needs
        an attributed verifier so the receipt is not self-anonymous.
        """
        missing: list[str] = []
        for name in required_fields_for_tier(self.tier):
            value = getattr(self, name)
            if value is None or (isinstance(value, str) and not value.strip()):
                missing.append(name)

        if self.tier.rank >= EnumProofTier.L1.rank:
            verifier = self.verifier
            if verifier is None or not verifier.strip():
                missing.append("verifier")

        if missing:
            raise ValueError(
                f"proof_packet declares tier {self.tier.value} but is missing "
                f"required field(s): {', '.join(missing)}. A tier is a claim of "
                "evidence depth; every field that tier requires must be populated."
            )
        return self


__all__ = ["ModelProofPacket", "required_fields_for_tier"]
