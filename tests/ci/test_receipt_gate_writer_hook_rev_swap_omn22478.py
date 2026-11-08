# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""OMN-22478: a writer-app pin bump may move first-party hook revs in .pre-commit-config.yaml.

The nightly sibling-pin train moves the omnibase_core source pin and, in the same
change, the core hook blocks of ``.pre-commit-config.yaml`` (omniclaude#3207): the
hooks must sit strictly newer than the pin. That change touches a file the
pin-swap classifier refused, so the train pull request fell through to the
evidence gate (merge_base: no test-side change) and never merged. Its pin then
trailed the newest dev tag past the stale_pin bound and every omniclaude pull
request went red on Tests Gate (omniclaude#3211, job 128556803898).

The exemption is derived, never asserted: every changed line of the hook config
must swap the dev merge tag of a ``rev:`` line whose owning ``repo:`` is a
first-party repository. Nothing else may change in the file.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.ci.test_receipt_gate_writer_pin_only_in_job_omn17427 import (
    _assert_output,
    _run,
)
from tests.ci.test_receipt_gate_writer_pin_swap_omn20068 import PROJECT, _prepare

pytestmark = pytest.mark.unit

HOOKS = ".pre-commit-config.yaml"
OLD_TAG = "dev-20261106041752-8377609527be"
NEW_TAG = "dev-20261107224734-3e0da50b8d15"
OTHER_TAG = "dev-20261101103701-2fc5e461fca7"
CORE = "https://github.com/OmniNode-ai/omnibase_core"
THIRD_PARTY = "https://github.com/astral-sh/ruff-pre-commit"


def _config(
    first: str = OLD_TAG, second: str = OTHER_TAG, repo: str = CORE, extra: str = ""
) -> str:
    return (
        "repos:\n"
        f"  - repo: {repo}\n"
        f"    rev: {first}\n"
        "    hooks:\n"
        "      - id: check-no-utcnow\n"
        f"  - repo: {CORE}\n"
        f"    rev: {second}\n"
        "    hooks:\n"
        "      - id: check-node-home\n"
        f"{extra}"
    )


BASE = {"pyproject.toml": PROJECT, "uv.lock": "version = 1\n", HOOKS: _config()}
HEAD = {
    "pyproject.toml": PROJECT.replace("0.1.0", "0.1.1"),
    "uv.lock": "version = 2\n",
    HOOKS: _config(first=NEW_TAG),
}


def test_train_shape_hook_rev_swap_is_exempt(tmp_path: Path) -> None:
    env = _prepare(tmp_path, HEAD, base_changes=BASE)
    result = _run(env)
    _assert_output(env, exempt=True)
    assert "pin-swap-only change" in result.stdout
    assert "1 hook rev(s) in 1 file(s)" in result.stdout


def test_two_blocks_moving_to_one_tag_are_exempt(tmp_path: Path) -> None:
    changes = {**HEAD, HOOKS: _config(first=NEW_TAG, second=NEW_TAG)}
    env = _prepare(tmp_path, changes, base_changes=BASE)
    result = _run(env)
    _assert_output(env, exempt=True)
    assert "2 hook rev(s) in 1 file(s)" in result.stdout


@pytest.mark.parametrize(
    ("config", "reason"),
    [
        pytest.param(
            _config(first=NEW_TAG, extra="  - repo: https://x.y/z\n"),
            f"{HOOKS} adds or removes a line",
            id="added-line",
        ),
        pytest.param(
            _config(first="main"),
            f"{HOOKS} line 3 is not solely a first-party hook rev swap",
            id="rev-to-branch",
        ),
        pytest.param(
            _config(first="dev-20261107224734-3E0DA50B8D15"),
            f"{HOOKS} line 3 is not solely a first-party hook rev swap",
            id="uppercase-tag",
        ),
        pytest.param(
            _config(first=NEW_TAG).replace("check-no-utcnow", "check-other"),
            f"{HOOKS} line 5 is not solely a first-party hook rev swap",
            id="changed-hook-id",
        ),
        pytest.param(
            _config(first=NEW_TAG).replace(f"repo: {CORE}", f"repo: {THIRD_PARTY}", 1),
            f"{HOOKS} line 2 is not solely a first-party hook rev swap",
            id="repo-line-changed",
        ),
        pytest.param(
            _config(first=NEW_TAG).replace("    rev:", "    rev :", 1),
            f"{HOOKS} line 3 is not solely a first-party hook rev swap",
            id="changed-key-spelling",
        ),
    ],
)
def test_hook_config_change_beyond_a_rev_swap_fails_closed(
    tmp_path: Path, config: str, reason: str
) -> None:
    env = _prepare(tmp_path, {**HEAD, HOOKS: config}, base_changes=BASE)
    result = _run(env)
    _assert_output(env, exempt=False)
    assert "OCC writer app is not exempt:" in result.stdout
    assert reason in result.stdout


def test_third_party_hook_rev_swap_fails_closed(tmp_path: Path) -> None:
    base = {**BASE, HOOKS: _config(repo=THIRD_PARTY)}
    head = {**HEAD, HOOKS: _config(first=NEW_TAG, repo=THIRD_PARTY)}
    env = _prepare(tmp_path, head, base_changes=base)
    result = _run(env)
    _assert_output(env, exempt=False)
    assert f"{HOOKS} line 3 is not solely a first-party hook rev swap" in result.stdout


def test_hook_rev_swap_without_a_dependency_move_fails_closed(
    tmp_path: Path,
) -> None:
    # The train moves hooks with the pin; a hook-only change is not that change.
    env = _prepare(tmp_path, {HOOKS: HEAD[HOOKS]}, base_changes=BASE)
    result = _run(env)
    _assert_output(env, exempt=False)
    assert "a hook rev swap requires a changed dependency manifest" in result.stdout
