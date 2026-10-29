# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""The index run compares with the merge base of HEAD and the target branch (OMN-21523).

The CI run resets to the merge base with the target branch, so its index holds the whole
pull request. The pre-commit run used to compare the index with branch ``HEAD``: on a branch
whose earlier commit installed the burn-down file, the next correct line read as growth of
an installed file and was refused, while CI accepted the same change. Each case names the
refusal the old comparison base gives, so the fix is a failing test before and a passing
one after.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from omnibase_core.nodes.node_canonical_file_shape_check_compute.runtime_canonical_file_shape_check import (
    GitRepo,
    resolve_revisions,
    target_merge_base,
)
from omnibase_core.validators.no_unguarded_git_subprocess import (
    scrub_git_location_env,
)
from tests.unit.nodes.node_canonical_file_shape_check_compute.support import (
    BASELINE,
    RULES,
    baseline_text,
    git,
    init_repo,
    issues,
    rules_hit,
    stage,
    write,
)

pytestmark = pytest.mark.unit

P = RULES.parameters
BURNDOWN = P.burndown_baseline_path
TICKET = "OMN-21523"
HEADER = P.burndown_baseline_header.format(ticket=TICKET)
CODE = "".join(f"value_{n} = {n}\n" for n in range(12))


def _burndown(*paths: str) -> str:
    return HEADER + "".join(f"{path}\n" for path in paths)


