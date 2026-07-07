# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Receipt-attestation diff-consistency gate (OMN-13927).

A DoD receipt may *claim* things about its own PR diff — "net-new-only", "no
existing receipts or the contract are modified". The per-receipt honesty gate
(:mod:`omnibase_core.validation.validator_receipt_honesty`, rules A-E) is a pure
``f(receipt) -> violations`` with **zero diff context**, so it structurally
cannot catch a receipt that lies about its own diff. That gap produced the
OMN-13917 incident: OCC #3551 merged a self-binding receipt attesting
net-new-only while the same PR's diff modified ``contracts/OMN-13501.yaml`` and
four pre-existing merged receipts.

This module closes the residual **attestation-honesty** class. It is deliberately
kept out of ``check_receipt_honesty`` (which must stay pure per-receipt); a
diff-consistency check needs the PR ``--name-status`` diff, so it lives here with
its own pure core (:func:`check_diff_consistency`) and a thin git-free CLI.

Relationship to append-only (OMN-13888,
:mod:`omnibase_core.validation.validator_occ_append_only`): append-only removes
the *ability* to rewrite a merged contract entry or receipt file. Diff-consistency
closes a different gap — a receipt that *lies about its diff* staying a trusted
forensic artifact. The ``NET_NEW_ONLY`` attestation is the append-only claim at
the receipt-attestation level: it asserts the diff touched nothing pre-existing.

Scope (v1 — closed enum, NOT NLP). Two trigger paths:

* **Structured (authoritative):** ``diff_attestations: list[EnumDiffAttestation]``
  on :class:`~omnibase_core.models.contracts.ticket.model_dod_receipt.ModelDodReceipt`.
* **Legacy free-text (high-precision only):** two regexes over ``actual_output`` of
  a receipt ADDED in the PR ⇒ enforce ``NET_NEW_ONLY``. No match ⇒ no check.

General free-text claim extraction is explicitly descoped (unbounded NLP,
false-positive prone). A contradicted attestation is a hard FAIL (exit 1, blocks
merge). No skip token, no allowlist — a merged false receipt is corrected via the
OMN-13888 supersession model, never edited.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from pydantic import ValidationError

from omnibase_core.enums.ticket.enum_diff_attestation import EnumDiffAttestation
from omnibase_core.models.contracts.ticket.model_dod_receipt import ModelDodReceipt

_RECEIPT_PREFIX = "drift/dod_receipts/"
_CONTRACT_PREFIX = "contracts/"
# git --name-status status letters that mean "touched a pre-existing file".
_MUTATION_CODES = frozenset({"M", "D", "R", "C"})

# Legacy free-text triggers (high-precision, deliberately narrow). Both imply a
# NET_NEW_ONLY obligation. The first catches the verbatim OMN-13917 #3551 phrasing
# ("No existing receipts or the OMN-13501 contract are modified"); the second the
# canonical "net-new-only" shorthand.
_NET_NEW_CLAIM_RES: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"no existing (receipts?|contracts?)[^.]{0,80}(are )?modif", re.IGNORECASE
    ),
    re.compile(r"net[- ]new[- ]only", re.IGNORECASE),
)


@dataclass(frozen=True)
class DiffConsistencyViolation:
    """One attestation contradicted by the PR diff.

    Attributes:
        attestation: The diff-falsifiable claim that was contradicted.
        detail: Human-readable explanation naming the offending diff entries.
        receipt_path: Path to the receipt on disk (empty when checked in-memory).
    """

    attestation: EnumDiffAttestation
    detail: str
    receipt_path: Path = field(default_factory=Path)


def _normalize_name_status(
    name_status: Iterable[tuple[str, str]],
) -> list[tuple[str, str]]:
    """Reduce ``(git_status, path)`` pairs to ``(single-letter-code, path)``.

    ``git diff --name-status`` emits rename/copy scores (``R100``); only the
    leading letter carries the class, so it is normalized to a single uppercase
    character. Blank statuses are dropped.
    """
    normalized: list[tuple[str, str]] = []
    for status, path in name_status:
        code = status.strip().upper()[:1] if status.strip() else ""
        if code:
            normalized.append((code, path))
    return normalized


def _enforced_attestations(receipt: ModelDodReceipt) -> set[EnumDiffAttestation]:
    """Resolve which attestations this receipt must satisfy.

    Union of the structured ``diff_attestations`` field (authoritative) and the
    legacy free-text NET_NEW_ONLY triggers over ``actual_output``. A receipt with
    neither makes no diff-falsifiable claim and is exempt from this gate.
    """
    enforced: set[EnumDiffAttestation] = set(receipt.diff_attestations)
    text = receipt.actual_output or ""
    if any(pattern.search(text) for pattern in _NET_NEW_CLAIM_RES):
        enforced.add(EnumDiffAttestation.NET_NEW_ONLY)
    return enforced


