# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OMN-19513: ``onex-work-ledger render --repair`` refuses ledger writes under a test runner.

Operator ruling 2026-10-01: "it should be impossible to like fake test like that". Each test
makes a directory stand in for the canonical ledger's place by moving the temporary directory
(``TMPDIR`` for a subprocess, ``tempfile.tempdir`` in process) to a sibling scratch directory, so
no test touches a real ledger file.
"""

from __future__ import annotations

import hashlib
import subprocess
import tempfile
from pathlib import Path

import pytest

from omnibase_core.cli import cli_work_ledger_render
from omnibase_core.handlers import handler_ledger_write_guard as guard
from omnibase_core.models.bootstrap.model_environment_bootstrap import (
    ModelEnvironmentBootstrap,
)
from tests.unit.models.events.work.test_work_ledger_render import (
    EVENTS_ENV,
    MD_ENV,
    SCRIPT,
    _all_events,
    _write_pair,
)

pytestmark = pytest.mark.unit


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _divergent_pair(root: Path) -> tuple[Path, Path]:
    """A JSONL ledger and an md ledger that is missing rows, so ``--repair`` would write."""
    events = _all_events()
    return _write_pair(root, events, events[:-1])


def _run_repair(
    jsonl: Path, md: Path, scratch: Path, *, test_context: bool
) -> subprocess.CompletedProcess[str]:
    env = {
        "PATH": str(SCRIPT.parent),
        "TMPDIR": str(scratch),
        EVENTS_ENV: str(jsonl),
        MD_ENV: str(md),
    }
    if test_context:
        env[guard.TEST_CONTEXT_ENV] = "1"
    return subprocess.run(
        [str(SCRIPT), "render", "--repair"],
        capture_output=True,
        text=True,
        env=env,
        check=False,
        timeout=120,
    )


def test_repair_of_canonical_md_exits_79_and_leaves_bytes_unchanged(
    tmp_path: Path,
) -> None:
    canonical = tmp_path / "canonical"
    scratch = tmp_path / "scratch"
    canonical.mkdir()
    scratch.mkdir()
    jsonl, md = _divergent_pair(canonical)
    before = _sha(md)
    proc = _run_repair(jsonl, md, scratch, test_context=True)
    assert proc.returncode == 79, proc.stderr
    assert guard.GUARD_NAME in proc.stderr
    assert _sha(md) == before
    assert not (canonical / ".ledger_locks").exists(), "judged before the lock is taken"


def test_the_same_repair_of_a_scratch_md_succeeds(tmp_path: Path) -> None:
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    jsonl, md = _divergent_pair(scratch)
    before = _sha(md)
    proc = _run_repair(jsonl, md, scratch, test_context=True)
    assert proc.returncode == 0, proc.stderr
    assert _sha(md) != before


def test_repair_outside_a_test_runner_still_writes_the_canonical_md(
    tmp_path: Path,
) -> None:
    """The guard keys on the test signal: the same command without one is not refused."""
    canonical = tmp_path / "canonical"
    scratch = tmp_path / "scratch"
    canonical.mkdir()
    scratch.mkdir()
    jsonl, md = _divergent_pair(canonical)
    proc = _run_repair(jsonl, md, scratch, test_context=False)
    assert proc.returncode == 0, proc.stderr


def test_in_process_repair_of_canonical_md_is_refused_and_check_is_not(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    canonical = tmp_path / "canonical"
    scratch = tmp_path / "scratch"
    canonical.mkdir()
    scratch.mkdir()
    jsonl, md = _divergent_pair(canonical)
    monkeypatch.setattr(tempfile, "tempdir", str(scratch))
    monkeypatch.setenv(EVENTS_ENV, str(jsonl))
    before = _sha(md)
    code, lines = cli_work_ledger_render.run_render("repair", str(md))
    assert code == guard.EXIT_TEST_WRITE_REFUSED
    assert any(guard.GUARD_NAME in line for line in lines)
    assert _sha(md) == before
    code, _ = cli_work_ledger_render.run_render("check", str(md))
    assert code == cli_work_ledger_render.EXIT_FOUND
    assert _sha(md) == before


def test_the_test_fails_with_the_refusal_switched_off(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With the guard's check turned into a no-op the canonical md is written: the refusal,
    and nothing else, is what keeps the bytes unchanged in the tests above."""
    canonical = tmp_path / "canonical"
    scratch = tmp_path / "scratch"
    canonical.mkdir()
    scratch.mkdir()
    jsonl, md = _divergent_pair(canonical)
    monkeypatch.setattr(tempfile, "tempdir", str(scratch))
    monkeypatch.setenv(EVENTS_ENV, str(jsonl))
    monkeypatch.setattr(guard, "check_file", lambda path: None)
    before = _sha(md)
    code, _ = cli_work_ledger_render.run_render("repair", str(md))
    assert code == cli_work_ledger_render.EXIT_CLEAR
    assert _sha(md) != before


def test_a_real_topic_and_a_real_dsn_are_refused_under_a_test_runner() -> None:
    topic = "onex.evt.omnimarket.work-ledger-row-appended.v1"
    with pytest.raises(guard.LedgerTestWriteRefusedError, match=guard.GUARD_NAME):
        guard.check_topic(topic)
    with pytest.raises(guard.LedgerTestWriteRefusedError, match=guard.GUARD_NAME):
        guard.check_dsn("postgresql://u@db.internal.example:5432/ledger")
    guard.check_topic("onex.evt.test.scratch.v1")
    guard.check_dsn("postgresql://u@localhost:5432/scratch")


def test_the_scratch_ledger_fixture_gives_each_test_its_own_ledger(
    tmp_path: Path,
) -> None:
    names = (MD_ENV, "ONEX_LEDGER_WRITE_VIA", "ONEX_LEDGER_BUS_APPEND_COMMAND")
    env = ModelEnvironmentBootstrap.capture_process_environment(
        declared_keys=names
    ).environment
    assert Path(env.optional(MD_ENV) or "").parent == tmp_path
    assert env.optional("ONEX_LEDGER_WRITE_VIA") is None
    assert env.optional("ONEX_LEDGER_BUS_APPEND_COMMAND") is None
