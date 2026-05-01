# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Receipt-Gate library — verify every cited ticket's dod_evidence has PASS receipts.

The principle (OMN-TBD, "Enforcement by Receipt"): ticket contracts declare
intent (what must be proved). Receipts declare fact (what was proved). A PR
does not merge unless every dod_evidence check on every cited ticket has a
corresponding PASS receipt at the canonical path.

Canonical receipt path:
    <receipts-dir>/<OMN-XXXX>/<evidence-item-id>/<check-type>.yaml

Decision matrix:
    - No tickets in PR body              → FAIL ("no ticket ref")
    - Evidence-Ticket missing            → FAIL ("missing Evidence-Ticket")
    - PR title ↔ Evidence-Ticket mismatch → FAIL ("PR title mismatch")
    - Branch ↔ Evidence-Ticket mismatch  → FAIL ("branch mismatch")
    - Contract ticket_id ↔ Evidence-Ticket mismatch → FAIL ("contract ticket_id mismatch")
    - Receipt ticket_id ↔ Evidence-Ticket mismatch  → FAIL ("receipt ticket_id mismatch")
    - Ticket has no contract file        → FAIL ("no contract")
    - Contract has no dod_evidence       → FAIL ("no dod_evidence")
    - Receipt missing for any check      → FAIL ("no receipt")
    - Receipt file unparseable           → FAIL ("corrupt receipt")
    - Receipt schema invalid             → FAIL ("invalid receipt")
    - Receipt path↔content mismatch      → FAIL (declared id != lookup id)
    - Receipt missing verifier field     → FAIL ("missing verifier")
    - Receipt missing probe_command/stdout → FAIL ("missing probe_command|probe_stdout")
    - Receipt verifier == runner          → FAIL ("self-attestation: ... ADVISORY")
    - Receipt status != PASS              → FAIL ("failing receipt (ADVISORY|FAIL|PENDING)")
    - Override token: free-text reason   → FAIL (must use approved allowlist id)
    - Override token: unknown id         → FAIL ("unknown approval id")
    - Override token: expired            → FAIL ("approval expired")
    - Override token: scope mismatch     → FAIL ("approval not scoped to this repo/PR")
    - Override token: self-approved      → FAIL ("self-approval rejected")
    - Override token: valid allowlist id → PASS with friction ("override accepted")
    - All checks have PASS receipts      → PASS

Adversarial invariants (OMN-9788)
---------------------------------
The gate enforces four invariants on every receipt before accepting it as
proof. These mirror the OMN-9786 ``ModelDodReceipt`` model invariants but
are surfaced as gate-level errors so the failure message tells the operator
exactly which adversarial guarantee was missed:

1. ``verifier`` field MUST be present and non-empty (rejects legacy /
   pre-OMN-9786 receipts that elide the field).
2. ``probe_command`` AND ``probe_stdout`` fields MUST be present; both
   must be non-whitespace after stripping.
3. ``verifier`` MUST differ from ``runner`` (rejects self-attestation).
4. Final ``status`` MUST be ``PASS`` (rejects ADVISORY, FAIL, PENDING).

Invariants 1-3 are enforced as pre-schema lookups so missing-field
errors mention the field name even when other validation errors would
otherwise mask the problem.

Skip-token allowlist (OMN-10417)
---------------------------------
``[skip-receipt-gate: <approval-id>]`` requires ``<approval-id>`` to exist
in ``onex_change_control/allowlists/skip_token_approvals.yaml``.  Free-text
reasons are rejected.  Allowlist schema:

    approvals:
      - id: <str>
        granted_by: <github-login>
        granted_at: <ISO-8601>
        expires_at: <ISO-8601>
        scope_repos: [<repo>, ...]
        scope_pr_numbers: [<int>, ...]   # REQUIRED

Rejection criteria (all hard FAIL, no bypass):
    - ``approval-id`` not found in allowlist
    - ``expires_at`` in the past
    - current repo not in ``scope_repos``
    - current PR not in ``scope_pr_numbers``
    - ``granted_by == pr_author`` (self-approval)
    - ``scope_pr_numbers`` missing or empty in the allowlist entry

Every accepted bypass logs to CI output with the allowlist entry id, granted_by,
and scope for audit traceability.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from omnibase_core.enums.ticket.enum_receipt_status import EnumReceiptStatus
from omnibase_core.models.contracts.ticket.model_dod_receipt import ModelDodReceipt
from omnibase_core.models.contracts.ticket.model_receipt_check_result import (
    ModelReceiptCheckResult,
)
from omnibase_core.models.contracts.ticket.model_receipt_gate_result import (
    ModelReceiptGateResult,
)
from omnibase_core.validation.completion_verify import verify as _completion_verify

# PRs opened after this UTC datetime must include contract_sha256 in receipts;
# earlier PRs get ADVISORY downgrade for the 7-day legacy window (OMN-10421).
_CONTRACT_SHA256_REQUIRED_AFTER = datetime(2026, 4, 30, 0, 0, 0, tzinfo=UTC)

