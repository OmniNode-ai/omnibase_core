# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OMN-19050 — the anti-retry guard compares what was observed, not a commit id.

``_guarded_winner`` refuses a PASS that supersedes a FAIL when the two are the
same observation. It used to decide "same observation" by ``commit_sha``
alone, and that was wrong in both directions. Measured on omnimarket#2839:

* **It let an empty commit through.** ``9c09739`` has tree ``7dceb0ed``,
  byte-identical to the ``f490fba`` tree the FAIL was recorded at. A new
  commit id with no code change cleared the FAIL, and would have cleared any
  FAIL, a flaky one included. That is the retry-until-green channel the guard
  exists to close.
* **It refused a real correction.** The contract's declared check named two
  test files the PR deletes by design. The check was corrected and
  re-executed at the SAME head. The new PASS was a different observation,
  because a different check ran, but it had the same commit id, so the guard
  refused it.

The repaired rule, which these tests pin:

* Code identity is the ``tree_sha`` when both records carry one. Otherwise
  it falls back to ``commit_sha``, so records written before ``tree_sha``
  existed resolve exactly as they did. The same ``commit_sha`` is always the
  same code: a claimed tree can make two commits the same, never one commit
  two.
* The check definition has changed only when BOTH the ``contract_entry_sha256``
  and the declared command differ. The runner prefixes each command with a
  per-commit ``repos/<owner>/<repo>/commits/<sha>`` line, and that line is
  ignored. An edit to the item's description alone changes the entry hash but
  not the check.
* Same code and same definition: refused. Same code and changed definition:
  allowed, and the resolution records why. Different code: allowed.
* A PASS is refused against ANY earlier FAIL for the same observation, not
  only the latest. Otherwise FAIL at T1, then FAIL at T2, then PASS at T1
  again would launder T1's failure.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from omnibase_core.enums.ticket.enum_receipt_status import EnumReceiptStatus
from omnibase_core.models.contracts.ticket.model_dod_receipt import ModelDodReceipt
from omnibase_core.validation.validator_occ_merge_eligibility import (
    EnumOccEligibilityReason,
    ModelOccEligibilityInput,
    validate_occ_merge_eligibility,
)
from omnibase_core.validation.validator_receipt_gate import (
    compute_contract_entry_sha256,
)
from omnibase_core.validation.validator_receipt_supersession import (
    SupersessionResolution,
    resolve_supersession,
)

TICKET = "OMN-19378"
ITEM = "dod-occ-diff-derived-behavior-proof-pr-2839"
CHECK = "test_passes"
PR = 2839
REPO = "OmniNode-ai/omnimarket"

# The real identities from omnimarket#2839. 9c09739 is an empty commit on top
# of f490fba, so the two share a tree.
FAIL_HEAD = "f490fba530e695341c89aa84b8c24111f7414368"  # pragma: allowlist secret
EMPTY_COMMIT_HEAD = (
    "9c09739b3241d87feeda1d6ab6b625e2d2f65d56"  # pragma: allowlist secret
)
SHARED_TREE = "7dceb0ed" + "0" * 32
FIXED_HEAD = "668a565b" + "1" * 32
FIXED_TREE = "5a1f0c3e" + "2" * 32

# The as-generated check named two test files the PR deletes; the corrected
# one drops them. These are the two contract_entry_sha256 values 66946494a5
# moved between.
FOUR_PATH_COMMAND = (
    "uv run pytest tests/ci/test_no_stale_rebuild_classifier.py "
    "tests/unit/scripts/test_ci_bus_lane_transport.py "
    "tests/unit/scripts/test_trigger_producer_effect_assertion.py "
    "tests/unit/scripts/test_trigger_rebuild_on_merge.py -q"
)
TWO_PATH_COMMAND = (
    "uv run pytest tests/ci/test_no_stale_rebuild_classifier.py "
    "tests/unit/scripts/test_ci_bus_lane_transport.py -q"
)
AS_GENERATED_ENTRY = (
    "sha256:8ac0efc771106c714a4c504f0751d1ae8c47b78ad45f7bec047916cdbcc8c33c"
)
CORRECTED_ENTRY = (
    "sha256:50e6d94980f3ab499c7f5b5db1f527ab600157e8e7286a72030fdc0865901714"
)