def _out(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.com", *args],
        cwd=repo,
        env=scrub_git_location_env(),
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _git_repo(repo: Path) -> GitRepo:
    return GitRepo(
        root=repo,
        env=scrub_git_location_env(),
        cat_file_timeout_s=P.cat_file_timeout_s,
    )


@pytest.fixture
def base_repo(tmp_path: Path) -> Path:
    """The target branch: scripts/a.py baselined, scripts/b.py and scripts/c.py refused unlisted."""
    write(tmp_path, "scripts/a.py", CODE)
    write(tmp_path, "scripts/b.py", CODE + "# b\n")
    write(tmp_path, "scripts/c.py", CODE + "# c\n")
    write(tmp_path, "src/pkg/models/model_ok.py", "ok = 1\n")
    init_repo(tmp_path, baselined=["scripts/a.py"])
    git(tmp_path, "update-ref", "refs/remotes/origin/dev", "HEAD")
    return tmp_path


@pytest.fixture
def installed_branch(base_repo: Path) -> Path:
    """A feature branch whose earlier commit installed the burn-down file listing scripts/b.py."""
    git(base_repo, "checkout", "-q", "-b", "feature")
    write(base_repo, BURNDOWN, _burndown("scripts/b.py"))
    stage(base_repo)
    git(base_repo, "commit", "-q", "-m", f"install the burn-down for {TICKET}")
    return base_repo


# --- the reported refusal: a correct line on a branch that already installed the file ----


def test_a_correct_burndown_line_after_an_earlier_install_commit_is_accepted(
    installed_branch: Path,
) -> None:
    """CI accepts this change against the merge base; so must the index run."""
    write(installed_branch, BURNDOWN, _burndown("scripts/b.py", "scripts/c.py"))
    stage(installed_branch)
    assert rules_hit(installed_branch) == []


def test_planted_old_base_refuses_the_same_correct_line_as_baseline_growth(
    installed_branch: Path,
) -> None:
    """Falsifier: against branch HEAD, the old base, the line above is baseline-growth."""
    write(installed_branch, BURNDOWN, _burndown("scripts/b.py", "scripts/c.py"))
    stage(installed_branch)
    assert rules_hit(installed_branch, base="HEAD") == ["baseline-growth"]


def test_the_default_base_is_the_merge_base_with_the_target_branch(
    installed_branch: Path,
) -> None:
    merge_base = _out(installed_branch, "rev-parse", "origin/dev")
    assert merge_base != _out(installed_branch, "rev-parse", "HEAD")
    assert resolve_revisions(_git_repo(installed_branch), None, None, P) == (
        ":",
        merge_base,
    )


# --- real growth is still refused ---------------------------------------------------


def test_a_burndown_entry_for_a_file_the_change_adds_is_still_refused(
    installed_branch: Path,
) -> None:
    write(installed_branch, "scripts/new.py", CODE)
    write(installed_branch, BURNDOWN, _burndown("scripts/b.py", "scripts/new.py"))
    stage(installed_branch)
    found = issues(installed_branch)
    assert [(issue.code, str(issue.file_path)) for issue in found] == [
        ("burndown-extra-entry", BURNDOWN)
    ]


def test_a_burndown_entry_the_baseline_already_lists_is_still_refused(
    installed_branch: Path,
) -> None:
    write(installed_branch, BURNDOWN, _burndown("scripts/a.py", "scripts/b.py"))
    stage(installed_branch)
    assert rules_hit(installed_branch) == ["burndown-extra-entry"]


def test_growth_of_the_baseline_committed_earlier_on_the_branch_is_refused(
    base_repo: Path,
) -> None:
    """Against branch HEAD this reads clean; against the merge base it is the growth CI refuses."""
    git(base_repo, "checkout", "-q", "-b", "feature")
    write(base_repo, "scripts/new.py", CODE)
    write(base_repo, BASELINE, baseline_text(["scripts/a.py", "scripts/new.py"]))
    stage(base_repo)
    git(base_repo, "commit", "-q", "-m", "grow the baseline")
    write(base_repo, "src/pkg/models/model_ok.py", "ok = 2\n")
    stage(base_repo)
    assert rules_hit(base_repo, base="HEAD") == []
    assert "baseline-growth" in rules_hit(base_repo)


def test_a_new_noncanonical_file_is_still_refused_on_a_branch(
    installed_branch: Path,
) -> None:
    write(installed_branch, "scripts/new.py", CODE)
    stage(installed_branch)
    assert rules_hit(installed_branch) == ["noncanonical-file"]


# --- the commit-message rule reads the range, as the CI run does -----------------------


def test_a_ticket_cited_by_an_earlier_commit_of_the_range_is_cited(
    installed_branch: Path,
) -> None:
    write(installed_branch, BURNDOWN, _burndown("scripts/b.py", "scripts/c.py"))
    stage(installed_branch)
    assert rules_hit(installed_branch, commit_message="burn down one more path") == []


def test_planted_ticket_cited_by_no_commit_of_the_range_is_refused(
    base_repo: Path,
) -> None:
    git(base_repo, "checkout", "-q", "-b", "feature")
    write(base_repo, BURNDOWN, _burndown("scripts/b.py"))
    stage(base_repo)
    git(base_repo, "commit", "-q", "-m", "install a burn-down")
    write(base_repo, BURNDOWN, _burndown("scripts/b.py", "scripts/c.py"))
    stage(base_repo)
    assert rules_hit(base_repo, commit_message="burn down one more path") == [
        "burndown-ticket-uncited"
    ]


# --- which ref names the target branch ---------------------------------------------------


def test_origin_head_names_the_target_branch_before_the_fixed_refs(
    base_repo: Path,
) -> None:
    git(base_repo, "checkout", "-q", "-b", "feature")
    write(base_repo, "src/pkg/models/model_two.py", "two = 2\n")
    stage(base_repo)
    git(base_repo, "commit", "-q", "-m", "second")
    git(base_repo, "update-ref", "refs/remotes/origin/trunk", "HEAD")
    git(
        base_repo,
        "symbolic-ref",
        "refs/remotes/origin/HEAD",
        "refs/remotes/origin/trunk",
    )
    assert target_merge_base(_git_repo(base_repo), P) == _out(
        base_repo, "rev-parse", "HEAD"
    )


def test_the_main_ref_is_the_target_when_no_dev_ref_exists(base_repo: Path) -> None:
    git(base_repo, "update-ref", "refs/remotes/origin/main", "HEAD")
    git(base_repo, "update-ref", "-d", "refs/remotes/origin/dev")
    assert target_merge_base(_git_repo(base_repo), P) == _out(
        base_repo, "rev-parse", "HEAD"
    )


def test_with_no_target_ref_the_base_is_head(base_repo: Path) -> None:
    git(base_repo, "update-ref", "-d", "refs/remotes/origin/dev")
    assert target_merge_base(_git_repo(base_repo), P) is None
    assert resolve_revisions(_git_repo(base_repo), None, None, P) == (":", "HEAD")


def test_with_no_common_ancestor_the_base_is_head(base_repo: Path) -> None:
    empty_tree = _out(base_repo, "hash-object", "-t", "tree", "/dev/null")
    unrelated = _out(base_repo, "commit-tree", empty_tree, "-m", "unrelated")
    git(base_repo, "update-ref", "refs/remotes/origin/dev", unrelated)
    assert resolve_revisions(_git_repo(base_repo), None, None, P) == (":", "HEAD")


def test_an_explicit_base_wins_over_the_target_branch(installed_branch: Path) -> None:
    assert resolve_revisions(_git_repo(installed_branch), "HEAD", None, P) == (
        ":",
        "HEAD",
    )
