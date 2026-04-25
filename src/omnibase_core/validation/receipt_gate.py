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
    - Receipt status != PASS             → FAIL ("failing receipt")
    - Override token in PR body          → PASS with friction ("override accepted")
    - All checks have PASS receipts      → PASS
"""

from __future__ import annotations

import re
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
OVERRIDE_PATTERN = re.compile(r"\[skip-receipt-gate:\s*(.+?)\]", re.IGNORECASE)


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
    if receipt.status is not EnumReceiptStatus.PASS:
        return fail(f"failing receipt ({receipt.status.value}) at {receipt_path}")

    return ModelReceiptCheckResult(
        ticket_id=ticket_id,
        evidence_item_id=evidence_item_id,
        check_type=check_type,
        passed=True,
        reason="PASS",
    )


def validate_pr_receipts(
    pr_body: str,
    contracts_dir: Path,
    receipts_dir: Path,
    pr_title: str | None = None,
) -> ModelReceiptGateResult:
    """Run the receipt-gate against a PR's body + the repo's contracts + receipts."""
    override = OVERRIDE_PATTERN.search(pr_body)
    if override:
        reason = override.group(1).strip()
        if reason:
            return ModelReceiptGateResult(
                passed=True,
                friction_logged=True,
                message=(
                    f"[skip-receipt-gate] override accepted: {reason!r}. "
                    "FRICTION LOGGED: receipt gate bypassed — every override must be "
                    "tracked and closed within 7 days."
                ),
            )

    ticket_ids = _extract_ticket_ids(pr_body, pr_title)
    if not ticket_ids:
        return ModelReceiptGateResult(
            passed=False,
            message=(
                "RECEIPT GATE FAILED: PR body cites no OMN-XXXX ticket. "
                "Every PR must cite a ticket whose dod_evidence proves the work. "
                "Use [skip-receipt-gate: <reason>] if this is a truly ticket-less "
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
    "validate_pr_receipts",
]
