# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Commit-time base of the canonical-file-shape ratchet (OMN-21515).

With no ``--base``, the index is compared with the merge base of ``HEAD`` and the
landing ref, the way CI compares a pull request, so a branch that already
committed the ticketed burn-down file can still add the findings that exist at
the merge base. With no landing ref the base stays ``HEAD``.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from omnibase_core.nodes.node_canonical_file_shape_check_compute.runtime_canonical_file_shape_check import (
    main,
)
from omnibase_core.validators.no_unguarded_git_subprocess import (
    scrub_git_location_env,
)
from tests.unit.nodes.node_canonical_file_shape_check_compute.support import (
    IDENTITY,
    RULES,
    git,
    init_repo,
    issues,
    rules_hit,
    stage,
    write,
)

pytestmark = pytest.mark.unit

BURNDOWN = RULES.parameters.burndown_baseline_path
HEADER = RULES.parameters.burndown_baseline_header.format(ticket="OMN-21523")
CODE = "".join(f"value_{n} = {n}\n" for n in range(12))
LANDING = "refs/remotes/origin/dev"


def _burndown(*paths: str) -> str:
    return HEADER + "".join(f"{path}\n" for path in paths)


def _land_at_head(repo: Path) -> None:
    """Make the current commit the landing branch of ``repo`` through ``origin/HEAD``."""
    git(repo, "update-ref", LANDING, "HEAD")
    git(repo, "symbolic-ref", "refs/remotes/origin/HEAD", LANDING)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """Merge base: scripts/a.py baselined, scripts/b.py and scripts/c.py refused and unlisted."""
    write(tmp_path, "scripts/a.py", CODE)
    write(tmp_path, "scripts/b.py", CODE + "# b\n")
    write(tmp_path, "scripts/c.py", CODE + "# c\n")
    write(tmp_path, "src/pkg/models/model_ok.py", "ok = 1\n")
    init_repo(tmp_path, baselined=["scripts/a.py"])
    _land_at_head(tmp_path)
    git(tmp_path, "checkout", "-q", "-b", "feature")
    return tmp_path


@pytest.fixture
def branch_installed(repo: Path) -> Path:
    """``repo`` after a branch commit installed the burn-down file; the merge base has none."""
    write(repo, BURNDOWN, _burndown("scripts/b.py"))
    stage(repo)
    git(repo, "commit", "-q", "-m", "install burn-down")
    return repo


def _codes(repo: Path) -> list[tuple[str, str]]:
    return sorted((issue.code or "", str(issue.file_path)) for issue in issues(repo))


def test_a_base_finding_added_to_the_file_the_branch_installed_is_admitted(
    branch_installed: Path,
) -> None:
    write(branch_installed, BURNDOWN, _burndown("scripts/b.py", "scripts/c.py"))
    stage(branch_installed)
    assert rules_hit(branch_installed) == []


def test_the_same_change_is_refused_against_head_when_no_landing_ref_resolves(
    branch_installed: Path,
) -> None:
    git(branch_installed, "symbolic-ref", "--delete", "refs/remotes/origin/HEAD")
    write(branch_installed, BURNDOWN, _burndown("scripts/b.py", "scripts/c.py"))
    stage(branch_installed)
    assert _codes(branch_installed) == [("baseline-growth", BURNDOWN)]


def test_the_landing_ref_is_the_contracts_parameter(branch_installed: Path) -> None:
    elsewhere = RULES.model_copy(
        update={
            "parameters": RULES.parameters.model_copy(
                update={"landing_ref": "refs/remotes/origin/absent"}
            )
        }
    )
    write(branch_installed, BURNDOWN, _burndown("scripts/b.py", "scripts/c.py"))
    stage(branch_installed)
    assert [issue.code for issue in issues(branch_installed, rules=elsewhere)] == [
        "baseline-growth"
    ]


def test_an_explicit_base_wins_over_the_landing_ref(branch_installed: Path) -> None:
    write(branch_installed, BURNDOWN, _burndown("scripts/b.py", "scripts/c.py"))
    stage(branch_installed)
    assert rules_hit(branch_installed, base="HEAD") == ["baseline-growth"]


def test_the_commit_time_hook_admits_the_same_change(branch_installed: Path) -> None:
    write(branch_installed, BURNDOWN, _burndown("scripts/b.py", "scripts/c.py"))
    stage(branch_installed)
    assert (
        main(["--repo-root", str(branch_installed)], env=scrub_git_location_env()) == 0
    )


def test_an_entry_for_a_file_the_branch_added_is_still_refused(
    branch_installed: Path,
) -> None:
    write(branch_installed, "scripts/new.py", CODE + "# new\n")
    write(
        branch_installed,
        BURNDOWN,
        _burndown("scripts/b.py", "scripts/c.py", "scripts/new.py"),
    )
    stage(branch_installed)
    assert _codes(branch_installed) == [("burndown-extra-entry", BURNDOWN)]


def test_growth_is_still_refused_when_the_file_exists_at_the_merge_base(
    repo: Path,
) -> None:
    write(repo, BURNDOWN, _burndown("scripts/b.py"))
    stage(repo)
    git(repo, "commit", "-q", "-m", "install burn-down")
    _land_at_head(repo)
    write(repo, BURNDOWN, _burndown("scripts/b.py", "scripts/c.py"))
    stage(repo)
    assert _codes(repo) == [("baseline-growth", BURNDOWN)]


def test_a_landing_ref_with_unrelated_history_falls_back_to_head(
    branch_installed: Path,
) -> None:
    empty_tree = subprocess.run(
        ["git", "hash-object", "-t", "tree", "-w", "--stdin"],
        cwd=branch_installed,
        env=scrub_git_location_env(),
        input=b"",
        capture_output=True,
        check=True,
    ).stdout.decode()
    island = subprocess.run(
        ["git", *IDENTITY, "commit-tree", empty_tree.strip(), "-m", "island"],
        cwd=branch_installed,
        env=scrub_git_location_env(),
        capture_output=True,
        check=True,
    ).stdout.decode()
    git(branch_installed, "update-ref", LANDING, island.strip())
    write(branch_installed, BURNDOWN, _burndown("scripts/b.py", "scripts/c.py"))
    stage(branch_installed)
    assert _codes(branch_installed) == [("baseline-growth", BURNDOWN)]
