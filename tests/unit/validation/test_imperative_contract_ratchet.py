# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Shrink-only ratchet of a repository's imperative-contract allowlist (OMN-20918).

Each consumer carries its own allowlist, so no repository can widen another's. Against
the merge base an allowlist may lose a path and may not gain one. The handler is
exercised on allowlist texts, and the CLI on a real git history: a base commit holding
the allowlist, then a head that gains, loses or keeps a path.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.handlers.handler_imperative_allowlist_ratchet import (
    HandlerImperativeAllowlistRatchet,
    allowlisted_paths,
)
from omnibase_core.handlers.handler_imperative_contract_guard_cli import main
from omnibase_core.models.nodes.imperative_contract_guard.model_allowlist_ratchet_input import (
    ModelAllowlistRatchetInput,
)
from omnibase_core.validators.no_unguarded_git_subprocess import (
    scrub_git_location_env,
)

pytestmark = pytest.mark.unit

ALLOWLIST_NAME = "imperative-contract-allowlist.yaml"


def _allowlist(*paths: str) -> str:
    entries = "".join(
        f"  - path: {p}\n    violations:\n      - raw_http_inference\n"
        "    ticket: OMN-1\n"
        for p in paths
    )
    return (
        "allowlisted_handlers:\n" + entries if paths else "allowlisted_handlers: []\n"
    )


def _ratchet(base: str | None, head: str | None):
    return HandlerImperativeAllowlistRatchet().handle(
        ModelAllowlistRatchetInput(base_text=base, head_text=head)
    )


def test_imperative_contract_ratchet_refuses_an_allowlist_that_gains_an_entry() -> None:
    report = _ratchet(
        _allowlist("src/pkg/a.py"), _allowlist("src/pkg/a.py", "src/pkg/b.py")
    )
    assert report.added == ["src/pkg/b.py"]
    assert not report.admitted


def test_imperative_contract_ratchet_admits_an_allowlist_that_loses_an_entry() -> None:
    report = _ratchet(
        _allowlist("src/pkg/a.py", "src/pkg/b.py"), _allowlist("src/pkg/a.py")
    )
    assert report.added == []
    assert report.removed == ["src/pkg/b.py"]
    assert report.admitted


def test_imperative_contract_ratchet_admits_an_unchanged_allowlist() -> None:
    text = _allowlist("src/pkg/a.py")
    report = _ratchet(text, text)
    assert report.added == [] and report.removed == [] and report.admitted


def test_imperative_contract_ratchet_refuses_a_swap_of_one_entry_for_another() -> None:
    report = _ratchet(_allowlist("src/pkg/a.py"), _allowlist("src/pkg/b.py"))
    assert report.added == ["src/pkg/b.py"]
    assert report.removed == ["src/pkg/a.py"]
    assert not report.admitted


def test_imperative_contract_ratchet_ignores_a_violation_list_change_on_a_kept_path() -> (
    None
):
    base = _allowlist("src/pkg/a.py")
    head = base.replace("raw_http_inference", "direct_db")
    assert _ratchet(base, head).admitted


def test_imperative_contract_ratchet_admits_the_first_landing_as_a_bootstrap() -> None:
    report = _ratchet(None, _allowlist("src/pkg/a.py"))
    assert report.bootstrap and report.admitted


def test_imperative_contract_ratchet_refuses_an_entry_it_cannot_read() -> None:
    with pytest.raises(ModelOnexError, match="not a mapping"):
        allowlisted_paths("allowlisted_handlers:\n  - src/pkg/a.py\n")


def test_imperative_contract_ratchet_reads_nothing_from_an_empty_file() -> None:
    assert allowlisted_paths(None) == []
    assert allowlisted_paths("") == []


# --- The CLI on a git history ---


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
        env=scrub_git_location_env(),
    ).stdout


