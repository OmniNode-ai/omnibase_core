# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""The bypass count file is judged against the merge base with the base branch, and fails closed (OMN-25336).

The ratchet compared the count file with ``git show HEAD:<file>``. On a CI checkout ``HEAD`` is the
commit being judged, so a pull request that raised the file compared it with itself and the
"the file may not be raised" refusal could never fire; a git error skipped the comparison. The
failing controls are a committed raise (read healthy at ``HEAD``) and an unreadable base (read as no
base at all).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from omnibase_core.validation.validator_effect_node_bypass import (
    ValidatorEffectNodeBypass,
)
from omnibase_core.validators.no_unguarded_git_subprocess import scrub_git_location_env

_CLI = (
    "import subprocess\n\n"
    "def merge(n: int) -> None:\n"
    '    subprocess.run(["gh", "pr", "merge", str(n)], check=True)\n'
)
_API = 'URL = f"https://api.github.com/repos/{{repo}}/pulls"\n'
_COUNT_FILE = Path("config/ratchet.yaml")


def _git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
        cwd=root,
        env=scrub_git_location_env(),
        check=True,
        capture_output=True,
    )


def _commit(root: Path, ratchet: int, planted: dict[str, str], message: str) -> None:
    count_file = root / _COUNT_FILE
    count_file.parent.mkdir(parents=True, exist_ok=True)
    count_file.write_text(f"max_bypasses: {ratchet}\n", encoding="utf-8")
    for name, source in planted.items():
        (root / "pkg").mkdir(exist_ok=True)
        (root / "pkg" / f"{name}.py").write_text(source, encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", message)


def _validator_on(
    root: Path, ratchet: int, base_ref: str | None
) -> ValidatorEffectNodeBypass:
    return ValidatorEffectNodeBypass(
        root=root, ratchet=ratchet, ratchet_path=_COUNT_FILE, base_ref=base_ref
    )


def _validator(root: Path, ratchet: int) -> ValidatorEffectNodeBypass:
    """The validator whose caller names ``origin/dev`` as the base, as the repository's hook does."""
    return _validator_on(root, ratchet, "origin/dev")


@pytest.mark.unit
def test_bypass_base_ref_a_committed_raise_is_refused_against_the_merge_base(
    tmp_path: Path,
) -> None:
    """On a CI checkout HEAD is the judged commit: the raise is already committed."""
    _git(tmp_path, "init", "-q")
    _commit(tmp_path, 1, {"one": _CLI}, "base")
    _git(tmp_path, "update-ref", "refs/remotes/origin/dev", "HEAD")
    _commit(tmp_path, 2, {"two": _API}, "raise the count file")

    result = _validator(tmp_path, 2).validate([tmp_path])

    assert not result.is_valid
    assert "base revision holds 1" in result.issues[0].message


@pytest.mark.unit
def test_bypass_base_ref_compares_with_the_merge_base_not_the_moved_base_tip(
    tmp_path: Path,
) -> None:
    """Positive control: a base branch that moved on does not make an unchanged file look raised."""
    _git(tmp_path, "init", "-q")
    _commit(tmp_path, 1, {"one": _CLI}, "base")
    _git(tmp_path, "branch", "feature")
    _commit(tmp_path, 0, {"one": "VALUE = 1\n"}, "base branch lowers the count")
    _git(tmp_path, "update-ref", "refs/remotes/origin/dev", "HEAD")
    _git(tmp_path, "checkout", "-q", "feature")

    result = _validator(tmp_path, 1).validate([tmp_path])

    assert result.is_valid, [i.message for i in result.issues]


@pytest.mark.unit
def test_bypass_base_ref_a_count_file_new_to_the_branch_is_not_a_raise(
    tmp_path: Path,
) -> None:
    _git(tmp_path, "init", "-q")
    (tmp_path / "README.md").write_text("x\n", encoding="utf-8")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "base")
    _git(tmp_path, "update-ref", "refs/remotes/origin/dev", "HEAD")
    _commit(tmp_path, 1, {"one": _CLI}, "add the count file")

    assert _validator(tmp_path, 1).validate([tmp_path]).is_valid


