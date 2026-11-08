# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""OMN-22478: the writer-app verdict for the sibling pin train's hook rev bump.

The gate admits a diff of dependency pins plus ``rev:`` swaps in
``.pre-commit-config.yaml`` through the pinned verifier's
``classify_precommit_hook_rev_pin_train_only`` and nothing else. The verifier's
own rules are tested in omnimarket; these tests run the real gate step against
real git objects with a stub verifier, and pin the wiring: the exemption names
its classifier, any other edit to the config is still refused, and a verifier
that lacks the function fails closed.
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from tests.ci.test_receipt_gate_writer_pin_only_in_job_omn17427 import (
    _assert_output,
    _run,
)
from tests.ci.test_receipt_gate_writer_pin_swap_omn20068 import PROBE as BASE_PROBE
from tests.ci.test_receipt_gate_writer_workflow_pin_omn20074 import _prepare

pytestmark = pytest.mark.unit

CONFIG = ".pre-commit-config.yaml"
OLD = "dev-20261106041752-8377609527be"
NEW = "dev-20261107224734-3e0da50b8d15"
PROJECT = '[project]\nname = "x"\nversion = "0.1.0"\n'

# A stub of the verifier's hook rev classifier: admits a change of lines of the
# shape "    rev: dev-..." only. Its real rules live in omnimarket.
PROBE = BASE_PROBE + dedent("""\

    def classify_precommit_hook_rev_pin_train_only(
        paths, *, pyproject_head, pyproject_base, precommit_head, precommit_base,
    ):
        others = [p for p in paths if p != ".pre-commit-config.yaml"]
        if others:
            ok, reason = classify_dependency_pin_only(
                others, pyproject_head=pyproject_head, pyproject_base=pyproject_base,
            )
            if not ok:
                return False, f"beyond the hook revs: {reason}"
        if precommit_head is None or precommit_base is None:
            return False, "config unreadable"
        head, base = precommit_head.splitlines(), precommit_base.splitlines()
        if len(head) != len(base):
            return False, "a line is added or removed"
        for new, old in zip(head, base):
            if new != old and not (new.startswith("    rev: dev-") and old.startswith("    rev: dev-")):
                return False, "a line beyond a hook rev changed"
        return True, "dependency pins and first-party hook revs only"
    """)


def _config(rev: str, args: str = "[--repo, x]") -> str:
    return (
        "repos:\n"
        "  - repo: https://github.com/OmniNode-ai/omnibase_core\n"
        f"    rev: {rev}\n"
        "    hooks:\n"
        "      - id: check-no-utcnow\n"
        f"        args: {args}\n"
    )


BASE_FILES = {
    "pyproject.toml": PROJECT,
    "uv.lock": "version = 1\n",
    CONFIG: _config(OLD),
}
TRAIN = {
    "pyproject.toml": PROJECT.replace("0.1.0", "0.1.1"),
    "uv.lock": "version = 2\n",
    CONFIG: _config(NEW),
}


def test_train_pins_and_hook_rev_swap_is_exempt(tmp_path: Path) -> None:
    env, _ = _prepare(tmp_path, TRAIN, base_changes=BASE_FILES, probe=PROBE)
    result = _run(env)
    _assert_output(env, exempt=True)
    assert "dependency-pin-only change" in result.stdout
    assert "classify_precommit_hook_rev_pin_train_only" in result.stdout
    assert env["HEAD_SHA"] in result.stdout


def test_hook_rev_swap_alone_is_exempt(tmp_path: Path) -> None:
    env, _ = _prepare(
        tmp_path, {CONFIG: _config(NEW)}, base_changes=BASE_FILES, probe=PROBE
    )
    _run(env)
    _assert_output(env, exempt=True)


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        pytest.param(
            {CONFIG: _config(NEW, args="[--repo, y]")},
            "a line beyond a hook rev changed",
            id="args-edited",
        ),
        pytest.param(
            {CONFIG: _config(NEW) + "      - id: another-hook\n"},
            "a line is added or removed",
            id="hook-added",
        ),
        pytest.param(
            {CONFIG: _config("v0.47.47")},
            "a line beyond a hook rev changed",
            id="rev-not-a-dev-tag",
        ),
        pytest.param({"src/x.py": "x = 1\n"}, "beyond the hook revs", id="source-file"),
        pytest.param(
            {".github/workflows/ci.yml": "jobs: {}\n"},
            "beyond the hook revs",
            id="workflow-file",
        ),
        pytest.param({CONFIG: None}, "hook rev pin train", id="config-deleted"),
    ],
)
def test_control_any_other_edit_stays_refused(
    tmp_path: Path, changes: dict[str, str | None], reason: str
) -> None:
    env, _ = _prepare(
        tmp_path, {**TRAIN, **changes}, base_changes=BASE_FILES, probe=PROBE
    )
    result = _run(env)
    _assert_output(env, exempt=False)
    assert "OCC writer app is not exempt:" in result.stdout
    assert reason in result.stdout


def test_control_a_verifier_without_the_function_fails_closed(tmp_path: Path) -> None:
    env, _ = _prepare(tmp_path, TRAIN, base_changes=BASE_FILES, probe=BASE_PROBE)
    result = _run(env)
    _assert_output(env, exempt=False)
    assert (
        "the pinned verifier has no classify_precommit_hook_rev_pin_train_only"
        in result.stdout
    )


def test_control_the_config_without_the_train_change_is_not_judged_here(
    tmp_path: Path,
) -> None:
    env, _ = _prepare(
        tmp_path,
        {
            "pyproject.toml": PROJECT.replace("0.1.0", "0.1.1"),
            "uv.lock": "version = 2\n",
        },
        base_changes=BASE_FILES,
        probe=PROBE,
    )
    _run(env)
    _assert_output(env, exempt=True)