def _repo(tmp_path: Path, base_allowlist: str | None) -> Path:
    repo = tmp_path / "pkg"
    (repo / "src" / "pkg").mkdir(parents=True)
    (repo / "src" / "pkg" / "__init__.py").write_text("")
    (repo / "pyproject.toml").write_text('[project]\nname = "pkg"\n')
    if base_allowlist is not None:
        (repo / ALLOWLIST_NAME).write_text(base_allowlist)
    _git(repo, "init", "-q", "-b", "dev")
    _git(repo, "config", "user.email", "t@example.invalid")
    _git(repo, "config", "user.name", "t")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "base")
    _git(repo, "checkout", "-q", "-b", "change")
    return repo


def _cli(repo: Path, capsys: pytest.CaptureFixture[str]) -> tuple[int, str]:
    capsys.readouterr()
    code = main(
        [
            "--repo-root",
            str(repo),
            "--allowlist-path",
            ALLOWLIST_NAME,
            "--ratchet-base-ref",
            "dev",
        ]
    )
    return code, capsys.readouterr().out


def test_imperative_contract_ratchet_cli_refuses_a_gained_entry(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = _repo(tmp_path, _allowlist("src/pkg/a.py"))
    (repo / ALLOWLIST_NAME).write_text(_allowlist("src/pkg/a.py", "src/pkg/b.py"))
    _git(repo, "commit", "-q", "-am", "widen")
    code, out = _cli(repo, capsys)
    assert code == 1
    assert "REFUSED" in out
    assert "+ src/pkg/b.py" in out


def test_imperative_contract_ratchet_cli_admits_a_lost_entry(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = _repo(tmp_path, _allowlist("src/pkg/a.py", "src/pkg/b.py"))
    (repo / ALLOWLIST_NAME).write_text(_allowlist("src/pkg/a.py"))
    _git(repo, "commit", "-q", "-am", "shrink")
    code, out = _cli(repo, capsys)
    assert code == 0
    assert "gains no path" in out
    assert "1 removed" in out


def test_imperative_contract_ratchet_cli_judges_the_working_tree_allowlist(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = _repo(tmp_path, _allowlist("src/pkg/a.py"))
    (repo / ALLOWLIST_NAME).write_text(_allowlist("src/pkg/a.py", "src/pkg/c.py"))
    code, _ = _cli(repo, capsys)
    assert code == 1


def test_imperative_contract_ratchet_cli_compares_against_the_merge_base(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A path the base branch gained after the fork is not a gain of this change."""
    repo = _repo(tmp_path, _allowlist("src/pkg/a.py"))
    _git(repo, "checkout", "-q", "dev")
    (repo / ALLOWLIST_NAME).write_text(_allowlist("src/pkg/a.py", "src/pkg/z.py"))
    _git(repo, "commit", "-q", "-am", "dev widens")
    _git(repo, "checkout", "-q", "change")
    (repo / "src" / "pkg" / "other.py").write_text("X = 1\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "unrelated")
    code, out = _cli(repo, capsys)
    assert code == 0, out


def test_imperative_contract_ratchet_cli_admits_the_first_landing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = _repo(tmp_path, None)
    (repo / ALLOWLIST_NAME).write_text(_allowlist("src/pkg/a.py"))
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "bootstrap")
    code, out = _cli(repo, capsys)
    assert code == 0
    assert "absent at the merge base" in out


def test_imperative_contract_ratchet_cli_fails_on_an_unknown_base_ref(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path, _allowlist("src/pkg/a.py"))
    with pytest.raises(ModelOnexError, match="no merge base"):
        main(
            [
                "--repo-root",
                str(repo),
                "--allowlist-path",
                ALLOWLIST_NAME,
                "--ratchet-base-ref",
                "no-such-ref",
            ]
        )


def test_imperative_contract_ratchet_cli_fails_the_run_even_with_no_findings(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A repository with no violation at all still cannot widen its allowlist."""
    repo = _repo(tmp_path, _allowlist())
    (repo / ALLOWLIST_NAME).write_text(_allowlist("src/pkg/new.py"))
    code, out = _cli(repo, capsys)
    assert code == 1
    assert "REFUSED" in out