def _check_net_new_only(
    entries: list[tuple[str, str]],
) -> str | None:
    """Every receipt/contract diff entry must be an add (``A``)."""
    offenders = [
        f"{code} {path}"
        for code, path in entries
        if path.startswith((_RECEIPT_PREFIX, _CONTRACT_PREFIX))
        and code in _MUTATION_CODES
    ]
    if not offenders:
        return None
    return (
        "receipt attests NET_NEW_ONLY but the diff modifies/deletes/renames "
        f"{len(offenders)} pre-existing receipt/contract file(s): "
        + ", ".join(sorted(offenders))
    )


def _check_receipts_unmodified(
    entries: list[tuple[str, str]],
) -> str | None:
    """No mutation of any file under ``drift/dod_receipts/``."""
    offenders = [
        f"{code} {path}"
        for code, path in entries
        if path.startswith(_RECEIPT_PREFIX) and code in _MUTATION_CODES
    ]
    if not offenders:
        return None
    return (
        "receipt attests RECEIPTS_UNMODIFIED but the diff modifies/deletes/"
        f"renames {len(offenders)} merged receipt file(s): "
        + ", ".join(sorted(offenders))
    )


def _check_contract_unmodified(
    entries: list[tuple[str, str]],
    ticket_id: str,
) -> str | None:
    """The ticket's own ``contracts/<ticket_id>.yaml`` must be absent or added."""
    target = f"{_CONTRACT_PREFIX}{ticket_id}.yaml"
    offenders = [
        f"{code} {path}"
        for code, path in entries
        if path == target and code in _MUTATION_CODES
    ]
    if not offenders:
        return None
    return (
        "receipt attests CONTRACT_UNMODIFIED but the diff modifies/deletes/"
        "renames its own contract: " + ", ".join(sorted(offenders))
    )


def check_diff_consistency(
    receipt: ModelDodReceipt,
    name_status: Iterable[tuple[str, str]],
    ticket_id: str | None = None,
) -> list[DiffConsistencyViolation]:
    """Validate a receipt's diff-falsifiable attestations against the PR diff.

    Pure — no I/O. The caller supplies the parsed ``git diff --name-status``
    output as ``(status, path)`` pairs (repo-relative paths).

    Args:
        receipt: The receipt whose attestations are being checked. Only receipts
            ADDED in the PR should be passed for the legacy free-text trigger to
            be meaningful; the structured trigger is always honored.
        name_status: ``(git_status, path)`` pairs for the whole PR diff. Status
            letters: ``A`` add, ``M`` modify, ``D`` delete, ``R``/``C`` rename/copy.
        ticket_id: Ticket whose contract the ``CONTRACT_UNMODIFIED`` predicate
            targets. Defaults to ``receipt.ticket_id`` when omitted.

    Returns:
        One :class:`DiffConsistencyViolation` per contradicted attestation. Empty
        when the receipt makes no claim or every claim holds.
    """
    resolved_ticket = ticket_id if ticket_id is not None else receipt.ticket_id
    enforced = _enforced_attestations(receipt)
    if not enforced:
        return []

    entries = _normalize_name_status(name_status)
    violations: list[DiffConsistencyViolation] = []

    if EnumDiffAttestation.NET_NEW_ONLY in enforced:
        detail = _check_net_new_only(entries)
        if detail is not None:
            violations.append(
                DiffConsistencyViolation(
                    attestation=EnumDiffAttestation.NET_NEW_ONLY, detail=detail
                )
            )

    if EnumDiffAttestation.RECEIPTS_UNMODIFIED in enforced:
        detail = _check_receipts_unmodified(entries)
        if detail is not None:
            violations.append(
                DiffConsistencyViolation(
                    attestation=EnumDiffAttestation.RECEIPTS_UNMODIFIED, detail=detail
                )
            )

    if EnumDiffAttestation.CONTRACT_UNMODIFIED in enforced:
        detail = _check_contract_unmodified(entries, resolved_ticket)
        if detail is not None:
            violations.append(
                DiffConsistencyViolation(
                    attestation=EnumDiffAttestation.CONTRACT_UNMODIFIED, detail=detail
                )
            )

    return violations


# ---------------------------------------------------------------------------
# File-scanning helpers (used by the CLI, pre-commit, and CI wiring)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ReceiptDiffFinding:
    """All diff-consistency violations found for one receipt file on disk."""

    receipt_path: Path
    violations: list[DiffConsistencyViolation]


