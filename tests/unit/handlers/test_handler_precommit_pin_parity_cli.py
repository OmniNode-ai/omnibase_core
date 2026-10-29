# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the check-precommit-pin-parity CLI (OMN-21495, plan task T0.2).

The CLI reads the config, resolves each rev's commit time (from a history
repository, else from the pre-commit cache), runs the pure handler and exits 0
on PASS and 1 on FAIL or ERROR. Revs are real commits in a temporary
repository, so the ordering comes from git and not from a fixture.
"""

from __future__ import annotations

import json
import sqlite3
import subprocess
from pathlib import Path

import pytest
import yaml

from omnibase_core.handlers.handler_precommit_pin_parity_cli import (
    DEFAULT_CONFIG,
    DEFAULT_RULES,
    main,
)
from omnibase_core.models.precommit_pins import ModelPrecommitPinRules
from omnibase_core.validators.no_unguarded_git_subprocess import (
    scrub_git_location_env,
)

pytestmark = pytest.mark.unit

_ORG = "OmniNode-ai"
_CORE = f"https://github.com/{_ORG}/omnibase_core"


def _git(repo: Path, *args: str, when: str | None = None) -> str:
    identity = {
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@example.invalid",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@example.invalid",
    }
    if when is not None:
        identity |= {"GIT_AUTHOR_DATE": when, "GIT_COMMITTER_DATE": when}
    done = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
        env={**scrub_git_location_env(), **identity},
    )
    return done.stdout.strip()


def _history(path: Path) -> tuple[Path, str, str]:
    """A repository with an older and a newer commit; returns (repo, old, new)."""
    path.mkdir()
    _git(path, "init", "-q")
    shas: list[str] = []
    for n, when in enumerate(("2026-01-01T00:00:00Z", "2026-02-01T00:00:00Z")):
        (path / "f.txt").write_text(str(n), encoding="utf-8")
        _git(path, "add", "f.txt")
        _git(path, "commit", "-q", "-m", f"c{n}", when=when)
        shas.append(_git(path, "rev-parse", "HEAD"))
    return path, shas[0], shas[1]


def _config(root: Path, *revs: str) -> None:
    repos = [
        {"repo": _CORE, "rev": rev, "hooks": [{"id": f"hook-{n}"}]}
        for n, rev in enumerate(revs)
    ]
    (root / DEFAULT_CONFIG).write_text(
        yaml.safe_dump({"repos": repos}), encoding="utf-8"
    )


def _rules(root: Path) -> list[str]:
    path = root / "rules.yaml"
    path.write_text(yaml.safe_dump({"hook_repos": [_CORE]}), encoding="utf-8")
    return ["--rules", str(path)]


def test_packaged_rules_name_the_shared_core_hook_repo() -> None:
    rules = ModelPrecommitPinRules.model_validate(
        yaml.safe_load(DEFAULT_RULES.read_text(encoding="utf-8"))
    )
    assert _CORE in rules.hook_repos


def test_lowered_pin_exits_one_and_names_the_rev(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    history, old, new = _history(tmp_path / "hist")
    root = tmp_path / "consumer"
    root.mkdir()
    _config(root, old, new)
    code = main(["--root", str(root), "--history-repo", str(history), *_rules(root)])
    assert code == 1
    assert old in capsys.readouterr().out


def test_converged_pins_exit_zero(tmp_path: Path) -> None:
    history, _old, new = _history(tmp_path / "hist")
    root = tmp_path / "consumer"
    root.mkdir()
    _config(root, new, new)
    argv = ["--root", str(root), "--history-repo", str(history), *_rules(root)]
    assert main(argv) == 0


def test_a_rev_the_history_does_not_hold_exits_one(tmp_path: Path) -> None:
    history, _old, new = _history(tmp_path / "hist")
    root = tmp_path / "consumer"
    root.mkdir()
    _config(root, "f" * 40, new)
    argv = ["--root", str(root), "--history-repo", str(history), *_rules(root)]
    assert main(argv) == 1


def test_a_missing_config_exits_one_and_is_never_a_pass(tmp_path: Path) -> None:
    root = tmp_path / "consumer"
    root.mkdir()
    assert main(["--root", str(root), *_rules(root)]) == 1


def test_a_config_that_does_not_parse_exits_one(tmp_path: Path) -> None:
    root = tmp_path / "consumer"
    root.mkdir()
    (root / DEFAULT_CONFIG).write_text("repos: [\n", encoding="utf-8")
    assert main(["--root", str(root), *_rules(root)]) == 1


def test_the_report_json_is_written(tmp_path: Path) -> None:
    history, old, new = _history(tmp_path / "hist")
    root = tmp_path / "consumer"
    root.mkdir()
    _config(root, old, new)
    out = tmp_path / "report.json"
    main(
        [
            "--root",
            str(root),
            "--history-repo",
            str(history),
            "--report-json",
            str(out),
            *_rules(root),
        ]
    )
    assert json.loads(out.read_text(encoding="utf-8"))["overall_status"] == "FAIL"


def test_without_a_history_repo_the_pre_commit_cache_supplies_the_times(
    tmp_path: Path,
) -> None:
    history, old, new = _history(tmp_path / "hist")
    cache = tmp_path / "cache"
    cache.mkdir()
    db = sqlite3.connect(cache / "db.db")
    db.execute("CREATE TABLE repos (repo TEXT, ref TEXT, path TEXT)")
    for rev in (old, new):
        clone = cache / f"repo-{rev[:8]}"
        _git(tmp_path, "clone", "-q", str(history), str(clone))
        _git(clone, "checkout", "-q", rev)
        db.execute("INSERT INTO repos VALUES (?, ?, ?)", (_CORE, rev, str(clone)))
    db.commit()
    db.close()
    cached = ["--pre-commit-home", str(cache), *_rules(tmp_path)]
    root = tmp_path / "consumer"
    root.mkdir()
    _config(root, old, new)
    assert main(["--root", str(root), *cached]) == 1
    _config(root, new, new)
    assert main(["--root", str(root), *cached]) == 0
