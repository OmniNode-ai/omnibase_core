# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the executed-parity engine (OMN-15340).

The engine's whole value is that it DISTINGUISHES exit reasons. "The test exited
non-zero on the base tree" is not the claim — "the test executed on the base tree and
failed on its own assertion" is. These tests pin the classification matrix by really
running pytest, and pin the non-vacuity probe that stops a base-tree run from silently
grading HEAD source.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from scripts.ci.parity_replay import (
    EnumParityOutcome,
    _probe_source_residency,
    _run_env,
    red_on_base,
    resolve_interpreter,
    run_test_id,
)

pytestmark = pytest.mark.unit

TEST_MODULE = """
import pytest


def test_assertion_fails():
    assert 1 == 2, "discriminating claim"


def test_passes():
    assert True


def test_explicit_fail():
    pytest.fail("explicit")


def test_non_assertion_exception():
    None.handle(1)


@pytest.mark.skip(reason="not here")
def test_skipped():
    assert False
"""

BROKEN_MODULE = """
import a_module_that_does_not_exist_anywhere  # noqa: F401


def test_never_runs():
    assert True
"""


@pytest.fixture
def sandbox(tmp_path: Path) -> Path:
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_kinds.py").write_text(TEST_MODULE, encoding="utf-8")
    (tmp_path / "tests" / "test_broken.py").write_text(BROKEN_MODULE, encoding="utf-8")
    return tmp_path


@pytest.mark.parametrize(
    ("test_id", "expected"),
    [
        ("tests/test_kinds.py::test_assertion_fails", EnumParityOutcome.RED_ASSERTION),
        ("tests/test_kinds.py::test_explicit_fail", EnumParityOutcome.RED_ASSERTION),
        ("tests/test_kinds.py::test_passes", EnumParityOutcome.PASSED),
        (
            "tests/test_kinds.py::test_non_assertion_exception",
            EnumParityOutcome.RED_EXCEPTION,
        ),
        ("tests/test_kinds.py::test_skipped", EnumParityOutcome.SKIPPED),
        ("tests/test_broken.py::test_never_runs", EnumParityOutcome.COLLECTION_ERROR),
        ("tests/test_kinds.py::test_absent", EnumParityOutcome.NOT_COLLECTED),
    ],
)
def test_exit_reasons_are_distinguished(
    sandbox: Path, test_id: str, expected: EnumParityOutcome
) -> None:
    """Only RED_ASSERTION counts as RED; the other four non-pass reasons are distinct.

    An ImportError at collection and a missing test id both exit non-zero, and both
    prove exactly nothing about the pre-change tree — collapsing them into "non-zero"
    is the failure mode this engine exists to prevent.
    """
    result = run_test_id(
        test_id,
        interpreter=resolve_interpreter(sandbox),
        cwd=sandbox,
        env=_run_env(sandbox),
    )
    assert result.outcome is expected, result.detail


def test_residency_probe_accepts_module_inside_the_expected_root(
    tmp_path: Path,
) -> None:
    src = tmp_path / "src"
    (src / "probepkg").mkdir(parents=True)
    (src / "probepkg" / "__init__.py").write_text("", encoding="utf-8")
    (src / "probepkg" / "mod.py").write_text("X = 1\n", encoding="utf-8")

    ok, detail = _probe_source_residency(
        "probepkg.mod",
        interpreter=resolve_interpreter(tmp_path),
        cwd=tmp_path,
        env=_run_env(src),
        expected_root=tmp_path,
    )
    assert ok is True, detail


def test_residency_probe_rejects_module_resolved_outside_the_base_tree(
    tmp_path: Path,
) -> None:
    """The vacuity guard: an editable install resolving to HEAD must FAIL the run.

    Without this the base-tree execution grades HEAD source, so both the RED and the
    GREEN it reports are meaningless.
    """
    elsewhere = tmp_path / "elsewhere"
    (elsewhere / "probepkg").mkdir(parents=True)
    (elsewhere / "probepkg" / "__init__.py").write_text("", encoding="utf-8")
    (elsewhere / "probepkg" / "mod.py").write_text("X = 1\n", encoding="utf-8")
    base_tree = tmp_path / "base"
    base_tree.mkdir()

    ok, detail = _probe_source_residency(
        "probepkg.mod",
        interpreter=resolve_interpreter(tmp_path),
        cwd=base_tree,
        env=_run_env(elsewhere),
        expected_root=base_tree,
    )
    assert ok is False
    assert "VACUOUS BASE RUN" in detail


def test_residency_probe_fails_closed_when_module_absent(tmp_path: Path) -> None:
    ok, detail = _probe_source_residency(
        "no_such_module_at_all",
        interpreter=resolve_interpreter(tmp_path),
        cwd=tmp_path,
        env=_run_env(tmp_path),
        expected_root=tmp_path,
    )
    assert ok is False
    assert "does not resolve" in detail


def test_red_on_base_fails_closed_on_unresolvable_base_ref(tmp_path: Path) -> None:
    ok, detail = red_on_base(
        "pkg.nodes.node_x",
        ("tests/test_x.py::test_y",),
        "0" * 40,
        "pkg.handler",
        tmp_path,
        tmp_path / "src",
    )
    assert ok is False
    assert "unresolvable" in detail


def test_red_on_base_fails_closed_without_test_ids(tmp_path: Path) -> None:
    ok, detail = red_on_base(
        "pkg.nodes.node_x", (), "HEAD", "pkg.handler", tmp_path, tmp_path / "src"
    )
    assert ok is False
    assert "no test_ids" in detail


def test_run_env_strips_inherited_pytest_and_git_overrides(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Inherited PYTEST_ADDOPTS / GIT_DIR would silently retarget the inner run."""
    monkeypatch.setenv("PYTEST_ADDOPTS", "-x --reruns 5")
    monkeypatch.setenv("GIT_DIR", "/somewhere/else/.git")
    monkeypatch.setenv("PYTHONPATH", "/leftover")

    env = _run_env(tmp_path / "src")

    assert "PYTEST_ADDOPTS" not in env
    assert "GIT_DIR" not in env
    assert env["PYTHONPATH"] == str(tmp_path / "src")
    assert os.environ["PYTEST_ADDOPTS"] == "-x --reruns 5"  # caller env untouched