def _bound(command: str, head: str) -> str:
    """The runner's check_value: a product-repo reference, then the command."""
    return f"repos/{REPO}/commits/{head}\n{command}"


def _receipt(
    *,
    status: EnumReceiptStatus,
    head: str,
    tree: str | None,
    command: str,
    entry: str,
) -> dict[str, object]:
    body: dict[str, object] = {
        "schema_version": "1.0.0",
        "ticket_id": TICKET,
        "evidence_item_id": ITEM,
        "check_type": CHECK,
        "check_value": _bound(command, head),
        "status": status.value,
        "run_timestamp": datetime(2026, 9, 24, 7, 38, tzinfo=UTC),
        "commit_sha": head,
        "runner": "omnimarket-ci occ-receipt-runner",
        "verifier": "github-actions product-repo test execution",
        "probe_command": _bound(command, head),
        "probe_stdout": (
            "14 passed in 6.42s"
            if status is EnumReceiptStatus.PASS
            else "ERROR: file or directory not found"
        ),
        "exit_code": 0 if status is EnumReceiptStatus.PASS else 4,
        "pr_number": PR,
        "contract_entry_sha256": entry,
    }
    if tree is not None:
        body["tree_sha"] = tree
    return body


def _record(replacement: dict[str, object], minute: int) -> dict[str, object]:
    return {
        "schema_version": "1.0.0",
        "ticket_id": TICKET,
        "evidence_item_id": ITEM,
        "check_type": CHECK,
        "supersedes": f"drift/dod_receipts/{TICKET}/{ITEM}/{CHECK}.yaml",
        "reason": "the declared check was executed for real in the product checkout",
        "superseder": "omnimarket-ci occ-receipt-runner",
        "created_at": datetime(2026, 9, 24, 8, minute, tzinfo=UTC),
        "tombstone": False,
        "replacement": replacement,
    }


def _chain(root: Path, *receipts: dict[str, object]) -> Path:
    """Write receipts as the runner's attempt records, oldest first."""
    key_dir = root / "receipts" / TICKET / ITEM
    key_dir.mkdir(parents=True)
    for index, receipt in enumerate(receipts, start=1):
        suffix = str(PR) if index == 1 else f"{PR}.{index:04d}"
        (key_dir / f"{CHECK}.supersede.{suffix}.yaml").write_text(
            yaml.safe_dump(_record(receipt, index), sort_keys=True),
            encoding="utf-8",
        )
    return root / "receipts"


def _resolve(receipts: Path, *, with_pr: bool = True) -> SupersessionResolution:
    resolution = resolve_supersession(
        receipts,
        TICKET,
        ITEM,
        CHECK,
        current_pr_number=PR if with_pr else None,
    )
    assert resolution is not None
    assert resolution.error is None
    assert resolution.receipt is not None
    return resolution


def _fail(
    *,
    head: str = FAIL_HEAD,
    tree: str | None = SHARED_TREE,
    command: str = TWO_PATH_COMMAND,
    entry: str = CORRECTED_ENTRY,
) -> dict[str, object]:
    return _receipt(
        status=EnumReceiptStatus.FAIL,
        head=head,
        tree=tree,
        command=command,
        entry=entry,
    )


def _pass(
    *,
    head: str,
    tree: str | None,
    command: str = TWO_PATH_COMMAND,
    entry: str = CORRECTED_ENTRY,
) -> dict[str, object]:
    return _receipt(
        status=EnumReceiptStatus.PASS,
        head=head,
        tree=tree,
        command=command,
        entry=entry,
    )


# --------------------------------------------------------------------------- #
# Negative controls: the same observation restated must not clear a FAIL
# --------------------------------------------------------------------------- #


@pytest.mark.unit
@pytest.mark.parametrize("with_pr", [True, False], ids=["tier1", "legacy"])
def test_an_empty_commit_does_not_clear_a_fail(tmp_path: Path, with_pr: bool) -> None:
    """A new commit id over the same tree is the same code. The FAIL stands."""
    receipts = _chain(
        tmp_path,
        _fail(),
        _pass(head=EMPTY_COMMIT_HEAD, tree=SHARED_TREE),
    )

    resolution = _resolve(receipts, with_pr=with_pr)

    assert resolution.receipt is not None
    assert resolution.receipt.status is EnumReceiptStatus.FAIL
    assert resolution.receipt.commit_sha == FAIL_HEAD
    assert resolution.guard_note is not None
    assert "refused" in resolution.guard_note
    assert SHARED_TREE in resolution.guard_note


