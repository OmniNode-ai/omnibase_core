# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelDodReceipt — proof artifact for a single dod_evidence check run.

A receipt is the **only** acceptable proof that a ticket's DoD check was
executed. The receipt-gate CI check (`validate_pr_receipts.py`) blocks
merge on any PR whose linked ticket contract has dod_evidence items
without corresponding PASS receipts.

Design rule: ticket contracts declare intent (what must be proved).
Receipts declare fact (what was proved, when, by whom, with what output).
A ticket is not Done without every declared check having a PASS receipt.

Receipts are stored at:
    onex_change_control/drift/dod_receipts/<OMN-XXXX>/<evidence-item-id>/<check-type>.yaml

The path encodes ticket → evidence item → check, mirroring the contract
structure so lookup is O(1) path traversal, not search.

Adversarial invariants (OMN-9786, Centralized Transition Policy)
----------------------------------------------------------------
The receipt is the canonical "did this actually happen" probe artifact.
Four invariants are enforced by ``enforce_adversarial_invariants`` to keep
self-attested or structurally-weak proof from satisfying the gate:

1. ``verifier == runner`` (self-attestation) AND ``status == PASS`` →
   status auto-downgraded to ``ADVISORY``. Independent verification is
   required for PASS. ``FAIL`` and ``PENDING`` are preserved — they
   carry distinct meaning that ADVISORY would erase. Identity strings
   are compared after stripping surrounding whitespace, so
   ``"worker-A"`` and ``"worker-A "`` cannot be used to bypass this
   rule.
2. ``check_type == "file_exists"`` AND ``status == PASS`` → status
   auto-downgraded to ``ADVISORY``. File presence proves a write, not
   that the behavior under test occurred. ``FAIL`` and ``PENDING`` are
   preserved for the same reason as Rule 1.
3. ``check_type in {command, test_passes, endpoint, grep}`` AND empty
   ``probe_stdout`` AND ``status != PENDING`` → ``ValueError``. An
   executable check that produced no captured output is
   indistinguishable from "never ran". ``PENDING`` is exempt because by
   definition the probe was allocated but not yet executed — empty
   stdout is the correct representation.
4. ``schema_version`` must be a valid SemVer 2.0.0 string (per the
   official regex inlined as ``_SEMVER_RE``; mirrors
   ``SEMVER_PATTERN`` in :mod:`omnibase_core.validation.phases`).
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from omnibase_core.enums.ticket.enum_receipt_status import EnumReceiptStatus

_TICKET_ID_RE = re.compile(r"^OMN-\d+$")
_SHA_RE = re.compile(r"^[0-9a-fA-F]{7,40}$")
# SemVer 2.0.0 — official regex from https://semver.org/#is-there-a-suggested-regular-expression-regex-to-check-a-semver-string
# Rejects leading zeros in numeric core (e.g. "01.0.0"), allows pre-release
# identifiers with dot-separated alphanumerics and hyphens (e.g. "1.0.0-rc.1"),
# and allows build metadata containing hyphens (e.g. "1.0.0+build-7"). Inlined
# here to avoid a contracts-models → validation circular import.
_SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)"
    r"(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
    r"(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
)

# check_types whose proof requires captured stdout. Listed here (not in the
# validator body) so the policy is grep-able and easy to extend.
EXECUTABLE_CHECK_TYPES = frozenset({"command", "test_passes", "endpoint", "grep"})

# check_types whose proof is structurally weak (file presence only). The
# transition policy demotes these to ADVISORY regardless of verifier identity.
WEAK_PROOF_CHECK_TYPES = frozenset({"file_exists"})


