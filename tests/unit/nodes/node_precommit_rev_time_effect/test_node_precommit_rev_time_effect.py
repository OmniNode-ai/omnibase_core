# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Real git and SQLite coverage for the contracted rev-time effect."""

from __future__ import annotations

import sqlite3
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from omnibase_core.models.precommit_pins.model_precommit_pin import ModelPrecommitPin
from omnibase_core.models.precommit_pins.model_precommit_rev_time_parameters import (
    ModelPrecommitRevTimeParameters,
)
from omnibase_core.models.precommit_pins.model_precommit_rev_time_request import (
    ModelPrecommitRevTimeRequest,
)
from omnibase_core.nodes.node_precommit_rev_time_effect.handler import (
    NodePrecommitRevTimeEffect,
)
from omnibase_core.nodes.node_precommit_rev_time_effect.runtime_precommit_pin_parity import (
    build_container,
)
from omnibase_core.validation.validator_precommit_pin_parity import (
    ValidatorPrecommitPinParity,
)
from omnibase_core.validators.no_unguarded_git_subprocess import scrub_git_location_env

pytestmark = pytest.mark.unit
CORE = "https://github.com/OmniNode-ai/omnibase_core"


def git(repo: Path, *args: str, when: str | None = None) -> str:
    env = {
        **scrub_git_location_env(),
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@example.invalid",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@example.invalid",
    }
    if when:
        env.update(GIT_AUTHOR_DATE=when, GIT_COMMITTER_DATE=when)
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
        env=scrub_git_location_env(env),
    ).stdout.strip()


@pytest.fixture
def history(tmp_path):
    repo = tmp_path / "history"
    repo.mkdir()
    git(repo, "init", "-q")
    revs = []
    for n, when in enumerate(("2026-01-01T00:00:00Z", "2026-02-01T00:00:00Z")):
        (repo / "f").write_text(str(n))
        git(repo, "add", "f")
        git(repo, "commit", "-q", "-m", str(n), when=when)
        revs.append(git(repo, "rev-parse", "HEAD"))
    return repo, revs


def parameters(**updates):
    params = ValidatorPrecommitPinParity(build_container()).rules.lookup
    return ModelPrecommitRevTimeParameters.model_validate(
        {**params.model_dump(), **updates}
    )


def pins(revs):
    return tuple(
        ModelPrecommitPin(repo=CORE, rev=r, line=1, hook_ids=("x",)) for r in revs
    )


def test_history_real_git_and_unresolved(history):
    repo, revs = history
    result = NodePrecommitRevTimeEffect().handle(
        ModelPrecommitRevTimeRequest(
            pins=pins([*revs, "absent"]), parameters=parameters(history_repo=str(repo))
        )
    )
    assert [r.rev for r in result.rev_times] == sorted(revs)
    stamps = {r.rev: r.committed_at for r in result.rev_times}
    assert stamps[revs[0]] < stamps[revs[1]]


def test_real_readonly_cache(history, tmp_path, monkeypatch):
    repo, revs = history
    cache = tmp_path / "cache"
    cache.mkdir()
    with sqlite3.connect(cache / "db.db") as db:
        db.execute("CREATE TABLE repos(repo TEXT, ref TEXT, path TEXT)")
        for rev in revs:
            clone = cache / rev
            git(tmp_path, "clone", "-q", str(repo), str(clone))
            git(clone, "checkout", "-q", rev)
            db.execute("INSERT INTO repos VALUES (?, ?, ?)", (CORE, rev, str(clone)))
    before = (cache / "db.db").read_bytes()
    # A hostile parent git location must not redirect git show to another repo.
    monkeypatch.setenv("GIT_DIR", str(tmp_path / "wrong"))
    result = NodePrecommitRevTimeEffect().handle(
        ModelPrecommitRevTimeRequest(
            pins=pins(revs), parameters=parameters(), cache_home=str(cache)
        )
    )
    assert len(result.rev_times) == 2
    assert (cache / "db.db").read_bytes() == before
    stamps = {r.rev: r.committed_at for r in result.rev_times}
    assert stamps[revs[0]] < stamps[revs[1]]


def test_missing_cache_is_not_created(tmp_path):
    home = tmp_path / "absent"
    assert (
        not NodePrecommitRevTimeEffect()
        .handle(
            ModelPrecommitRevTimeRequest(
                pins=pins(["old"]), parameters=parameters(), cache_home=str(home)
            )
        )
        .rev_times
    )
    assert not home.exists()


def test_timeout_is_contract_owned(tmp_path):
    node = NodePrecommitRevTimeEffect()
    with patch(
        "subprocess.run", side_effect=subprocess.TimeoutExpired("git", 0.125)
    ) as call:
        result = node.handle(
            ModelPrecommitRevTimeRequest(
                pins=pins(["old"]),
                parameters=parameters(
                    history_repo=str(tmp_path), git_timeout_seconds=0.125
                ),
            )
        )
    assert call.call_args.kwargs["timeout"] == 0.125
    assert result.rev_times == ()