@pytest.mark.unit
def test_a_description_only_edit_is_not_a_check_definition_change(
    tmp_path: Path,
) -> None:
    """The entry hash covers the description, so it moves on a prose edit.

    The command that ran did not change, so this is still the same
    observation. Accepting it would let anyone clear a flaky FAIL by editing
    one word of the item's description.
    """
    receipts = _chain(
        tmp_path,
        _fail(entry=AS_GENERATED_ENTRY),
        _pass(head=EMPTY_COMMIT_HEAD, tree=SHARED_TREE, entry=CORRECTED_ENTRY),
    )

    resolution = _resolve(receipts)

    assert resolution.receipt is not None
    assert resolution.receipt.status is EnumReceiptStatus.FAIL


@pytest.mark.unit
def test_a_command_edit_without_a_new_entry_hash_is_refused(tmp_path: Path) -> None:
    """A differing command under an unchanged entry hash is not a definition change.

    This is the shape OCC commit 66946494a5 left on OCC main: the FAIL records
    had their ``contract_entry_sha256`` rewritten to the corrected entry while
    their ``check_value`` still shows the old command. The hash says the
    definition did not change, so the guard does not accept the PASS.
    """
    receipts = _chain(
        tmp_path,
        _fail(command=FOUR_PATH_COMMAND, entry=CORRECTED_ENTRY),
        _pass(head=EMPTY_COMMIT_HEAD, tree=SHARED_TREE, entry=CORRECTED_ENTRY),
    )

    resolution = _resolve(receipts)

    assert resolution.receipt is not None
    assert resolution.receipt.status is EnumReceiptStatus.FAIL


@pytest.mark.unit
def test_an_earlier_fail_is_not_laundered_by_an_intervening_one(
    tmp_path: Path,
) -> None:
    """FAIL at T1, FAIL at T2, PASS at T1 again: the T1 failure still stands."""
    receipts = _chain(
        tmp_path,
        _fail(),
        _fail(head=FIXED_HEAD, tree=FIXED_TREE),
        _pass(head=EMPTY_COMMIT_HEAD, tree=SHARED_TREE),
    )

    resolution = _resolve(receipts)

    assert resolution.receipt is not None
    assert resolution.receipt.status is EnumReceiptStatus.FAIL
    assert resolution.receipt.commit_sha == FAIL_HEAD


@pytest.mark.unit
def test_legacy_same_commit_same_definition_is_still_refused(tmp_path: Path) -> None:
    """Records without tree_sha fall back to commit_sha, as before."""
    receipts = _chain(
        tmp_path,
        _fail(tree=None),
        _pass(head=FAIL_HEAD, tree=None),
    )

    resolution = _resolve(receipts)

    assert resolution.receipt is not None
    assert resolution.receipt.status is EnumReceiptStatus.FAIL


@pytest.mark.unit
@pytest.mark.parametrize(
    "pass_tree", [FIXED_TREE, None], ids=["claims-another-tree", "omits-tree"]
)
def test_the_same_commit_is_the_same_code_whatever_tree_is_claimed(
    tmp_path: Path, pass_tree: str | None
) -> None:
    """One commit has one tree. A record claiming otherwise does not get a new observation.

    tree_sha is written by the record's author and nothing checks it against
    commit_sha, so a tree may only ever ADD sameness. Before this, a PASS at
    the FAIL's own commit that claimed a different tree cleared the FAIL.
    """
    receipts = _chain(
        tmp_path,
        _fail(),
        _pass(head=FAIL_HEAD, tree=pass_tree),
    )

    resolution = _resolve(receipts)

    assert resolution.receipt is not None
    assert resolution.receipt.status is EnumReceiptStatus.FAIL
    assert resolution.guard_note is not None
    assert "refused" in resolution.guard_note


# --------------------------------------------------------------------------- #
# Positive controls: a different observation must still be able to clear it
# --------------------------------------------------------------------------- #