def parse_name_status(text: str) -> list[tuple[str, str]]:
    """Parse ``git diff --name-status`` output into ``(status, path)`` pairs.

    Rename/copy lines carry the destination path last (``R100\told\tnew``); the
    destination is the one that exists at head, so it is taken as the path.
    """
    pairs: list[tuple[str, str]] = []
    for line in text.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        pairs.append((parts[0], parts[-1]))
    return pairs


def _load_receipt(receipt_path: Path) -> ModelDodReceipt | None:
    """Parse + validate one receipt file, or ``None`` if not a valid receipt.

    Structurally invalid receipts are skipped here — the receipt-gate owns those
    failures; this gate only speaks to attestation honesty.
    """
    try:
        raw = yaml.safe_load(receipt_path.read_text(encoding="utf-8"))
    except (yaml.YAMLError, OSError):
        return None
    if not isinstance(raw, dict):
        return None
    try:
        return ModelDodReceipt.model_validate(raw)
    except (ValidationError, ValueError):
        return None


def scan_receipt_files_with_diff(
    receipt_paths: Iterable[Path],
    name_status: Iterable[tuple[str, str]],
) -> list[ReceiptDiffFinding]:
    """Run :func:`check_diff_consistency` over explicit receipt files.

    This is the mode used by pre-commit and PR CI: it checks only the receipts
    changed on the PR without making historical receipts a prerequisite for every
    unrelated PR. Each receipt's ``CONTRACT_UNMODIFIED`` predicate targets its own
    ``ticket_id``.
    """
    entries = list(name_status)
    findings: list[ReceiptDiffFinding] = []
    for receipt_path in sorted(set(receipt_paths)):
        if not receipt_path.exists() or receipt_path.suffix not in {".yaml", ".yml"}:
            continue
        receipt = _load_receipt(receipt_path)
        if receipt is None:
            continue
        violations = check_diff_consistency(receipt, entries)
        if violations:
            stamped = [
                DiffConsistencyViolation(
                    attestation=v.attestation,
                    detail=v.detail,
                    receipt_path=receipt_path,
                )
                for v in violations
            ]
            findings.append(
                ReceiptDiffFinding(receipt_path=receipt_path, violations=stamped)
            )
    return findings


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main(argv: Sequence[str] | None = None) -> int:
    """CLI: check changed receipts' attestations against a name-status diff.

    Usage::

        git diff --name-status "origin/dev"...HEAD > /tmp/diff_name_status.txt
        python -m omnibase_core.validation.validator_receipt_diff_consistency \\
            --diff-file /tmp/diff_name_status.txt \\
            drift/dod_receipts/OMN-XXXX/item/command.yaml ...

    Exit codes:
        0 — no contradicted attestations
        1 — one or more contradicted attestations, or a missing/unreadable diff file
    """
    parser = argparse.ArgumentParser(
        description=(
            "Receipt-attestation diff-consistency gate (OMN-13927): fail when a "
            "receipt attests a diff-falsifiable claim (NET_NEW_ONLY, "
            "RECEIPTS_UNMODIFIED, CONTRACT_UNMODIFIED) that its own PR diff "
            "contradicts."
        )
    )
    parser.add_argument(
        "--diff-file",
        required=True,
        help="Path to a file containing `git diff --name-status <base>...<head>` output.",
    )
    parser.add_argument(
        "receipt_paths",
        nargs="*",
        help="Receipt YAML files changed on this PR (the receipts to check).",
    )
    args = parser.parse_args(argv)

    diff_path = Path(args.diff_file)
    try:
        diff_text = diff_path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"ERROR: cannot read --diff-file {diff_path}: {exc}", file=sys.stderr)
        return 1
    name_status = parse_name_status(diff_text)

    explicit_paths = [Path(p) for p in args.receipt_paths]
    if not explicit_paths:
        print("RECEIPT DIFF-CONSISTENCY GATE PASSED: no changed receipt files to check")
        return 0

    findings = scan_receipt_files_with_diff(explicit_paths, name_status)
    if not findings:
        print(
            "RECEIPT DIFF-CONSISTENCY GATE PASSED: "
            f"0 contradicted attestations across {len(explicit_paths)} receipt(s)"
        )
        return 0

    total = sum(len(f.violations) for f in findings)
    print(
        f"RECEIPT DIFF-CONSISTENCY GATE FAILED: {total} contradicted attestation(s) "
        f"across {len(findings)} receipt(s):\n"
    )
    for finding in findings:
        for v in finding.violations:
            print(f"  [{v.attestation}] {finding.receipt_path}")
            print(f"    {v.detail}")
            print()
    return 1


if __name__ == "__main__":
    sys.exit(main())


__all__ = [
    "DiffConsistencyViolation",
    "EnumDiffAttestation",
    "ReceiptDiffFinding",
    "check_diff_consistency",
    "main",
    "parse_name_status",
    "scan_receipt_files_with_diff",
]