TICKET_PATTERN = re.compile(r"\bOMN-(\d+)\b", re.IGNORECASE)
CLOSING_KEYWORD_PATTERN = re.compile(
    r"\b(?:Closes|Fixes|Resolves|Implements)\b[:\s]+OMN-(\d+)\b",
    re.IGNORECASE,
)
# Matches any real [skip-*: ...] bypass token (OMN-10347: Rule #10 enforcement).
# Angle-bracket placeholders such as [skip-receipt-gate: <token>] are docs
# examples, not executable bypass tokens.
SKIP_TOKEN_PATTERN = re.compile(r"\[skip-[a-zA-Z][^\]<>]*\]", re.IGNORECASE)
# Matches [skip-receipt-gate: <token>] — token must be a safe identifier to
# reject free-text reasons and placeholder examples such as "<token>".
OVERRIDE_PATTERN = re.compile(
    r"\[skip-receipt-gate:\s*([A-Za-z0-9._-]+)\s*\]",
    re.IGNORECASE,
)
# Inline marker pattern used only to reject the superseded approval syntax.
# Receipt-gate bypass requires the central allowlist checked by _validate_skip_token.
ALLOWLIST_PATTERN = re.compile(r"#\s*skip-token-allowed:\s*(\S+)", re.IGNORECASE)
# Matches "Evidence-Ticket: OMN-XXXX" line in PR body (OMN-10420 identity binding).
EVIDENCE_TICKET_PATTERN = re.compile(
    r"^Evidence-Ticket:\s*(OMN-\d+)\s*$",
    re.IGNORECASE | re.MULTILINE,
)
# Matches "Evidence-Source: ..." line — presence triggers identity binding (OMN-10420).
EVIDENCE_SOURCE_PATTERN = re.compile(
    r"^Evidence-Source:\s*\S",
    re.IGNORECASE | re.MULTILINE,
)

# Matches "Evidence-Source: OCC#1234" or "Evidence-Source: <40-char-sha>" lines.
# OCC#NNN form references an open PR by number; SHA form references a merged commit.
# Requires at least one space after the colon, consistent with the workflow grep.
EVIDENCE_SOURCE_OCC_PR_PATTERN = re.compile(
    r"^Evidence-Source:\s+OCC#(\d+)\s*$",
    re.IGNORECASE | re.MULTILINE,
)
EVIDENCE_SOURCE_SHA_PATTERN = re.compile(
    r"^Evidence-Source:\s+([0-9a-f]{7,40})\s*$",
    re.IGNORECASE | re.MULTILINE,
)
# Detects any Evidence-Source line (used to distinguish "present but invalid" from "absent").
EVIDENCE_SOURCE_ANY_PATTERN = re.compile(
    r"^Evidence-Source:\s+\S",
    re.IGNORECASE | re.MULTILINE,
)

# The SHA of the commit that merged OMN-10419 (Task 9 / T6a). PRs opened after
# this SHA are required to include Evidence-Source. PRs opened before it are
# grandfathered — the cutoff check in _is_evidence_source_required returns False
# when pr_created_at predates this merge.
#
# Placeholder value — replaced by the actual merge SHA when this PR lands. The
# workflow resolves the cutoff via the OCC_PINNING_CUTOFF_SHA env var injected
# by the Check out onex_change_control step.
EVIDENCE_SOURCE_CUTOFF_SHA = "PENDING_MERGE"


def parse_evidence_source(pr_body: str) -> tuple[str | None, str | None]:
    """Parse the Evidence-Source line from a PR body.

    Returns:
        ``(occ_pr_number_str, sha)`` where exactly one is set, or ``(None, None)``
        if no Evidence-Source line is present.

        - OCC PR form ``OCC#1234``: returns ``("1234", None)``.
        - SHA form ``<sha>``: returns ``(None, "<sha>")``.
        - Present but invalid form: returns ``(None, None)`` with the caller
          responsible for detecting the presence via EVIDENCE_SOURCE_ANY_PATTERN.
    """
    for line in pr_body.splitlines():
        if not line.lower().startswith("evidence-source:"):
            continue
        if m_pr := EVIDENCE_SOURCE_OCC_PR_PATTERN.fullmatch(line):
            return (m_pr.group(1), None)
        if m_sha := EVIDENCE_SOURCE_SHA_PATTERN.fullmatch(line):
            return (None, m_sha.group(1))
        break
    return (None, None)


def compute_contract_sha256(contract_path: Path) -> str:
    """Return the SHA-256 hex digest of a contract YAML file's raw bytes."""
    return hashlib.sha256(contract_path.read_bytes()).hexdigest()


def _prefixed_contract_sha256(contract_path: Path) -> str:
    """Return the canonical contract hash value used by DoD receipts."""
    return f"sha256:{compute_contract_sha256(contract_path)}"


