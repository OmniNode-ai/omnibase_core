# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Append-only enforcement for OCC contracts + receipts (OMN-13888, scope 2).

Per-entry hashing (scope 1) removes the *demand* to rewrite merged receipts; this
gate removes the *ability*. Given the contract at the merge base and at the PR
head, every dod_evidence item present at the base must exist at the head with an
identical per-entry hash (editing an item is a violation; removing one is a
violation). Appending a brand-new item id is allowed. A net-new contract
(``base is None``) passes trivially. Separately, any ``M``/``D``/``R`` git diff
of an existing receipt file under ``drift/dod_receipts/<TICKET>/`` is a
violation — corrections must be net-new ``A`` (add) supersession files.

The pure core (:func:`evaluate_append_only`) takes the two parsed contracts and
a list of ``(git_status, path)`` diff tuples, so it is fully unit-testable. The
:func:`main` CLI performs the git I/O.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from collections.abc import Iterable, Sequence
from pathlib import Path

import yaml

from omnibase_core.models.validation.model_occ_append_only_result import (
    EnumAppendOnlyViolationKind,
    ModelAppendOnlyViolation,
    ModelOccAppendOnlyResult,
)
from omnibase_core.validation.validator_receipt_gate import (
    ContractEntryNotFoundError,
    compute_contract_entry_sha256,
)

_APPEND_ONLY_VIOLATION = "APPEND_ONLY_VIOLATION"
_RECEIPT_DIR_PREFIX = "drift/dod_receipts"


def _entry_ids(contract: object) -> list[str]:
    ids: list[str] = []
    if isinstance(contract, dict):
        items = contract.get("dod_evidence", [])
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict):
                    item_id = item.get("id")
                    if isinstance(item_id, str):
                        ids.append(item_id)
    return ids


def evaluate_append_only(
    base_contract: dict[str, object] | None,
    head_contract: dict[str, object] | None,
    receipt_diff: Iterable[tuple[str, str]] = (),
) -> ModelOccAppendOnlyResult:
    """Evaluate the append-only invariant. Pure — no I/O.

    Args:
        base_contract: Parsed contract at the merge base, or ``None`` when the
            contract is net-new on this PR (nothing to protect → pass).
        head_contract: Parsed contract at the PR head.
        receipt_diff: ``(git_status, path)`` pairs from ``git diff
            --name-status`` scoped to the receipt directory. Status letters:
            ``A`` add (allowed), ``M`` modify, ``D`` delete, ``R``/``C`` rename/copy.
    """
    violations: list[ModelAppendOnlyViolation] = []

    if base_contract is not None:
        head = head_contract if isinstance(head_contract, dict) else {}
        head_ids = set(_entry_ids(head))
        for base_id in _entry_ids(base_contract):
            if base_id not in head_ids:
                violations.append(
                    ModelAppendOnlyViolation(
                        kind=EnumAppendOnlyViolationKind.ENTRY_REMOVED,
                        target=base_id,
                        detail=(
                            f"dod_evidence item {base_id!r} present at base was "
                            "removed at head; removals are forbidden (append-only)."
                        ),
                    )
                )
                continue
            try:
                base_hash = compute_contract_entry_sha256(base_contract, base_id)
                head_hash = compute_contract_entry_sha256(head, base_id)
            except ContractEntryNotFoundError:
                # Defensive: id membership already checked above.
                continue
            if base_hash != head_hash:
                violations.append(
                    ModelAppendOnlyViolation(
                        kind=EnumAppendOnlyViolationKind.ENTRY_EDITED,
                        target=base_id,
                        detail=(
                            f"dod_evidence item {base_id!r} was edited "
                            f"(entry hash {base_hash} -> {head_hash}); existing "
                            "entries are immutable. Append a new item or file a "
                            "supersession record instead."
                        ),
                    )
                )

    for status, path in receipt_diff:
        code = status.strip().upper()[:1] if status.strip() else ""
        if code in ("M", "D", "R", "C"):
            violations.append(
                ModelAppendOnlyViolation(
                    kind=EnumAppendOnlyViolationKind.RECEIPT_FILE_MUTATED,
                    target=path,
                    detail=(
                        f"receipt file {path!r} was {code!r} (modified/deleted/"
                        "renamed); merged receipts are immutable. Corrections must "
                        "be net-new '.supersede.<NNNN>.yaml' add-only files."
                    ),
                )
            )

    if violations:
        return ModelOccAppendOnlyResult(
            ok=False,
            reason=_APPEND_ONLY_VIOLATION,
            violations=tuple(violations),
            detail=f"{len(violations)} append-only violation(s) detected.",
        )
    return ModelOccAppendOnlyResult(
        ok=True,
        detail="No append-only violations: existing entries and receipts unchanged.",
    )


def _load_yaml_from_git(
    repo: Path, ref: str, rel_path: str
) -> dict[str, object] | None:
    proc = subprocess.run(
        ["git", "-C", str(repo), "show", f"{ref}:{rel_path}"],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return None
    parsed = yaml.safe_load(proc.stdout)
    return parsed if isinstance(parsed, dict) else None


def _load_yaml_file(path: Path) -> dict[str, object] | None:
    if not path.is_file():
        return None
    parsed = yaml.safe_load(path.read_text(encoding="utf-8"))
    return parsed if isinstance(parsed, dict) else None


def _receipt_diff_from_git(
    repo: Path, base_ref: str, ticket_id: str
) -> list[tuple[str, str]]:
    scope = f"{_RECEIPT_DIR_PREFIX}/{ticket_id}"
    proc = subprocess.run(
        ["git", "-C", str(repo), "diff", "--name-status", base_ref, "--", scope],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return []
    diff: list[tuple[str, str]] = []
    for line in proc.stdout.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        status = parts[0]
        # Rename/copy lines carry the destination path last.
        path = parts[-1]
        diff.append((status, path))
    return diff


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="OCC append-only enforcement gate (OMN-13888)"
    )
    parser.add_argument("--repo", required=True, help="Path to the OCC repo root.")
    parser.add_argument("--ticket-id", required=True)
    parser.add_argument(
        "--base-ref",
        default="origin/dev",
        help="Merge-base ref to compare against (default origin/dev).",
    )
    args = parser.parse_args(argv)

    repo = Path(args.repo)
    contract_rel = f"contracts/{args.ticket_id}.yaml"
    base_contract = _load_yaml_from_git(repo, args.base_ref, contract_rel)
    head_contract = _load_yaml_file(repo / contract_rel)
    receipt_diff = _receipt_diff_from_git(repo, args.base_ref, args.ticket_id)

    result = evaluate_append_only(base_contract, head_contract, receipt_diff)
    sys.stdout.write(f"{result.to_json()}\n")
    return 0 if result.ok else 1


if __name__ == "__main__":
    sys.exit(main())


__all__ = [
    "ModelOccAppendOnlyResult",
    "evaluate_append_only",
    "main",
]