@pytest.mark.unit
def test_a_genuinely_new_tree_clears_a_fail(tmp_path: Path) -> None:
    receipts = _chain(
        tmp_path,
        _fail(),
        _pass(head=FIXED_HEAD, tree=FIXED_TREE),
    )

    resolution = _resolve(receipts)

    assert resolution.receipt is not None
    assert resolution.receipt.status is EnumReceiptStatus.PASS
    assert resolution.receipt.tree_sha == FIXED_TREE
    assert resolution.guard_note is None


@pytest.mark.unit
@pytest.mark.parametrize(
    ("fail_tree", "pass_head", "pass_tree"),
    [
        (SHARED_TREE, EMPTY_COMMIT_HEAD, SHARED_TREE),
        (None, FAIL_HEAD, None),
    ],
    ids=["same-tree", "legacy-same-commit"],
)
def test_a_check_definition_fix_at_the_same_code_clears_a_fail_and_says_why(
    tmp_path: Path,
    fail_tree: str | None,
    pass_head: str,
    pass_tree: str | None,
) -> None:
    """The omnimarket#2839 correction: a different check ran, over the same code.

    The first FAIL executed the as-generated four-path command against entry
    8ac0efc7. The correction re-executed the two-path command against entry
    50e6d949. That is a different observation, and the resolution has to say
    why it accepted a PASS at the FAIL's own code.
    """
    receipts = _chain(
        tmp_path,
        _fail(tree=fail_tree, command=FOUR_PATH_COMMAND, entry=AS_GENERATED_ENTRY),
        _pass(head=pass_head, tree=pass_tree),
    )

    resolution = _resolve(receipts)

    assert resolution.receipt is not None
    assert resolution.receipt.status is EnumReceiptStatus.PASS
    assert resolution.guard_note is not None
    assert "check definition changed" in resolution.guard_note
    assert AS_GENERATED_ENTRY in resolution.guard_note
    assert CORRECTED_ENTRY in resolution.guard_note


@pytest.mark.unit
def test_legacy_records_at_different_commits_resolve_exactly_as_before(
    tmp_path: Path,
) -> None:
    """No retroactive change: records written before tree_sha keep their verdict.

    This is the chain on OCC main for omnimarket#2839: two FAILs at f490fba,
    then a PASS at the empty commit 9c09739. None of them carries tree_sha, so
    the guard compares commit ids and the PASS wins, as it did when it merged.
    Making it resolve FAIL now would take eligibility away from evidence that
    has already merged.
    """
    receipts = _chain(
        tmp_path,
        _fail(tree=None),
        _fail(tree=None),
        _pass(head=EMPTY_COMMIT_HEAD, tree=None),
    )

    resolution = _resolve(receipts)

    assert resolution.receipt is not None
    assert resolution.receipt.status is EnumReceiptStatus.PASS
    assert resolution.receipt.commit_sha == EMPTY_COMMIT_HEAD


@pytest.mark.unit
def test_a_tree_on_only_one_record_falls_back_to_commit_identity(
    tmp_path: Path,
) -> None:
    """A tree on one side only cannot be compared. The guard uses commit ids."""
    receipts = _chain(
        tmp_path,
        _fail(tree=None),
        _pass(head=EMPTY_COMMIT_HEAD, tree=SHARED_TREE),
    )

    resolution = _resolve(receipts)

    assert resolution.receipt is not None
    assert resolution.receipt.status is EnumReceiptStatus.PASS


# --------------------------------------------------------------------------- #
# The field itself
# --------------------------------------------------------------------------- #


@pytest.mark.unit
def test_tree_sha_is_optional() -> None:
    receipt = ModelDodReceipt.model_validate(_fail(tree=None))

    assert receipt.tree_sha is None


@pytest.mark.unit
@pytest.mark.parametrize("value", ["7dceb0ed", "7DCEB0ED" + "0" * 32, "g" * 40, ""])
def test_tree_sha_must_be_a_full_lowercase_object_id(value: str) -> None:
    """An abbreviated tree id could match two trees, so only a full id is accepted."""
    with pytest.raises(ValidationError):
        ModelDodReceipt.model_validate(_fail(tree=value))


@pytest.mark.unit
def test_tree_sha_accepts_a_sha256_object_id() -> None:
    tree = "ab" * 32

    receipt = ModelDodReceipt.model_validate(_fail(tree=tree))

    assert receipt.tree_sha == tree


