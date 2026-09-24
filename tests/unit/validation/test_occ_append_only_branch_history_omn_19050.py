# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OMN-19050: a companion branch may not rewrite the evidence it already holds.

The OCC Append-Only Gate diffed a pull request against its merge base, so it
protected only files that had already merged. A record added on the companion
branch and then changed or removed by a later commit on that same branch was
invisible to it, because against the merge base the record is simply added.
Both of these happened on the omnimarket#2839 companion and reached OCC main
through the squash merge:

* 66946494a5 rewrote ``contract_entry_sha256`` on two runner-written FAIL
  records, while their ``check_value`` still shows the command that actually
  ran.
* 22261d23a8 deleted a runner-written PASS record. The runner then wrote a
  different record at the same path, so the merged diff reads as one clean
  addition.

The gate now also walks the branch's own commits. A commit that modifies,
deletes or renames a protected record is refused. A record is protected when
it is a supersession record (``*.supersede.*.yaml``, the correction primitive
itself) or when its prior content names the product-repo receipt runner. New
records, tombstones included, are still allowed. The autobind emitter's base
mints are not protected: re-minting them at a new head is the normal flow, and
the scan over 60 merged companions found 141 such re-mints.
"""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

import pytest
import yaml

from omnibase_core.enums.enum_append_only_violation_kind import (
    EnumAppendOnlyViolationKind,
)
from omnibase_core.validation.validator_occ_append_only import (
    BranchHistoryChange,
    evaluate_append_only,
    main,
)
from omnibase_core.validators.no_unguarded_git_subprocess import (
    scrub_git_location_env,
)

TICKET = "OMN-19378"
ITEM = "dod-occ-diff-derived-behavior-proof-pr-2839"
KEY_DIR = f"drift/dod_receipts/{TICKET}/{ITEM}"
FAIL_RECORD = f"{KEY_DIR}/test_passes.supersede.2839.yaml"
PASS_RECORD = f"{KEY_DIR}/test_passes.supersede.2839.0003.yaml"
BASE_MINT = f"{KEY_DIR}/test_passes.yaml"
RUNNER = "omnimarket-ci occ-receipt-runner"


def _entry(tag: str) -> str:
    return "sha256:" + hashlib.sha256(tag.encode()).hexdigest()


def _receipt(*, status: str, runner: str, entry: str) -> dict[str, object]:
    executed = status != "PENDING"
    return {
        "schema_version": "1.0.0",
        "ticket_id": TICKET,
        "evidence_item_id": ITEM,
        "check_type": "test_passes",
        "check_value": "uv run pytest tests/ci/test_no_stale_rebuild_classifier.py -q",
        "status": status,
        "run_timestamp": "2026-09-24T07:38:16Z",
        "commit_sha": "f490fba5" + "0" * 32,
        "runner": runner,
        "verifier": "github-actions product-repo test execution",
        "probe_command": "uv run pytest tests/ci/test_no_stale_rebuild_classifier.py -q",
        "probe_stdout": "14 passed in 6.42s" if executed else "",
        "exit_code": (0 if status == "PASS" else 4) if executed else None,
        "pr_number": 2839,
        "contract_entry_sha256": _entry(entry),
    }


def _runner_record(status: str, entry: str) -> str:
    return yaml.safe_dump(
        {
            "schema_version": "1.0.0",
            "ticket_id": TICKET,
            "evidence_item_id": ITEM,
            "check_type": "test_passes",
            "supersedes": BASE_MINT,
            "reason": "executed for real in the product checkout",
            "superseder": RUNNER,
            "created_at": "2026-09-24T07:38:16Z",
            "tombstone": False,
            "replacement": _receipt(status=status, runner=RUNNER, entry=entry),
        },
        sort_keys=True,
    )


def _emitter_mint(entry: str) -> str:
    return yaml.safe_dump(
        _receipt(status="PENDING", runner="node_pr_lifecycle_fix_effect", entry=entry),
        sort_keys=True,
    )


def _runner_base(entry: str) -> str:
    """A base receipt the runner wrote directly, for a key with no mint."""
    return yaml.safe_dump(
        _receipt(status="FAIL", runner=RUNNER, entry=entry), sort_keys=True
    )


# --------------------------------------------------------------------------- #
# The pure rule
# --------------------------------------------------------------------------- #


def _history_kinds(
    changes: list[BranchHistoryChange],
) -> list[EnumAppendOnlyViolationKind]:
    result = evaluate_append_only(None, None, branch_history=changes)
    return [violation.kind for violation in result.violations]


@pytest.mark.unit
@pytest.mark.parametrize("status", ["M", "D", "R100"])
def test_a_supersession_record_cannot_be_rewritten_on_the_branch(status: str) -> None:
    kinds = _history_kinds(
        [
            (
                "66946494a5",
                status,
                FAIL_RECORD,
                _runner_record("FAIL", "sha256:old"),
                None,
            )
        ]
    )

    assert kinds == [EnumAppendOnlyViolationKind.BRANCH_RECORD_MUTATED]


@pytest.mark.unit
def test_a_supersession_record_is_protected_whoever_wrote_it() -> None:
    """A hand-authored correction record is a correction all the same."""
    kinds = _history_kinds(
        [("b02418cc4a", "M", FAIL_RECORD, "reason: hand-run\n", None)]
    )

    assert kinds == [EnumAppendOnlyViolationKind.BRANCH_RECORD_MUTATED]


@pytest.mark.unit
def test_a_base_receipt_the_runner_wrote_cannot_be_rewritten() -> None:
    kinds = _history_kinds(
        [("c0ffee", "M", BASE_MINT, _runner_base("sha256:old"), None)]
    )

    assert kinds == [EnumAppendOnlyViolationKind.BRANCH_RECORD_MUTATED]


@pytest.mark.unit
def test_the_emitter_may_still_re_mint_its_own_base_receipt() -> None:
    """Positive control: autobind re-mints its PENDING base at each new head."""
    kinds = _history_kinds(
        [("7f45d34541", "M", BASE_MINT, _emitter_mint("sha256:a"), None)]
    )

    assert kinds == []


@pytest.mark.unit
@pytest.mark.parametrize("status", ["A", "C100"])
def test_adding_a_record_is_allowed(status: str) -> None:
    """Positive control: additions, tombstones included, are how corrections land."""
    kinds = _history_kinds([("3f26e3b466", status, PASS_RECORD, None, None)])

    assert kinds == []


@pytest.mark.unit
def test_a_violation_names_the_commit_and_the_record() -> None:
    result = evaluate_append_only(
        None,
        None,
        branch_history=[
            ("22261d23a8", "D", PASS_RECORD, _runner_record("PASS", "x"), None)
        ],
    )

    assert result.ok is False
    (violation,) = result.violations
    assert violation.target == PASS_RECORD
    assert "22261d23a8" in violation.detail


# --------------------------------------------------------------------------- #
# End to end through the CLI the OCC workflow runs, over a real git history
# --------------------------------------------------------------------------- #


def _git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
        env=scrub_git_location_env(),
    )
    return completed.stdout.strip()


def _commit(repo: Path, message: str, files: dict[str, str | None]) -> str:
    for rel, content in files.items():
        path = repo / rel
        if content is None:
            _git(repo, "rm", "-q", rel)
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        _git(repo, "add", rel)
    _git(repo, "commit", "-q", "-m", message)
    return _git(repo, "rev-parse", "HEAD")


@pytest.fixture
def companion(tmp_path: Path) -> tuple[Path, str]:
    """An OCC-shaped repo with a merged base and a companion branch off it."""
    repo = tmp_path / "occ"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "dev")
    _git(repo, "config", "user.email", "lane@example.invalid")
    _git(repo, "config", "user.name", "lane")
    _git(repo, "config", "commit.gpgsign", "false")
    base = _commit(
        repo,
        "base",
        {
            f"contracts/{TICKET}.yaml": yaml.safe_dump(
                {"ticket_id": TICKET, "dod_evidence": []}
            )
        },
    )
    _git(repo, "checkout", "-q", "-b", "auto/companion")
    _commit(repo, "autobind mint", {BASE_MINT: _emitter_mint("sha256:old")})
    _commit(repo, "runner FAIL", {FAIL_RECORD: _runner_record("FAIL", "sha256:old")})
    return repo, base


def _gate(repo: Path, base: str) -> int:
    return main(["--repo", str(repo), "--ticket-id", TICKET, "--base-ref", base])


@pytest.mark.unit
def test_cli_refuses_a_hand_edit_of_a_runner_record(
    companion: tuple[Path, str],
) -> None:
    """The 66946494a5 shape: rewrite a runner FAIL's entry hash on the branch."""
    repo, base = companion
    _commit(repo, "hand edit", {FAIL_RECORD: _runner_record("FAIL", "sha256:new")})

    assert _gate(repo, base) == 1