def _extract_ticket_ids(pr_body: str, pr_title: str | None = None) -> list[str]:
    """Return sorted unique ticket IDs cited by this PR.

    Precedence: body closing-keyword matches (CLOSING_KEYWORD_PATTERN) are
    checked first; if any are found they are returned exclusively (sorted,
    deduplicated, prefixed "OMN-").  Only when the body yields no matches does
    the function fall back to scanning pr_title with TICKET_PATTERN.  Returns
    [] when neither source yields a match.

    Args:
        pr_body: Full PR description text.
        pr_title: Optional PR title used as fallback when body has no matches.

    Returns:
        Sorted list of "OMN-<N>" strings, empty if none found.
    """
    closing_matches = CLOSING_KEYWORD_PATTERN.findall(pr_body)
    if closing_matches:
        return sorted({f"OMN-{m}" for m in closing_matches})
    # fallback-ok: Title ticket extraction is only used when body has no closing-keyword ticket.
    if pr_title:
        title_matches = TICKET_PATTERN.findall(pr_title)
        if title_matches:
            return sorted({f"OMN-{m}" for m in title_matches})
    return []


def _iter_dod_evidence(contract_data: object) -> list[tuple[str, str, str]]:
    """Yield (evidence_item_id, check_type, check_value) triples from contract YAML."""
    triples: list[tuple[str, str, str]] = []
    if not isinstance(contract_data, dict):
        return triples
    dod = contract_data.get("dod_evidence", [])
    if not isinstance(dod, list):
        return triples
    for item in dod:
        if not isinstance(item, dict):
            continue
        item_id = item.get("id")
        checks = item.get("checks", [])
        if not isinstance(item_id, str) or not isinstance(checks, list):
            continue
        for check in checks:
            if not isinstance(check, dict):
                continue
            ctype = check.get("check_type")
            cvalue = check.get("check_value")
            if isinstance(ctype, str) and isinstance(cvalue, str):
                triples.append((item_id, ctype, cvalue))
    return triples


def _check_adversarial_invariants_raw(raw: object, receipt_path: Path) -> str | None:
    """Pre-schema guard for the adversarial fields (OMN-9788).

    Runs before ``ModelDodReceipt.model_validate`` so missing-field errors
    mention the field name explicitly (``verifier``, ``probe_command``,
    ``probe_stdout``). Without this, pydantic's "Field required" message
    surfaces all missing fields together and the operator cannot tell
    which adversarial invariant was violated.

    Returns:
        ``None`` if the raw payload has all four required adversarial
        fields populated with non-whitespace strings. Otherwise an
        operator-facing failure reason naming the missing/empty field.
    """
    if not isinstance(raw, dict):
        return None  # downstream schema validation will catch non-dict
    for field in ("verifier", "probe_command", "probe_stdout"):
        if field not in raw:
            return (
                f"receipt at {receipt_path} missing required adversarial field "
                f"{field!r} (OMN-9786 invariant)"
            )
    # verifier and probe_command must be non-whitespace; probe_stdout may be
    # empty for non-executable check_types, so the model layer enforces the
    # executable-only stdout rule.
    for field in ("verifier", "probe_command"):
        value = raw.get(field)
        if not isinstance(value, str) or not value.strip():
            return (
                f"receipt at {receipt_path} field {field!r} is empty or "
                f"whitespace-only (OMN-9786 invariant)"
            )
    return None


def _check_adversarial_invariants_validated(
    receipt: ModelDodReceipt, receipt_path: Path
) -> str | None:
    """Post-schema adversarial check (OMN-9788).

    The model layer downgrades ``verifier == runner`` PASS receipts to
    ADVISORY and weak-proof check_types likewise; this function reports
    the resulting status with a message naming the adversarial rule so
    the operator sees ``advisory`` or ``self-attestation`` rather than
    a bare status code.

    Returns:
        ``None`` if the receipt resolves to ``EnumReceiptStatus.PASS``.
        Otherwise an operator-facing failure reason.
    """
    # Identities are already whitespace-stripped by the model's
    # ``_normalize_identity`` field validator.
    if receipt.verifier == receipt.runner:
        # Model auto-downgraded PASS → ADVISORY; surface the cause.
        return (
            f"receipt at {receipt_path} self-attestation rejected: "
            f"verifier={receipt.verifier!r} == runner={receipt.runner!r} "
            f"(status auto-downgraded to ADVISORY by OMN-9786 transition policy)"
        )
    if receipt.status is EnumReceiptStatus.ADVISORY:
        return (
            f"failing receipt (ADVISORY) at {receipt_path}: advisory-only "
            f"proof does not satisfy the receipt-gate; an independent "
            f"verifier must sign off with status=PASS"
        )
    if receipt.status is EnumReceiptStatus.PENDING:
        return (
            f"failing receipt (PENDING) at {receipt_path}: probe was "
            f"allocated but not executed; rerun the probe and produce a "
            f"PASS receipt before merging"
        )
    if receipt.status is not EnumReceiptStatus.PASS:
        return f"failing receipt ({receipt.status.value}) at {receipt_path}"
    return None


