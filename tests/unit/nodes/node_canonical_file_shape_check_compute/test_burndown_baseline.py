# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Ticketed burn-down baseline of the canonical-file-shape ratchet (OMN-21515).

A repository that already carries ``baseline_path`` installs the second,
ticketed file once for the findings a new rule adds; after that it only shrinks.
Each refusal has a planted-growth case here and each rule a clean case.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.nodes.node_canonical_file_shape_check_compute.runtime_canonical_file_shape_check import (
    main,
)
from omnibase_core.validators.no_unguarded_git_subprocess import (
    scrub_git_location_env,
)
from tests.unit.nodes.node_canonical_file_shape_check_compute.support import (
    BASELINE,
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
TICKET = "OMN-21523"
HEADER = RULES.parameters.burndown_baseline_header.format(ticket=TICKET)
CODE = "".join(f"value_{n} = {n}\n" for n in range(12))


def _burndown(*paths: str, header: str = HEADER) -> str:
    return header + "".join(f"{path}\n" for path in paths)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A repository with ``baseline_path`` listing scripts/a.py and scripts/b.py refused unlisted."""
    write(tmp_path, "scripts/a.py", CODE)
    write(tmp_path, "scripts/b.py", CODE + "# b\n")
    write(tmp_path, "src/pkg/models/model_ok.py", "ok = 1\n")
    return init_repo(tmp_path, baselined=["scripts/a.py"])


@pytest.fixture
def installed(repo: Path) -> Path:
    """``repo`` after the first install committed: the base now has the burn-down file."""
    write(repo, BURNDOWN, _burndown("scripts/b.py"))
    stage(repo)
    git(repo, "commit", "-q", "-m", "install burn-down")
    return repo


def _locations(repo: Path) -> list[tuple[str, str]]:
    return sorted((issue.code or "", str(issue.file_path)) for issue in issues(repo))


# --- first install --------------------------------------------------------------


def test_without_the_burndown_file_the_unlisted_path_is_refused(repo: Path) -> None:
    assert _locations(repo) == [("noncanonical-file", "scripts/b.py")]


def test_first_install_is_accepted_in_a_repository_that_already_has_baseline_path(
    repo: Path,
) -> None:
    write(repo, BURNDOWN, _burndown("scripts/b.py"))
    stage(repo)
    assert rules_hit(repo) == []
    assert "scripts/b.py" not in (repo / BASELINE).read_text()


def test_first_install_lists_only_paths_the_head_tree_is_refused_for(
    repo: Path,
) -> None:
    write(repo, BURNDOWN, _burndown("scripts/b.py", "scripts/gone.py"))
    stage(repo)
    assert _locations(repo) == [("baseline-stale", BURNDOWN)]


def test_planted_entry_without_a_ticket_at_install_is_burndown_ticket_missing(
    repo: Path,
) -> None:
    write(repo, BURNDOWN, _burndown("scripts/b.py", header="# burn-down baseline\n"))
    stage(repo)
    assert _locations(repo) == [("burndown-ticket-missing", BURNDOWN)]


def test_a_ticket_that_is_not_on_the_first_comment_line_does_not_count(
    repo: Path,
) -> None:
    write(
        repo,
        BURNDOWN,
        _burndown("scripts/b.py", header=f"# notes\n# Burn-down ticket: {TICKET}\n"),
    )
    stage(repo)
    assert rules_hit(repo) == ["burndown-ticket-missing"]


def test_a_path_listed_by_either_file_is_admitted(repo: Path) -> None:
    write(repo, BURNDOWN, _burndown("scripts/b.py"))
    stage(repo)
    assert rules_hit(repo) == []
    assert "scripts/a.py" in (repo / BASELINE).read_text()


def test_the_existing_baseline_is_never_extended_by_the_switch(repo: Path) -> None:
    """A new line in ``baseline_path`` is still ``baseline-growth``."""
    write(repo, BASELINE, (repo / BASELINE).read_text() + "scripts/b.py\n")
    stage(repo)
    assert _locations(repo) == [("baseline-growth", BASELINE)]


def test_first_install_does_not_open_the_old_baseline_for_growth(repo: Path) -> None:
    write(repo, "scripts/c.py", CODE)
    write(repo, BASELINE, (repo / BASELINE).read_text() + "scripts/c.py\n")
    write(repo, BURNDOWN, _burndown("scripts/b.py"))
    stage(repo)
    assert _locations(repo) == [("baseline-growth", BASELINE)]


# --- first install admits only base findings, under its own ticket ---------------


def test_planted_extra_line_at_install_as_an_added_file_is_burndown_extra_entry(
    repo: Path,
) -> None:
    """A brand-new violating file listed in the install is not a finding at base."""
    write(repo, "scripts/c.py", CODE)
    write(repo, BURNDOWN, _burndown("scripts/b.py", "scripts/c.py"))
    stage(repo)
    assert _locations(repo) == [("burndown-extra-entry", BURNDOWN)]
    [issue] = issues(repo)
    assert issue.message == RULES.parameters.burndown_extra_added_text.format(
        path="scripts/c.py", status="A"
    )


def test_planted_extra_line_at_install_as_a_renamed_in_file_is_burndown_extra_entry(
    repo: Path,
) -> None:
    git(repo, "mv", "scripts/b.py", "scripts/b2.py")
    write(repo, BURNDOWN, _burndown("scripts/b2.py"))
    stage(repo)
    assert _locations(repo) == [("burndown-extra-entry", BURNDOWN)]
    [issue] = issues(repo)
    assert issue.message == RULES.parameters.burndown_extra_added_text.format(
        path="scripts/b2.py", status="R"
    )


def test_planted_extra_line_at_install_duplicating_baseline_path_is_burndown_extra_entry(
    repo: Path,
) -> None:
    """scripts/a.py is already an admitted entry of ``baseline_path``."""
    write(repo, BURNDOWN, _burndown("scripts/a.py", "scripts/b.py"))
    stage(repo)
    assert _locations(repo) == [("burndown-extra-entry", BURNDOWN)]
    [issue] = issues(repo)
    assert issue.message == RULES.parameters.burndown_extra_duplicate_text.format(
        path="scripts/a.py", baseline=BASELINE
    )


def test_each_extra_entry_at_install_gets_its_own_issue(repo: Path) -> None:
    write(repo, "scripts/c.py", CODE)
    write(repo, BURNDOWN, _burndown("scripts/a.py", "scripts/b.py", "scripts/c.py"))
    stage(repo)
    assert rules_hit(repo) == ["burndown-extra-entry"] * 2


def test_a_modified_base_finding_is_not_an_extra_entry(repo: Path) -> None:
    """A file that existed at base and changed is still a base finding."""
    write(repo, "scripts/b.py", CODE + "# b\n# touched\n")
    write(repo, BURNDOWN, _burndown("scripts/b.py"))
    stage(repo)
    assert rules_hit(repo) == []


def test_planted_ticket_uncited_at_install_is_refused(repo: Path) -> None:
    write(repo, BURNDOWN, _burndown("scripts/b.py"))
    stage(repo)
    found = issues(repo, commit_message="chore: refresh the file-shape baselines\n")
    assert [(i.code, str(i.file_path)) for i in found] == [
        ("burndown-ticket-uncited", BURNDOWN)
    ]
    assert found[0].message == RULES.parameters.burndown_ticket_uncited_text.format(
        ticket=TICKET
    )


def test_a_ticket_cited_in_the_commit_message_admits_the_install(repo: Path) -> None:
    write(repo, BURNDOWN, _burndown("scripts/b.py"))
    stage(repo)
    assert (
        rules_hit(repo, commit_message=f"fix({TICKET}): install the burn-down\n") == []
    )


@pytest.mark.parametrize("cited", ["OMN-215230", "XOMN-21523", "OMN-2152"])
def test_a_ticket_that_only_shares_a_prefix_with_the_header_is_not_cited(
    repo: Path, cited: str
) -> None:
    write(repo, BURNDOWN, _burndown("scripts/b.py"))
    stage(repo)
    assert rules_hit(repo, commit_message=f"fix({cited}): install\n") == [
        "burndown-ticket-uncited"
    ]


def test_the_ticket_uncited_rule_is_deferred_while_the_message_is_unknown(
    repo: Path,
) -> None:
    """A pre-commit run on the index knows no message; the commit-msg stage and the revision run do."""
    write(repo, BURNDOWN, _burndown("scripts/b.py"))
    stage(repo)
    assert rules_hit(repo, commit_message=None) == []


def test_the_revision_run_reads_the_messages_of_the_commit_range(repo: Path) -> None:
    write(repo, BURNDOWN, _burndown("scripts/b.py"))
    stage(repo)
    git(repo, "commit", "-q", "-m", "chore: refresh the baselines")
    assert rules_hit(repo, base="HEAD~1", head="HEAD") == ["burndown-ticket-uncited"]
    write(repo, "docs/note.md", "note\n")
    stage(repo)
    git(repo, "commit", "-q", "-m", f"fix({TICKET}): the ticket's own change")
    assert rules_hit(repo, base="HEAD~2", head="HEAD") == []


def test_the_uncited_rule_does_not_apply_after_install(installed: Path) -> None:
    write(installed, "docs/note.md", "note\n")
    stage(installed)
    assert rules_hit(installed, commit_message="chore: unrelated\n") == []


# --- after install: shrink-only -------------------------------------------------


def test_after_install_the_file_with_no_change_is_clean(installed: Path) -> None:
    assert rules_hit(installed) == []


def test_planted_growth_after_install_is_baseline_growth(installed: Path) -> None:
    write(installed, "scripts/c.py", CODE)
    write(installed, BURNDOWN, _burndown("scripts/b.py", "scripts/c.py"))
    stage(installed)
    assert _locations(installed) == [("baseline-growth", BURNDOWN)]
    [issue] = issues(installed)
    assert "scripts/c.py" in issue.message
    assert RULES.parameters.burndown_growth_text.format(path="scripts/c.py") == (
        issue.message
    )


def test_deleting_an_entry_after_install_shrinks_cleanly(installed: Path) -> None:
    git(installed, "rm", "-q", "scripts/b.py")
    write(installed, BURNDOWN, _burndown())
    stage(installed)
    assert rules_hit(installed) == []


def test_a_one_for_one_rename_is_admitted_after_install(installed: Path) -> None:
    git(installed, "mv", "scripts/b.py", "scripts/b2.py")
    write(installed, BURNDOWN, _burndown("scripts/b2.py"))
    stage(installed)
    assert rules_hit(installed) == []


def test_a_rename_that_keeps_the_old_entry_and_adds_one_is_growth(
    installed: Path,
) -> None:
    git(installed, "mv", "scripts/b.py", "scripts/b2.py")
    write(installed, BURNDOWN, _burndown("scripts/b.py", "scripts/b2.py"))
    stage(installed)
    assert _locations(installed) == [("baseline-growth", BURNDOWN)]


def test_a_burndown_entry_that_is_now_canonical_is_stale(installed: Path) -> None:
    git(installed, "mv", "scripts/b.py", "src/pkg/models/model_b.py")
    stage(installed)
    assert _locations(installed) == [("baseline-stale", BURNDOWN)]


def test_a_listed_file_that_grows_is_baselined_file_growth(installed: Path) -> None:
    write(installed, "scripts/b.py", CODE + "# b\nextra = 1\n")
    stage(installed)
    assert rules_hit(installed) == ["baselined-file-growth"]


def test_planted_deletion_with_entries_is_burndown_baseline_removed(
    installed: Path,
) -> None:
    git(installed, "rm", "-q", BURNDOWN)
    stage(installed)
    assert "burndown-baseline-removed" in rules_hit(installed)


def test_planted_deletion_when_empty_is_burndown_baseline_removed(
    installed: Path,
) -> None:
    git(installed, "rm", "-q", "scripts/b.py")
    write(installed, BURNDOWN, _burndown())
    stage(installed)
    git(installed, "commit", "-q", "-m", "burn down")
    git(installed, "rm", "-q", BURNDOWN)
    stage(installed)
    assert _locations(installed) == [("burndown-baseline-removed", BURNDOWN)]


def test_an_empty_file_that_stays_is_clean(installed: Path) -> None:
    git(installed, "rm", "-q", "scripts/b.py")
    write(installed, BURNDOWN, _burndown())
    stage(installed)
    assert rules_hit(installed) == []


def test_planted_second_install_with_other_entries_is_baseline_growth(
    installed: Path,
) -> None:
    """The base already has the file; the head rewrites it under another ticket with other entries."""
    write(installed, "scripts/c.py", CODE)
    write(
        installed,
        BURNDOWN,
        _burndown(
            "scripts/b.py",
            "scripts/c.py",
            header=RULES.parameters.burndown_baseline_header.format(ticket="OMN-21524"),
        ),
    )
    stage(installed)
    assert _locations(installed) == [("baseline-growth", BURNDOWN)]


def test_planted_second_install_replacing_the_entries_is_baseline_growth(
    installed: Path,
) -> None:
    """Content unlike the deleted file, so git reads an add and a delete, not a rename."""
    write(installed, "scripts/c.py", "".join(f"other_{n} = 'x{n}'\n" for n in range(9)))
    git(installed, "rm", "-q", "scripts/b.py")
    write(installed, BURNDOWN, _burndown("scripts/c.py"))
    stage(installed)
    assert _locations(installed) == [("baseline-growth", BURNDOWN)]


def test_planted_second_install_at_another_path_is_a_new_exception_file(
    installed: Path,
) -> None:
    """A second burn-down-style file does not escape the exception-file rule."""
    write(installed, "scripts/c.py", CODE)
    write(
        installed,
        ".onex_ratchets/second_burndown_baseline.txt",
        _burndown("scripts/c.py"),
    )
    stage(installed)
    assert ("new-exception-file", ".onex_ratchets/second_burndown_baseline.txt") in (
        _locations(installed)
    )


def test_planted_entry_without_a_ticket_after_install_is_refused(
    installed: Path,
) -> None:
    write(
        installed, BURNDOWN, _burndown("scripts/b.py", header="# burn-down baseline\n")
    )
    stage(installed)
    assert _locations(installed) == [("burndown-ticket-missing", BURNDOWN)]


# --- new-exception-file still refuses every other new baseline file -------------


def test_every_other_new_baseline_file_is_still_a_new_exception_file(
    repo: Path,
) -> None:
    write(repo, BURNDOWN, _burndown("scripts/b.py"))
    write(repo, "config/other_baseline.txt", "a\n")
    write(repo, ".onex_ratchets/other_burndown_baseline.txt", _burndown())
    stage(repo)
    assert _locations(repo) == [
        ("new-exception-file", ".onex_ratchets/other_burndown_baseline.txt"),
        ("new-exception-file", "config/other_baseline.txt"),
    ]


def test_the_burndown_path_itself_is_not_a_new_exception_file(repo: Path) -> None:
    write(repo, BURNDOWN, _burndown("scripts/b.py"))
    stage(repo)
    assert "new-exception-file" not in rules_hit(repo)


# --- the runtime writes and prunes the file -------------------------------------


def _run(repo: Path, *argv: str) -> int:
    return main(["--repo-root", str(repo), *argv], env=scrub_git_location_env())


def test_write_burndown_baseline_lists_the_refused_paths_the_baseline_lacks(
    repo: Path,
) -> None:
    assert _run(repo, "--write-burndown-baseline", TICKET) == 0
    text = (repo / BURNDOWN).read_text()
    assert text == _burndown("scripts/b.py")
    stage(repo)
    assert rules_hit(repo) == []
    assert _run(repo) == 0


def test_write_burndown_baseline_is_refused_when_the_file_exists(repo: Path) -> None:
    write(repo, BURNDOWN, _burndown("scripts/b.py"))
    assert _run(repo, "--write-burndown-baseline", TICKET) == 1
    assert (repo / BURNDOWN).read_text() == _burndown("scripts/b.py")


def test_write_burndown_baseline_is_refused_for_a_word_that_is_not_a_ticket(
    repo: Path,
) -> None:
    assert _run(repo, "--write-burndown-baseline", "soon") == 1
    assert not (repo / BURNDOWN).exists()


def test_prune_baseline_prunes_the_burndown_file_and_keeps_its_header(
    installed: Path,
) -> None:
    git(installed, "rm", "-q", "scripts/b.py")
    assert _run(installed, "--prune-baseline") == 0
    assert (installed / BURNDOWN).read_text() == _burndown()
    stage(installed)
    assert rules_hit(installed) == []