class ModelDodReceipt(BaseModel):
    """Receipt proving a single dod_evidence check was run for a ticket.

    Frozen. Every field except ``actual_output``, ``exit_code``,
    ``duration_ms``, and ``pr_number`` is required — there is no such thing
    as an "aspirational" receipt. If a receipt exists on disk, it asserts
    the check ran with the recorded outcome.

    A receipt is consumed by the receipt-gate CI check at PR merge time
    and by ``node_dod_verify`` at ticket-close time. Both treat absence
    as identical to FAIL.

    The four adversarial fields (``schema_version``, ``verifier``,
    ``probe_command``, ``probe_stdout``) make the receipt resistant to
    self-attestation and "file written = work done" loopholes. See module
    docstring for the policy enforced by ``enforce_adversarial_invariants``.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )

    schema_version: str = Field(
        ...,
        description=(
            "SemVer 2.0.0 string for the receipt schema. Pins downstream "
            "consumers so future field additions can negotiate compatibility "
            "instead of silently dropping fields. Validated by the official "
            "SemVer 2.0.0 regex (see ``_SEMVER_RE``)."
        ),
    )
    ticket_id: str = Field(
        ..., description="Linear ticket this receipt proves (e.g., OMN-9084)"
    )
    # string-id-ok: evidence item IDs are human-readable slugs from the contract YAML (e.g., 'dod-001'), not UUIDs
    evidence_item_id: str = Field(
        ..., min_length=1, description="dod_evidence[].id this receipt covers"
    )
    check_type: str = Field(
        ...,
        min_length=1,
        description="dod_evidence[].checks[].check_type this receipt executed",
    )
    check_value: str = Field(
        ...,
        min_length=1,
        description="The original check_value from the contract (for audit parity)",
    )
    status: EnumReceiptStatus = Field(
        ...,
        description=(
            "PASS, FAIL, ADVISORY, or PENDING. Absence of a receipt is also "
            "treated as FAIL. May be auto-downgraded to ADVISORY by the "
            "transition policy (see module docstring)."
        ),
    )
    run_timestamp: datetime = Field(
        ..., description="UTC timestamp when the check was executed"
    )
    commit_sha: str = Field(
        ...,
        description=(
            "Git commit SHA the check was executed against. Used by the "
            "receipt-gate to reject stale receipts that predate the PR head."
        ),
    )
    runner: str = Field(
        ...,
        min_length=1,
        description=(
            "Who/what ran the check — agent name, worker ID, human login, or "
            "CI job identifier. Used for audit + friction attribution."
        ),
    )
    verifier: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description=(
            "Identity that verified the probe output. For ``PASS`` "
            "receipts it must differ from ``runner`` — self-attestation "
            "(verifier == runner, comparison is whitespace-stripped) "
            "auto-downgrades to ADVISORY. ``FAIL`` and ``PENDING`` are "
            "preserved regardless of verifier identity."
        ),
    )
    probe_command: str = Field(
        ...,
        max_length=10000,
        description=(
            "Literal command/probe executed (e.g., 'gh pr checks 123'). "
            "Recorded so audits can replay the probe."
        ),
    )
    probe_stdout: str = Field(
        ...,
        max_length=1_000_000,
        description=(
            "Literal captured stdout from the probe. Required (non-empty) "
            "for executable check_types: command, test_passes, endpoint, "
            "grep. May be empty for file_exists and other check_types that "
            "produce no output."
        ),
    )
    actual_output: str | None = Field(
        default=None,
        description=(
            "Truncated output from the check (stdout, HTTP body, file content). "
            "Large outputs should be stored in a sibling file and referenced here "
            "via path. None is allowed when the check produces no output. "
            "Distinct from ``probe_stdout`` (the literal captured stream); "
            "``actual_output`` may be a structured / truncated rendering for "
            "legacy classifiers that read it instead of ``probe_stdout``."
        ),
    )
    exit_code: int | None = Field(
        default=None,
        description="Exit code for command-type checks. None when not applicable.",
    )
    duration_ms: int | None = Field(
        default=None,
        ge=0,
        description="Wall-clock duration in milliseconds. None when not measured.",
    )
    pr_number: int | None = Field(
        default=None,
        ge=1,
        description=(
            "PR number this receipt was produced for. Used to correlate receipts "
            "to merge gate invocations. None for receipts not tied to a PR."
        ),
    )

    @field_validator("runner", "verifier")
    @classmethod
    def _normalize_identity(cls, v: str) -> str:
        """Strip surrounding whitespace and reject whitespace-only identities.

        Without normalization, ``runner="worker-A"`` and
        ``verifier="worker-A "`` (note trailing space) would compare
        unequal under Rule 1, allowing self-attestation to bypass the
        ADVISORY downgrade. Normalizing here means every consumer of the
        receipt sees a single canonical form.
        """
        normalized = v.strip()
        if not normalized:
            raise ValueError("runner/verifier must contain non-whitespace characters")
        return normalized

    @field_validator("ticket_id")
    @classmethod
    def _validate_ticket_id(cls, v: str) -> str:
        if not _TICKET_ID_RE.match(v):
            raise ValueError(f"ticket_id must match OMN-\\d+, got: {v!r}")
        return v

    @field_validator("commit_sha")
    @classmethod
    def _validate_commit_sha(cls, v: str) -> str:
        # Explicit length + case checks before regex, so uppercase/short/long
        # strings fail identically on every test-runner configuration.
        if not (7 <= len(v) <= 40):
            raise ValueError(f"commit_sha must be 7-40 hex chars (git SHA), got: {v!r}")
        if not all(c in "0123456789abcdef" for c in v):
            raise ValueError(f"commit_sha must be 7-40 hex chars (git SHA), got: {v!r}")
        if not _SHA_RE.match(v):
            raise ValueError(f"commit_sha must be 7-40 hex chars (git SHA), got: {v!r}")
        return v

    @field_validator("run_timestamp")
    @classmethod
    def _validate_tz_aware(cls, v: Any) -> datetime:
        if not isinstance(v, datetime):
            raise ValueError(f"run_timestamp must be datetime, got {type(v).__name__}")
        if v.tzinfo is None:
            raise ValueError("run_timestamp must be timezone-aware (UTC)")
        return v.astimezone(UTC)

    @field_validator("schema_version")
    @classmethod
    def _validate_schema_version(cls, v: str) -> str:
        if not _SEMVER_RE.match(v):
            raise ValueError(
                f"schema_version must be valid SemVer (e.g. '1.0.0'), got: {v!r}"
            )
        return v

    @model_validator(mode="after")
    def enforce_adversarial_invariants(self) -> ModelDodReceipt:
        """Apply the four-rule Centralized Transition Policy.

        Order matters:

        1. Executable check_types with empty stdout raise immediately —
           the receipt is structurally invalid, not just weak. PENDING
           is exempt: by definition the probe was allocated but not yet
           executed, so empty stdout is the expected representation.
        2. Self-attestation (verifier == runner) downgrades PASS to
           ADVISORY. FAIL and PENDING outcomes are preserved — they
           carry distinct meaning (probe ran and failed; probe queued
           but unexecuted) that ADVISORY would erase.
        3. file_exists (and other weak proof types) downgrade PASS to
           ADVISORY. FAIL and PENDING are preserved for the same reason
           as Rule 2.

        Rule (4) — schema_version SemVer match — is enforced as a field
        validator above, before this method runs.
        """
        # Rule 3: executable check_types must have non-empty probe_stdout.
        # PENDING is exempt — an unexecuted probe has no stdout by definition.
        if (
            self.status is not EnumReceiptStatus.PENDING
            and self.check_type in EXECUTABLE_CHECK_TYPES
            and not self.probe_stdout.strip()
        ):
            raise ValueError(
                f"probe_stdout required for executable check_type "
                f"{self.check_type!r}; receipts with empty stdout are "
                f"indistinguishable from probes that never ran"
            )

        # Rule 1: self-attestation downgrades PASS to ADVISORY.
        # FAIL and PENDING are preserved — collapsing them into ADVISORY
        # would erase meaningful outcomes (probe failed, probe queued).
        # ``runner`` and ``verifier`` have already been normalized
        # (whitespace-stripped) by ``_normalize_identity``, so a raw ``==``
        # is sufficient and cannot be bypassed by trailing-space padding.
        if self.verifier == self.runner and self.status is EnumReceiptStatus.PASS:
            object.__setattr__(self, "status", EnumReceiptStatus.ADVISORY)

        # Rule 2: weak-proof check_types downgrade PASS to ADVISORY.
        # FAIL and PENDING are preserved for the same reason.
        if (
            self.check_type in WEAK_PROOF_CHECK_TYPES
            and self.status is EnumReceiptStatus.PASS
        ):
            object.__setattr__(self, "status", EnumReceiptStatus.ADVISORY)

        return self


__all__ = [
    "EXECUTABLE_CHECK_TYPES",
    "ModelDodReceipt",
    "WEAK_PROOF_CHECK_TYPES",
]