def _check_one_receipt(
    ticket_id: str,
    evidence_item_id: str,
    check_type: str,
    receipts_dir: Path,
    contract_path: Path | None = None,
    pr_opened_at: datetime | None = None,
) -> ModelReceiptCheckResult:
    """Verify exactly one (ticket, evidence, check) has a PASS receipt on disk."""
    receipt_path = receipts_dir / ticket_id / evidence_item_id / f"{check_type}.yaml"

    def fail(reason: str) -> ModelReceiptCheckResult:
        return ModelReceiptCheckResult(
            ticket_id=ticket_id,
            evidence_item_id=evidence_item_id,
            check_type=check_type,
            passed=False,
            reason=reason,
        )

    if not receipt_path.exists():
        return fail(f"no receipt at {receipt_path}")

    try:
        with receipt_path.open(encoding="utf-8") as fh:
            raw = yaml.safe_load(fh)
    except (yaml.YAMLError, OSError) as e:
        return fail(f"corrupt receipt at {receipt_path}: {e}")

    # Pre-schema adversarial guard: missing/empty verifier, probe_command,
    # probe_stdout fields must produce a clear "missing <field>" message
    # before pydantic's bulk "Field required" error fires (OMN-9788).
    adversarial_raw_failure = _check_adversarial_invariants_raw(raw, receipt_path)
    if adversarial_raw_failure is not None:
        return fail(adversarial_raw_failure)

    try:
        receipt = ModelDodReceipt.model_validate(raw)
    except ValidationError as e:
        return fail(f"invalid receipt schema at {receipt_path}: {e}")

    if receipt.ticket_id != ticket_id:
        return fail(
            f"receipt at {receipt_path} declares ticket_id={receipt.ticket_id!r}, "
            f"expected {ticket_id!r}"
        )
    if receipt.evidence_item_id != evidence_item_id:
        return fail(
            f"receipt at {receipt_path} declares evidence_item_id="
            f"{receipt.evidence_item_id!r}, expected {evidence_item_id!r}"
        )
    if receipt.check_type != check_type:
        return fail(
            f"receipt at {receipt_path} declares check_type={receipt.check_type!r}, "
            f"expected {check_type!r}"
        )

    # Post-schema adversarial guard: surface ADVISORY / PENDING / self-
    # attestation with a message that names the rule (OMN-9788).
    adversarial_validated_failure = _check_adversarial_invariants_validated(
        receipt, receipt_path
    )
    if adversarial_validated_failure is not None:
        return fail(adversarial_validated_failure)

    # Hash-binding check (OMN-10421, invariant I4): verify the contract has
    # not mutated since this receipt was produced. Only active when the caller
    # supplies pr_opened_at — callers that omit it get no hash enforcement
    # (backward-compatible with pre-OMN-10421 call sites).
    if (
        contract_path is not None
        and contract_path.exists()
        and pr_opened_at is not None
    ):
        actual_sha = _prefixed_contract_sha256(contract_path)
        if receipt.contract_sha256 is None:
            is_post_cutoff = pr_opened_at >= _CONTRACT_SHA256_REQUIRED_AFTER
            if is_post_cutoff:
                return fail(
                    f"receipt at {receipt_path} missing required contract_sha256 field "
                    f"(OMN-10421): receipts produced after {_CONTRACT_SHA256_REQUIRED_AFTER.date()} "
                    "must record the contract hash. Rerun probes to produce a new receipt."
                )
            # Pre-cutoff PR: ADVISORY downgrade — field expected soon but not yet required.
            return ModelReceiptCheckResult(
                ticket_id=ticket_id,
                evidence_item_id=evidence_item_id,
                check_type=check_type,
                passed=False,
                reason=(
                    f"receipt at {receipt_path} missing contract_sha256 (ADVISORY — "
                    "legacy receipt within 7-day migration window; rerun probes to bind "
                    "the receipt to the current contract hash)"
                ),
            )
        if receipt.contract_sha256 != actual_sha:
            return fail(
                f"contract mutated post-receipt; rerun probes. "
                f"receipt contract_sha256={receipt.contract_sha256!r} but "
                f"sha256({contract_path})={actual_sha!r}"
            )

    return ModelReceiptCheckResult(
        ticket_id=ticket_id,
        evidence_item_id=evidence_item_id,
        check_type=check_type,
        passed=True,
        reason="PASS",
    )