@pytest.mark.unit
def test_cli_refuses_a_delete_hidden_by_a_re_add_at_the_same_path(
    companion: tuple[Path, str],
) -> None:
    """The 22261d23a8 shape: against the merge base this reads as one addition."""
    repo, base = companion
    _commit(repo, "runner PASS", {PASS_RECORD: _runner_record("PASS", "sha256:old")})
    _commit(repo, "hand delete", {PASS_RECORD: None})
    _commit(repo, "runner PASS again", {PASS_RECORD: _runner_record("PASS", "x")})

    assert _gate(repo, base) == 1


@pytest.mark.unit
def test_cli_passes_an_append_only_companion(companion: tuple[Path, str]) -> None:
    """Positive control: new records, a tombstone and an emitter re-mint pass."""
    repo, base = companion
    _commit(repo, "runner PASS", {PASS_RECORD: _runner_record("PASS", "sha256:old")})
    _commit(
        repo,
        "tombstone",
        {
            f"{KEY_DIR}/test_passes.supersede.2839.0004.yaml": yaml.safe_dump(
                {"superseder": "lane", "tombstone": True}
            )
        },
    )
    _commit(repo, "autobind re-mint", {BASE_MINT: _emitter_mint("sha256:new")})

    assert _gate(repo, base) == 0