@pytest.mark.unit
def test_bypass_base_ref_unreadable_base_fails_closed(tmp_path: Path) -> None:
    """Failing control: no base branch ref to compare with is a finding, not a skipped check."""
    _git(tmp_path, "init", "-q")
    _commit(tmp_path, 1, {"one": _CLI}, "only commit, no origin/dev")

    result = _validator(tmp_path, 1).validate([tmp_path])

    assert not result.is_valid
    assert "cannot read" in result.issues[0].message
    assert result.issues[0].rule_name == "count_ratchet"


@pytest.mark.unit
def test_bypass_base_ref_outside_a_git_checkout_fails_closed(tmp_path: Path) -> None:
    (tmp_path / _COUNT_FILE).parent.mkdir(parents=True)
    (tmp_path / _COUNT_FILE).write_text("max_bypasses: 0\n", encoding="utf-8")

    result = _validator(tmp_path, 0).validate([tmp_path])

    assert not result.is_valid
    assert "cannot read" in result.issues[0].message


# --- OMN-25394 (review finding 2): the base ref comes from the caller, never from the contract ---

_CONTRACT = Path(
    "src/omnibase_core/validation/contracts/effect_node_bypass.validation.yaml"
)
_PRECOMMIT = Path(".pre-commit-config.yaml")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


@pytest.mark.unit
def test_bypass_base_ref_contract_does_not_hard_code_origin_dev() -> None:
    """Failing control: the shipped contract named origin/dev, so a repo without that ref was refused."""
    text = (_repo_root() / _CONTRACT).read_text(encoding="utf-8")
    assert "origin/dev" not in text


@pytest.mark.unit
def test_bypass_base_ref_with_no_base_supplied_does_not_refuse_a_checkout_without_origin_dev(
    tmp_path: Path,
) -> None:
    """A downstream repo (or a shallow checkout) with no origin/dev and no caller ref is not refused."""
    _git(tmp_path, "init", "-q")
    _commit(tmp_path, 1, {"one": _CLI}, "only commit, no origin/dev")

    result = ValidatorEffectNodeBypass(
        root=tmp_path, ratchet=1, ratchet_path=_COUNT_FILE
    ).validate([tmp_path])

    assert result.is_valid, [i.message for i in result.issues]


@pytest.mark.unit
def test_bypass_base_ref_a_caller_ref_that_cannot_be_read_fails_closed(
    tmp_path: Path,
) -> None:
    """A ref the caller names and git cannot resolve is a refusal, never a skipped check."""
    _git(tmp_path, "init", "-q")
    _commit(tmp_path, 1, {"one": _CLI}, "only commit")

    result = _validator_on(tmp_path, 1, "origin/does-not-exist").validate([tmp_path])

    assert not result.is_valid
    assert "cannot read" in result.issues[0].message
    assert "origin/does-not-exist" in result.issues[0].message


@pytest.mark.unit
def test_bypass_base_ref_a_caller_ref_other_than_origin_dev_judges_the_raise(
    tmp_path: Path,
) -> None:
    _git(tmp_path, "init", "-q")
    _commit(tmp_path, 1, {"one": _CLI}, "base")
    _git(tmp_path, "update-ref", "refs/remotes/origin/main", "HEAD")
    _commit(tmp_path, 2, {"two": _API}, "raise the count file")

    result = _validator_on(tmp_path, 2, "origin/main").validate([tmp_path])

    assert not result.is_valid
    assert "base revision holds 1" in result.issues[0].message


@pytest.mark.unit
def test_bypass_base_ref_the_hook_passes_the_caller_ref_and_the_runtime_takes_it() -> (
    None
):
    """The repository's own hook is the caller: it names the base, and the runtime has the flag."""
    config = (_repo_root() / _PRECOMMIT).read_text(encoding="utf-8")
    hook = config[config.index("id: no-effect-node-bypass") :]
    hook = hook[: hook.index("always_run")]
    assert "--base-ref" in hook
    runtime = (
        _repo_root()
        / "src/omnibase_core/nodes/node_validation_report_write_effect/runtime_validator_run.py"
    ).read_text(encoding="utf-8")
    assert '"--base-ref"' in runtime