# --------------------------------------------------------------------------- #
# End to end through merge eligibility, the reader that binds
# --------------------------------------------------------------------------- #


def _contract(command: str) -> dict[str, object]:
    return {
        "ticket_id": TICKET,
        "title": "retire the dormant local rebuild classifier",
        "dod_evidence": [
            {
                "id": ITEM,
                "description": "diff-derived behavior proof",
                "checks": [{"check_type": CHECK, "check_value": command}],
            }
        ],
    }


def _eligibility_root(
    root: Path, *receipts: dict[str, object]
) -> ModelOccEligibilityInput:
    """The corrected contract on disk, a PENDING base mint, then the chain."""
    contract = _contract(TWO_PATH_COMMAND)
    (root / "contracts").mkdir(parents=True)
    (root / "contracts" / f"{TICKET}.yaml").write_text(
        yaml.safe_dump(contract, sort_keys=True), encoding="utf-8"
    )
    receipts_root = _chain(root, *receipts)
    base = _receipt(
        status=EnumReceiptStatus.PENDING,
        head=FAIL_HEAD,
        tree=None,
        command=TWO_PATH_COMMAND,
        entry=compute_contract_entry_sha256(contract, ITEM),
    )
    base["probe_stdout"] = ""
    base["exit_code"] = None
    (receipts_root / TICKET / ITEM / f"{CHECK}.yaml").write_text(
        yaml.safe_dump(base, sort_keys=True), encoding="utf-8"
    )
    return ModelOccEligibilityInput(
        repo="omnimarket",
        pr_number=PR,
        pr_title=f"fix({TICKET}): retire the dormant local rebuild classifier",
        pr_body=f"Closes: {TICKET}",
        pr_branch="jonah/omn-19378-retire-stale-rebuild-classifier",
        pr_commit_shas=(FAIL_HEAD, EMPTY_COMMIT_HEAD),
        pr_commit_texts=(f"fix({TICKET}): retire the classifier",),
        occ_commit_sha="c" * 40,
        contracts_dir=root / "contracts",
        receipts_dir=receipts_root,
    )


CURRENT_ENTRY = compute_contract_entry_sha256(_contract(TWO_PATH_COMMAND), ITEM)
PREVIOUS_ENTRY = compute_contract_entry_sha256(_contract(FOUR_PATH_COMMAND), ITEM)


@pytest.mark.unit
def test_eligibility_refuses_an_empty_commit_pass_and_says_why(tmp_path: Path) -> None:
    snapshot = _eligibility_root(
        tmp_path,
        _fail(entry=CURRENT_ENTRY),
        _pass(head=EMPTY_COMMIT_HEAD, tree=SHARED_TREE, entry=CURRENT_ENTRY),
    )

    result = validate_occ_merge_eligibility(snapshot)

    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.NONPASS_RECEIPT
    assert result.missing_or_nonpass_receipts == (f"{TICKET}:{ITEM}:{CHECK}",)
    assert "supersession guard" in result.detail
    assert "refused" in result.detail


@pytest.mark.unit
def test_eligibility_accepts_a_check_definition_fix_and_says_why(
    tmp_path: Path,
) -> None:
    snapshot = _eligibility_root(
        tmp_path,
        _fail(command=FOUR_PATH_COMMAND, entry=PREVIOUS_ENTRY),
        _pass(head=EMPTY_COMMIT_HEAD, tree=SHARED_TREE, entry=CURRENT_ENTRY),
    )

    result = validate_occ_merge_eligibility(snapshot)

    assert result.eligible is True, result.detail
    assert result.reason is EnumOccEligibilityReason.ELIGIBLE
    assert "check definition changed" in result.detail


@pytest.mark.unit
def test_eligibility_accepts_a_genuinely_new_tree(tmp_path: Path) -> None:
    snapshot = _eligibility_root(
        tmp_path,
        _fail(entry=CURRENT_ENTRY),
        _pass(head=EMPTY_COMMIT_HEAD, tree=FIXED_TREE, entry=CURRENT_ENTRY),
    )

    result = validate_occ_merge_eligibility(snapshot)

    assert result.eligible is True, result.detail
    assert "supersession guard" not in result.detail