@pytest.mark.unit
def test_cli_reads_the_branch_through_a_merge_from_dev(
    companion: tuple[Path, str],
) -> None:
    """A dev merge on the branch must not hide an earlier rewrite."""
    repo, _base = companion
    _commit(repo, "hand edit", {FAIL_RECORD: _runner_record("FAIL", "sha256:new")})
    _git(repo, "checkout", "-q", "dev")
    _commit(repo, "unrelated dev work", {"docs/note.md": "dev moved\n"})
    _git(repo, "checkout", "-q", "auto/companion")
    _git(repo, "merge", "-q", "--no-edit", "dev")
    merge_base = _git(repo, "merge-base", "dev", "HEAD")

    assert _gate(repo, merge_base) == 1


# --------------------------------------------------------------------------- #
# The companion effect's self-bind re-stamp of the whole-file hash
# --------------------------------------------------------------------------- #
#
# The effect's self-bind pass appends an item to the contract after the first
# pass has written the records, so the legacy whole-file ``contract_sha256`` in
# those records goes stale and the pass re-stamps it. Measured on OCC#11077:
# commit 232d124e5a changed exactly that one line in four supersede records it
# had written in 956023a1a. The per-entry hash beside it is untouched.


def _stamped(status: str, *, contract: str, entry: str | None = "sha256:e") -> str:
    record = yaml.safe_load(_runner_record(status, "sha256:unused"))
    replacement = record["replacement"]
    replacement["contract_sha256"] = contract
    if entry is None:
        del replacement["contract_entry_sha256"]
    else:
        replacement["contract_entry_sha256"] = entry
    return yaml.safe_dump(record, sort_keys=True)


@pytest.mark.unit
def test_the_self_bind_whole_file_hash_restamp_is_allowed() -> None:
    kinds = _history_kinds(
        [
            (
                "232d124e5a",
                "M",
                FAIL_RECORD,
                _stamped("FAIL", contract="sha256:before-self-bind"),
                _stamped("FAIL", contract="sha256:after-self-bind"),
            )
        ]
    )

    assert kinds == []


@pytest.mark.unit
def test_a_restamp_that_also_moves_the_entry_hash_is_refused() -> None:
    """The 66946494a5 rewrite does not become legal by riding on a re-stamp."""
    kinds = _history_kinds(
        [
            (
                "66946494a5",
                "M",
                FAIL_RECORD,
                _stamped("FAIL", contract="sha256:a", entry="sha256:as-generated"),
                _stamped("FAIL", contract="sha256:b", entry="sha256:corrected"),
            )
        ]
    )

    assert kinds == [EnumAppendOnlyViolationKind.BRANCH_RECORD_MUTATED]


@pytest.mark.unit
def test_a_restamp_where_the_whole_file_hash_is_the_only_binding_is_refused() -> None:
    kinds = _history_kinds(
        [
            (
                "c0ffee",
                "M",
                FAIL_RECORD,
                _stamped("FAIL", contract="sha256:a", entry=None),
                _stamped("FAIL", contract="sha256:b", entry=None),
            )
        ]
    )

    assert kinds == [EnumAppendOnlyViolationKind.BRANCH_RECORD_MUTATED]


@pytest.mark.unit
def test_a_restamp_that_also_flips_the_status_is_refused() -> None:
    kinds = _history_kinds(
        [
            (
                "c0ffee",
                "M",
                FAIL_RECORD,
                _stamped("FAIL", contract="sha256:a"),
                _stamped("PASS", contract="sha256:b"),
            )
        ]
    )

    assert kinds == [EnumAppendOnlyViolationKind.BRANCH_RECORD_MUTATED]


@pytest.mark.unit
def test_a_runner_record_this_core_cannot_model_is_still_protected() -> None:
    """Identity is read from the raw record, not through a model that may reject it.

    A runner receipt carrying a field this core does not declare (tree_sha, on
    a core without it) failed model validation and so lost its protection.
    """
    record = yaml.safe_load(_runner_base("sha256:old"))
    record["tree_sha"] = "7dceb0ed" + "0" * 32
    record["a_field_no_core_declares"] = True
    kinds = _history_kinds(
        [("c0ffee", "M", BASE_MINT, yaml.safe_dump(record, sort_keys=True), None)]
    )

    assert kinds == [EnumAppendOnlyViolationKind.BRANCH_RECORD_MUTATED]


@pytest.mark.unit
def test_cli_passes_the_self_bind_restamp(companion: tuple[Path, str]) -> None:
    repo, base = companion
    _commit(
        repo,
        "effect pass 1",
        {PASS_RECORD: _stamped("PASS", contract="sha256:before-self-bind")},
    )
    _commit(
        repo,
        "effect self-bind",
        {PASS_RECORD: _stamped("PASS", contract="sha256:after-self-bind")},
    )

    assert _gate(repo, base) == 0
