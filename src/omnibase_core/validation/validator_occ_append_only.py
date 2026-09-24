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

Branch history (OMN-19050). The diff above is taken against the merge base, so
it protects only records that have already merged. A record added on a
companion branch and then rewritten or removed by a later commit on that same
branch reads, against the merge base, as one clean addition. On the
omnimarket#2839 companion, OCC commit 66946494a5 rewrote the
``contract_entry_sha256`` of two runner-written FAIL records, and 22261d23a8
deleted a runner-written PASS record that the runner then replaced at the same
path. Both reached OCC main through the squash merge. So every commit on the
branch is also read on its own, and a commit that modifies, deletes or renames
a PROTECTED record is a violation. A record is protected when it is a
supersession record, which is the correction primitive itself, or when its
prior content names the product-repo receipt runner. The autobind emitter's
base mints are deliberately not protected, because re-minting them at a new
head is the normal flow. One modification of a protected record is allowed: a
re-stamp of the legacy whole-file ``contract_sha256`` beside an unchanged
``contract_entry_sha256``, which is what the companion effect's self-bind pass
does after it appends to the contract (OCC#11077, 232d124e5a).

Limit: the history read is the history that survives on the branch. A
force-push that replaces the branch removes the rewritten commits from
``base..HEAD``, and the companion emitter regenerates its branches that way.

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

from omnibase_core.enums.enum_append_only_violation_kind import (
    EnumAppendOnlyViolationKind,
)
from omnibase_core.models.validation.model_append_only_violation import (
    ModelAppendOnlyViolation,
)
from omnibase_core.models.validation.model_occ_append_only_contract import (
    ModelOccAppendOnlyContract,
)
from omnibase_core.models.validation.model_occ_append_only_result import (
    ModelOccAppendOnlyResult,
)
from omnibase_core.utils.util_safe_yaml_loader import load_yaml_mapping_no_duplicates
from omnibase_core.validation.validator_receipt_gate import (
    ContractEntryNotFoundError,
    compute_contract_entry_sha256,
)

_APPEND_ONLY_VIOLATION = "APPEND_ONLY_VIOLATION"
_RECEIPT_DIR_PREFIX = "drift/dod_receipts"

# The identity the product-repo receipt runner records as ``runner`` on every
# receipt it executes and as ``superseder`` on every record it files
# (omnimarket scripts/ci/occ_receipt_runner.py). A record carrying it is
# executed evidence, never a placeholder, so a branch may not rewrite it.
RECEIPT_RUNNER_IDENTITIES: frozenset[str] = frozenset(
    {"omnimarket-ci occ-receipt-runner"}
)

# One change a branch commit made to a receipt path: the commit, the git
# status letter(s), the path before the change, the content that path held
# before the change (None when the change is an addition), and the content the
# commit left at that path (None unless the change is a modification).
BranchHistoryChange = tuple[str, str, str, str | None, str | None]

# The legacy WHOLE-FILE contract hash. It goes stale on every append to the
# contract (validator_receipt_gate), so a producer that appends to the
# contract after writing a record re-stamps it. The per-entry hash beside it
# is the authoritative binding.
_WHOLE_FILE_HASH = "contract_sha256"
_ENTRY_HASH = "contract_entry_sha256"


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


def _record_mapping(text: str | None) -> dict[object, object] | None:
    """A record's YAML mapping, or None when there is no text or it is not one."""
    if not text:
        return None
    try:
        return load_yaml_mapping_no_duplicates(text, source="receipt record")
    except (ValueError, yaml.YAMLError):
        return None


def _names_the_runner(prior_text: str | None) -> bool:
    """Whether a record's prior content says the receipt runner produced it.

    The identity fields are read from the raw mapping, not through the record
    models, so a runner record that this core's models would reject (one
    carrying a field this core does not declare, for instance) keeps its
    protection. Content that is not a mapping is judged on its path alone.
    """
    record = _record_mapping(prior_text)
    if record is None:
        return False
    identities = [record.get("superseder"), record.get("runner")]
    replacement = record.get("replacement")
    if isinstance(replacement, dict):
        identities.append(replacement.get("runner"))
    return any(identity in RECEIPT_RUNNER_IDENTITIES for identity in identities)


def _level_without_whole_file_hash(
    level: dict[object, object],
) -> dict[object, object]:
    return {
        key: value
        for key, value in level.items()
        if key not in (_WHOLE_FILE_HASH, "replacement")
    }


def _only_whole_file_hash_restamped(
    prior_text: str | None, new_text: str | None
) -> bool:
    """Whether a modification changed nothing but the legacy whole-file hash.

    Checked at the record's top level and inside ``replacement``. At every
    level where ``contract_sha256`` moved, an unchanged ``contract_entry_sha256``
    must still bind it. On a level with no entry hash the whole-file hash IS
    the binding, and re-stamping it is the 66946494a5 rewrite in its legacy
    form, so it stays refused.
    """
    prior = _record_mapping(prior_text)
    new = _record_mapping(new_text)
    if prior is None or new is None or prior == new:
        return False
    prior_replacement = prior.get("replacement")
    new_replacement = new.get("replacement")
    levels: list[tuple[dict[object, object], dict[object, object]]] = [(prior, new)]
    if isinstance(prior_replacement, dict) and isinstance(new_replacement, dict):
        levels.append((prior_replacement, new_replacement))
    elif prior_replacement != new_replacement:
        return False
    for prior_level, new_level in levels:
        if _level_without_whole_file_hash(
            prior_level
        ) != _level_without_whole_file_hash(new_level):
            return False
        if prior_level.get(_WHOLE_FILE_HASH) != new_level.get(_WHOLE_FILE_HASH) and (
            prior_level.get(_ENTRY_HASH) is None
        ):
            return False
    return True


def _is_protected_record(path: str, prior_text: str | None) -> bool:
    if ".supersede." in Path(path).name:
        return True
    return _names_the_runner(prior_text)


def _branch_history_violations(
    branch_history: Iterable[BranchHistoryChange],
) -> list[ModelAppendOnlyViolation]:
    violations: list[ModelAppendOnlyViolation] = []
    for commit, status, path, prior_text, new_text in branch_history:
        code = status.strip().upper()[:1] if status.strip() else ""
        # A copy leaves its source in place, so it is an addition.
        if code not in ("M", "D", "R"):
            continue
        if not _is_protected_record(path, prior_text):
            continue
        if code == "M" and _only_whole_file_hash_restamped(prior_text, new_text):
            continue
        verb = {"M": "modified", "D": "deleted", "R": "renamed"}[code]
        violations.append(
            ModelAppendOnlyViolation(
                kind=EnumAppendOnlyViolationKind.BRANCH_RECORD_MUTATED,
                target=path,
                detail=(
                    f"commit {commit} {verb} evidence record {path!r} that this "
                    "branch already held. A supersession record, or a record the "
                    "receipt runner wrote, is immutable once it exists, merged or "
                    "not. Correct it with a net-new supersession record or a "
                    "tombstone."
                ),
            )
        )
    return violations


def evaluate_append_only(
    base_contract: dict[str, object] | None,
    head_contract: dict[str, object] | None,
    receipt_diff: Iterable[tuple[str, str]] = (),
    branch_history: Iterable[BranchHistoryChange] = (),
) -> ModelOccAppendOnlyResult:
    """Evaluate the append-only invariant. Pure — no I/O.

    Args:
        base_contract: Parsed contract at the merge base, or ``None`` when the
            contract is net-new on this PR (nothing to protect → pass).
        head_contract: Parsed contract at the PR head.
        receipt_diff: ``(git_status, path)`` pairs from ``git diff
            --name-status`` scoped to the receipt directory. Status letters:
            ``A`` add (allowed), ``M`` modify, ``D`` delete, ``R``/``C`` rename/copy.
        branch_history: one :data:`BranchHistoryChange` per receipt path each
            branch commit touched, read commit by commit (OMN-19050).
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

    violations.extend(_branch_history_violations(branch_history))

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
    parsed = ModelOccAppendOnlyContract.from_yaml(proc.stdout)
    return parsed.model_dump(mode="python")


def _load_yaml_file(path: Path) -> dict[str, object] | None:
    if not path.is_file():
        return None
    parsed = ModelOccAppendOnlyContract.from_yaml(path.read_text(encoding="utf-8"))
    return parsed.model_dump(mode="python")


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


def _git_text(repo: Path, *args: str) -> str | None:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return None
    return proc.stdout


def _branch_history_from_git(
    repo: Path, base_ref: str, ticket_id: str
) -> tuple[list[BranchHistoryChange], str | None]:
    """Every receipt change each branch commit made, read commit by commit.

    Each commit is diffed against its FIRST parent, so a merge from the base
    branch contributes only what the merge itself changed, and the branch's
    own commits reached through that merge are still read on their own.

    Returns the changes and None, or an empty list and the reason the history
    could not be read. An unreadable history must fail the gate, because an
    empty one would read as a clean branch.
    """
    scope = f"{_RECEIPT_DIR_PREFIX}/{ticket_id}"
    commits = _git_text(repo, "rev-list", "--reverse", f"{base_ref}..HEAD")
    if commits is None:
        return [], (
            f"cannot list the commits in {base_ref}..HEAD; the branch history "
            "must be readable (checkout with fetch-depth: 0)"
        )
    changes: list[BranchHistoryChange] = []
    for commit in commits.split():
        parents = _git_text(repo, "rev-list", "--parents", "-n", "1", commit)
        if parents is None or len(parents.split()) < 2:
            continue
        parent = parents.split()[1]
        diff = _git_text(
            repo, "diff", "--name-status", "-M", parent, commit, "--", scope
        )
        if diff is None:
            return [], f"cannot diff commit {commit} against {parent}"
        for line in diff.splitlines():
            if not line.strip():
                continue
            parts = line.split("\t")
            status = parts[0]
            # For a rename or copy the SOURCE is the record that existed.
            path = parts[1]
            prior = None
            if status[:1] in ("M", "D", "R"):
                prior = _git_text(repo, "show", f"{parent}:{path}")
            new = None
            if status[:1] == "M":
                new = _git_text(repo, "show", f"{commit}:{path}")
            changes.append((commit, status, path, prior, new))
    return changes, None


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
    branch_history, history_error = _branch_history_from_git(
        repo, args.base_ref, args.ticket_id
    )
    if history_error is not None:
        sys.stderr.write(
            f"append-only gate cannot read the branch history: {history_error}\n"
        )
        return 1

    result = evaluate_append_only(
        base_contract, head_contract, receipt_diff, branch_history
    )
    sys.stdout.write(f"{result.to_json()}\n")
    return 0 if result.ok else 1


if __name__ == "__main__":
    sys.exit(main())


__all__ = [
    "RECEIPT_RUNNER_IDENTITIES",
    "BranchHistoryChange",
    "ModelOccAppendOnlyResult",
    "evaluate_append_only",
    "main",
]