def _validate_skip_token(
    approval_id: str,
    pr_author: str | None,
    current_repo: str | None,
    current_pr_number: int | None,
    allowlist_path: Path,
) -> tuple[bool, str]:
    """Validate a skip-receipt-gate approval ID against the allowlist.

    Args:
        approval_id: The bare identifier from ``[skip-receipt-gate: <id>]``.
        pr_author: GitHub login of the PR author for self-approval checks.
        current_repo: Repo name (e.g. ``omnibase_core``) to scope check.
        current_pr_number: PR number to scope check.
        allowlist_path: Path to ``skip_token_approvals.yaml``.

    Returns:
        ``(True, audit_message)`` when the token is valid and accepted.
        ``(False, rejection_reason)`` for every rejection case.
    """
    if not allowlist_path.exists():
        return (
            False,
            f"[skip-receipt-gate] REJECTED: allowlist not found at {allowlist_path}. "
            "Use scripts/grant-skip-approval.sh to create an approved entry.",
        )

    try:
        with allowlist_path.open(encoding="utf-8") as fh:
            raw = yaml.safe_load(fh)
    except (yaml.YAMLError, OSError) as e:
        return (
            False,
            f"[skip-receipt-gate] REJECTED: allowlist corrupt at {allowlist_path}: {e}",
        )

    if not isinstance(raw, dict):
        return (
            False,
            f"[skip-receipt-gate] REJECTED: allowlist at {allowlist_path} is not a YAML mapping",
        )

    approvals = raw.get("approvals", [])
    if not isinstance(approvals, list):
        return (
            False,
            "[skip-receipt-gate] REJECTED: allowlist 'approvals' key is not a list",
        )

    matches = [
        a for a in approvals if isinstance(a, dict) and a.get("id") == approval_id
    ]
    if not matches:
        return (
            False,
            f"[skip-receipt-gate] REJECTED: approval id {approval_id!r} not found in allowlist. "
            "Use scripts/grant-skip-approval.sh to create an approved entry.",
        )
    if len(matches) > 1:
        return (
            False,
            f"[skip-receipt-gate] REJECTED: approval id {approval_id!r} appears "
            f"{len(matches)} times in the allowlist. Approval ids must be unique.",
        )
    entry = matches[0]

    # scope_pr_numbers is REQUIRED — missing or empty means the entry is invalid.
    scope_prs = entry.get("scope_pr_numbers")
    if not scope_prs or not isinstance(scope_prs, list) or len(scope_prs) == 0:
        return (
            False,
            f"[skip-receipt-gate] REJECTED: allowlist entry {approval_id!r} missing or empty "
            "'scope_pr_numbers' — every approval must be scoped to specific PR numbers.",
        )

    # Self-approval: granted_by must not equal the PR author.
    granted_by_raw = entry.get("granted_by")
    if not isinstance(granted_by_raw, str) or not granted_by_raw.strip():
        return (
            False,
            f"[skip-receipt-gate] REJECTED: allowlist entry {approval_id!r} missing or empty "
            "'granted_by' — every approval must record the approver login.",
        )
    granted_by = granted_by_raw.strip()
    if pr_author and granted_by.casefold() == pr_author.strip().casefold():
        return (
            False,
            f"[skip-receipt-gate] REJECTED: self-approval — approval {approval_id!r} was "
            f"granted by {granted_by!r} who is also the PR author. "
            "A different team member must grant the approval.",
        )

    # Expiry check — deterministic: compare against current UTC time.
    expires_at_raw = entry.get("expires_at")
    if expires_at_raw is None:
        return (
            False,
            f"[skip-receipt-gate] REJECTED: allowlist entry {approval_id!r} missing "
            "'expires_at' — every approval must expire.",
        )
    try:
        if isinstance(expires_at_raw, str):
            expires_at = datetime.fromisoformat(expires_at_raw)
        elif isinstance(expires_at_raw, datetime):
            expires_at = expires_at_raw
        else:
            # error-ok: internal sentinel immediately re-caught by enclosing except (ValueError, TypeError)
            raise ValueError(f"unexpected type: {type(expires_at_raw)}")
        # Make timezone-aware if naive (assume UTC).
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        now_utc = datetime.now(tz=UTC)
        if now_utc > expires_at:
            return (
                False,
                f"[skip-receipt-gate] REJECTED: approval {approval_id!r} expired at "
                f"{expires_at.isoformat()} (now={now_utc.isoformat()}). "
                "Use scripts/grant-skip-approval.sh to create a new entry.",
            )
    except (ValueError, TypeError) as e:
        return (
            False,
            f"[skip-receipt-gate] REJECTED: approval {approval_id!r} has unparseable "
            f"expires_at {expires_at_raw!r}: {e}",
        )

    # Repo scope check.
    scope_repos = entry.get("scope_repos")
    if not isinstance(scope_repos, list) or len(scope_repos) == 0:
        return (
            False,
            f"[skip-receipt-gate] REJECTED: allowlist entry {approval_id!r} missing or empty "
            "'scope_repos' — every approval must be scoped to specific repos.",
        )
    if current_repo is not None and current_repo not in scope_repos:
        return (
            False,
            f"[skip-receipt-gate] REJECTED: approval {approval_id!r} is scoped to repos "
            f"{scope_repos!r} but current repo is {current_repo!r}.",
        )

    # PR number scope check.
    if current_pr_number is not None and isinstance(scope_prs, list):
        if current_pr_number not in scope_prs:
            return (
                False,
                f"[skip-receipt-gate] REJECTED: approval {approval_id!r} is scoped to PR numbers "
                f"{scope_prs!r} but current PR is #{current_pr_number}.",
            )

    audit_msg = (
        f"[skip-receipt-gate] BYPASS ACCEPTED: approval={approval_id!r} "
        f"granted_by={granted_by!r} "
        f"scope_repos={scope_repos!r} scope_pr_numbers={scope_prs!r}. "
        "FRICTION LOGGED: receipt gate bypassed — every override must be "
        "tracked and closed within 7 days."
    )
    return (True, audit_msg)


