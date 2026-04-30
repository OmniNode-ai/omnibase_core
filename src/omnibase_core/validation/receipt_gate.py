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

import re
from datetime import UTC, datetime
from pathlib import Path

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

TICKET_PATTERN = re.compile(r"\bOMN-(\d+)\b", re.IGNORECASE)
CLOSING_KEYWORD_PATTERN = re.compile(
    r"\b(?:Closes|Fixes|Resolves|Implements)\b[:\s]+OMN-(\d+)\b",
    re.IGNORECASE,
)
# Matches [skip-receipt-gate: <token>] — token must be a non-whitespace identifier
# to reject free-text reasons. UUID-style, slug, or alphanumeric IDs are all accepted.
OVERRIDE_PATTERN = re.compile(r"\[skip-receipt-gate:\s*(\S+)\s*\]", re.IGNORECASE)


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
        pr_author: GitHub login of the PR author. None disables self-approval check.
        current_repo: Repo name (e.g. ``omnibase_core``) to scope check. None disables.
        current_pr_number: PR number to scope check. None disables.
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

    entry = next(
        (a for a in approvals if isinstance(a, dict) and a.get("id") == approval_id),
        None,
    )
    if entry is None:
        return (
            False,
            f"[skip-receipt-gate] REJECTED: approval id {approval_id!r} not found in allowlist. "
            "Use scripts/grant-skip-approval.sh to create an approved entry.",
        )

    # scope_pr_numbers is REQUIRED — missing or empty means the entry is invalid.
    scope_prs = entry.get("scope_pr_numbers")
    if not scope_prs or not isinstance(scope_prs, list) or len(scope_prs) == 0:
        return (
            False,
            f"[skip-receipt-gate] REJECTED: allowlist entry {approval_id!r} missing or empty "
            "'scope_pr_numbers' — every approval must be scoped to specific PR numbers.",
        )

    # Self-approval: granted_by must not equal the PR author.
    granted_by = entry.get("granted_by", "")
    if (
        pr_author
        and isinstance(granted_by, str)
        and granted_by.strip() == pr_author.strip()
    ):
        return (
            False,
            f"[skip-receipt-gate] REJECTED: self-approval — approval {approval_id!r} was "
            f"granted by {granted_by!r} who is also the PR author. "
            "A different team member must grant the approval.",
        )

    # Expiry check — deterministic: compare against current UTC time.
    expires_at_raw = entry.get("expires_at")
    if expires_at_raw is not None:
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
    scope_repos = entry.get("scope_repos", [])
    if current_repo is not None and isinstance(scope_repos, list) and scope_repos:
        if current_repo not in scope_repos:
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


def validate_pr_receipts(
    pr_body: str,
    contracts_dir: Path,
    receipts_dir: Path,
    pr_title: str | None = None,
    allowlist_path: Path | None = None,
    pr_author: str | None = None,
    current_repo: str | None = None,
    current_pr_number: int | None = None,
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
        pr_author: GitHub login of the PR author. Used for self-approval check.
        current_repo: Repository name (e.g. ``omnibase_core``). Used for scope check.
        current_pr_number: PR number. Used for scope check.
    """
    override = OVERRIDE_PATTERN.search(pr_body)
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
                _check_one_receipt(ticket_id, item_id, check_type, receipts_dir)
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


__all__ = [
    "CLOSING_KEYWORD_PATTERN",
    "OVERRIDE_PATTERN",
    "TICKET_PATTERN",
    "_validate_skip_token",
    "validate_pr_receipts",
]