def _verify_ticket_identity(
    evidence_ticket: str,
    pr_title: str | None,
    branch_name: str | None,
    contracts_dir: Path,
    receipts_dir: Path,
) -> str | None:
    """Verify that the Evidence-Ticket is consistent across all four identity axes.

    This enforces invariant I3 (OMN-10420): evidence must correspond to the same
    ticket as the PR.  Checks (in order):

    1. PR title contains Evidence-Ticket (case-insensitive).
    2. Branch name contains Evidence-Ticket (case-insensitive).
    3. ``contracts/<ticket-id>.yaml`` exists and its ``ticket_id`` field matches.
    4. Every receipt under ``drift/dod_receipts/<ticket-id>/`` has a ``ticket_id``
       field that matches.

    Args:
        evidence_ticket: Normalised ticket id (e.g. "OMN-10420") from the ``Evidence-Ticket:`` line.
        pr_title: PR title; checked for case-insensitive ticket reference.
        branch_name: Git branch name; checked for case-insensitive ticket reference.
        contracts_dir: Directory containing contract YAML files.
        receipts_dir: Root of the receipt tree.

    Returns:
        ``None`` when all axes are consistent.  Otherwise an operator-facing failure
        reason identifying exactly which axis mismatched.
    """
    ticket_upper = evidence_ticket.upper()

    # Axis 1: PR title.
    if pr_title is not None:
        if ticket_upper not in pr_title.upper():
            return (
                f"IDENTITY BINDING FAILED: PR title does not reference {evidence_ticket}. "
                f"PR title={pr_title!r}, Evidence-Ticket={evidence_ticket!r}. "
                "The PR title must contain the same ticket cited in Evidence-Ticket."
            )

    # Axis 2: Branch name.
    if branch_name is not None:
        if ticket_upper not in branch_name.upper():
            return (
                f"IDENTITY BINDING FAILED: branch name does not reference {evidence_ticket}. "
                f"branch={branch_name!r}, Evidence-Ticket={evidence_ticket!r}. "
                "The branch must be named for the same ticket cited in Evidence-Ticket."
            )

    # Axis 3: Contract ticket_id field.
    contract_path = contracts_dir / f"{evidence_ticket}.yaml"
    if contract_path.exists():
        try:
            with contract_path.open(encoding="utf-8") as fh:
                contract_data = yaml.safe_load(fh)
        except (yaml.YAMLError, OSError) as e:
            return f"IDENTITY BINDING FAILED: cannot read contract {contract_path}: {e}"
        if isinstance(contract_data, dict):
            contract_ticket_id = contract_data.get("ticket_id")
            if contract_ticket_id is not None:
                if str(contract_ticket_id).upper() != ticket_upper:
                    return (
                        f"IDENTITY BINDING FAILED: contract {contract_path} declares "
                        f"ticket_id={contract_ticket_id!r} but Evidence-Ticket is "
                        f"{evidence_ticket!r}. The contract ticket_id must match."
                    )

    # Axis 4: Receipt ticket_id fields.
    receipt_ticket_dir = receipts_dir / evidence_ticket
    if receipt_ticket_dir.exists():
        for receipt_path in receipt_ticket_dir.rglob("*.yaml"):
            try:
                with receipt_path.open(encoding="utf-8") as fh:
                    raw = yaml.safe_load(fh)
            except (yaml.YAMLError, OSError):
                continue  # corrupt receipts caught by _check_one_receipt
            if not isinstance(raw, dict):
                continue
            receipt_tid = raw.get("ticket_id")
            if receipt_tid is not None and str(receipt_tid).upper() != ticket_upper:
                return (
                    f"IDENTITY BINDING FAILED: receipt {receipt_path} declares "
                    f"ticket_id={receipt_tid!r} but Evidence-Ticket is "
                    f"{evidence_ticket!r}. All receipts must belong to the same ticket."
                )

    return None


def validate_pr_receipts(
    pr_body: str,
    contracts_dir: Path,
    receipts_dir: Path,
    pr_title: str | None = None,
    allowlist_path: Path | None = None,
    pr_author: str | None = None,
    current_repo: str | None = None,
    current_pr_number: int | None = None,
    pr_opened_at: datetime | None = None,
    evidence_ticket: str | None = None,
    branch_name: str | None = None,
) -> ModelReceiptGateResult:
    """Run the receipt-gate against a PR's body + the repo's contracts + receipts.

    Args:
        pr_body: Full PR description text.
        contracts_dir: Directory containing OMN-<ticket-id>.yaml ticket contracts.
        receipts_dir: Directory tree containing ModelDodReceipt YAML files.
        pr_title: Optional PR title; used as fallback ticket extraction source.
        allowlist_path: Path to ``onex_change_control/allowlists/skip_token_approvals.yaml``.
            When None, any ``[skip-receipt-gate: <id>]`` token is rejected because
            there is no allowlist to verify against.
        pr_author: GitHub login of the PR author. Required for skip tokens.
        current_repo: Repository name (e.g. ``omnibase_core``). Required for skip tokens.
        current_pr_number: PR number. Required for skip tokens.
        pr_opened_at: UTC datetime when the PR was opened. Used to determine whether
            missing ``contract_sha256`` is a hard FAIL (post-cutoff) or ADVISORY
            (within the 7-day legacy migration window). When None, the hash-binding
            check is skipped because no PR-open timestamp is available.
        evidence_ticket: Ticket id (e.g. "OMN-10420") from the ``Evidence-Ticket:``
            PR body line.  When provided (or auto-detected from the PR body), identity
            binding is enforced across all four axes: PR title, branch name, contract
            ticket_id, receipt ticket_id.  When ``None``, auto-detected from the
            ``Evidence-Ticket:`` line in ``pr_body``; if that line is present and this
            arg is also ``None`` the detected value is used.  If neither source yields
            a value and ``Evidence-Source`` is present, the gate fails.
        branch_name: Git branch name for axis-2 identity binding.
    """
    override = OVERRIDE_PATTERN.search(pr_body)
    skip_match = SKIP_TOKEN_PATTERN.search(pr_body)
    if skip_match and override is None:
        return ModelReceiptGateResult(
            passed=False,
            message=(
                f"RECEIPT GATE FAILED: PR body contains a [skip-*] bypass token "
                f"({skip_match.group(0)!r}) that is not an approved receipt-gate "
                "allowlist token. Use [skip-receipt-gate: <approval-id>] with "
                "a central allowlist entry scoped to this repo and PR, or add "
                "dod_evidence proving the work."
            ),
        )
    if override:
        approval_id = override.group(1).strip()
        if allowlist_path is None:
            return ModelReceiptGateResult(
                passed=False,
                message=(
                    f"[skip-receipt-gate] REJECTED: token {approval_id!r} present but "
                    "no allowlist_path provided to the gate. "
                    "Pass --allowlist-path pointing to "
                    "onex_change_control/allowlists/skip_token_approvals.yaml."
                ),
            )
        missing_context: list[str] = []
        if not isinstance(pr_author, str) or not pr_author.strip():
            missing_context.append("pr_author")
        if not isinstance(current_repo, str) or not current_repo.strip():
            missing_context.append("current_repo")
        if current_pr_number is None:
            missing_context.append("current_pr_number")
        if missing_context:
            return ModelReceiptGateResult(
                passed=False,
                message=(
                    f"[skip-receipt-gate] REJECTED: token {approval_id!r} present but "
                    f"required PR context is missing: {', '.join(missing_context)}. "
                    "Pass --pr-author, --current-repo, and --current-pr-number so "
                    "self-approval and repo/PR scope checks cannot be bypassed."
                ),
            )
        accepted, message = _validate_skip_token(
            approval_id=approval_id,
            pr_author=pr_author,
            current_repo=current_repo,
            current_pr_number=current_pr_number,
            allowlist_path=allowlist_path,
        )
        if not accepted:
            return ModelReceiptGateResult(passed=False, message=message)
        return ModelReceiptGateResult(
            passed=True,
            friction_logged=True,
            message=message,
        )

    # Identity binding (OMN-10420 / I3): enforced when Evidence-Source is present in the
    # PR body (T6a pairing) OR when evidence_ticket is explicitly passed to the gate.
    # Without Evidence-Source the caller has not opted into OCC pinning yet, so identity
    # binding is skipped (backward-compatible with pre-T6a PRs).
    has_evidence_source = bool(EVIDENCE_SOURCE_PATTERN.search(pr_body))
    if has_evidence_source or evidence_ticket is not None:
        resolved_evidence_ticket = evidence_ticket
        if resolved_evidence_ticket is None:
            et_match = EVIDENCE_TICKET_PATTERN.search(pr_body)
            if et_match:
                resolved_evidence_ticket = et_match.group(1).upper()

        if resolved_evidence_ticket is None:
            return ModelReceiptGateResult(
                passed=False,
                message=(
                    "RECEIPT GATE FAILED: PR body contains 'Evidence-Source' but is "
                    "missing an 'Evidence-Ticket: OMN-XXXX' line. Every PR with "
                    "Evidence-Source must also declare Evidence-Ticket so the gate can "
                    "verify the evidence is for the same ticket as the PR. "
                    "Add 'Evidence-Ticket: OMN-XXXX' to the PR body."
                ),
            )

        identity_failure = _verify_ticket_identity(
            evidence_ticket=resolved_evidence_ticket,
            pr_title=pr_title,
            branch_name=branch_name,
            contracts_dir=contracts_dir,
            receipts_dir=receipts_dir,
        )
        if identity_failure is not None:
            return ModelReceiptGateResult(passed=False, message=identity_failure)

    ticket_ids = _extract_ticket_ids(pr_body, pr_title)
    if not ticket_ids:
        return ModelReceiptGateResult(
            passed=False,
            message=(
                "RECEIPT GATE FAILED: PR body cites no OMN-XXXX ticket. "
                "Every PR must cite a ticket whose dod_evidence proves the work. "
                "Use [skip-receipt-gate: <approval-id>] if this is a truly ticket-less "
                "change (rare — chore/docs/emergency hotfix)."
            ),
        )

    all_checks: list[ModelReceiptCheckResult] = []
    for ticket_id in ticket_ids:
        contract_path = contracts_dir / f"{ticket_id}.yaml"
        if not contract_path.exists():
            all_checks.append(
                ModelReceiptCheckResult(
                    ticket_id=ticket_id,
                    evidence_item_id="*",
                    check_type="*",
                    passed=False,
                    reason=f"no contract at {contract_path}",
                )
            )
            continue

        try:
            with contract_path.open(encoding="utf-8") as fh:
                contract_data = yaml.safe_load(fh)
        except (yaml.YAMLError, OSError) as e:
            all_checks.append(
                ModelReceiptCheckResult(
                    ticket_id=ticket_id,
                    evidence_item_id="*",
                    check_type="*",
                    passed=False,
                    reason=f"corrupt contract at {contract_path}: {e}",
                )
            )
            continue

        triples = _iter_dod_evidence(contract_data)
        if not triples:
            all_checks.append(
                ModelReceiptCheckResult(
                    ticket_id=ticket_id,
                    evidence_item_id="*",
                    check_type="*",
                    passed=False,
                    reason=f"contract {contract_path} has no dod_evidence items",
                )
            )
            continue

        for item_id, check_type, _check_value in triples:
            all_checks.append(
                _check_one_receipt(
                    ticket_id,
                    item_id,
                    check_type,
                    receipts_dir,
                    contract_path=contract_path,
                    pr_opened_at=pr_opened_at,
                )
            )

    failures = [c for c in all_checks if not c.passed]
    if failures:
        parts = ["RECEIPT GATE FAILED. Missing or non-PASS receipts:"]
        parts.extend(
            f"  - {c.ticket_id} / {c.evidence_item_id} / {c.check_type}: {c.reason}"
            for c in failures
        )
        parts.append(
            "Fix: run the check, produce a ModelDodReceipt at the canonical path, "
            "then push. Never --skip-receipt-gate silently."
        )
        return ModelReceiptGateResult(
            passed=False,
            checks=all_checks,
            tickets_checked=ticket_ids,
            message="\n".join(parts),
        )

    return ModelReceiptGateResult(
        passed=True,
        checks=all_checks,
        tickets_checked=ticket_ids,
        message=(
            f"RECEIPT GATE PASSED: {len(all_checks)} check(s) across "
            f"{len(ticket_ids)} ticket(s) all have PASS receipts."
        ),
    )


EVIDENCE_HANDLERS: dict[str, Callable[..., Any]] = {}
EVIDENCE_HANDLERS["completion-verify"] = _completion_verify


__all__ = [
    "ALLOWLIST_PATTERN",
    "CLOSING_KEYWORD_PATTERN",
    "EVIDENCE_HANDLERS",
    "EVIDENCE_SOURCE_ANY_PATTERN",
    "EVIDENCE_SOURCE_CUTOFF_SHA",
    "EVIDENCE_SOURCE_OCC_PR_PATTERN",
    "EVIDENCE_SOURCE_PATTERN",
    "EVIDENCE_SOURCE_SHA_PATTERN",
    "EVIDENCE_TICKET_PATTERN",
    "OVERRIDE_PATTERN",
    "SKIP_TOKEN_PATTERN",
    "TICKET_PATTERN",
    "_CONTRACT_SHA256_REQUIRED_AFTER",
    "compute_contract_sha256",
    "parse_evidence_source",
    "validate_pr_receipts",
]
