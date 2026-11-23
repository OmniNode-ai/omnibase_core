# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OMN-19513: the ledger write guard refuses ledger writes under a test runner.

Operator ruling 2026-10-01: "it should be impossible to like fake test like that". A test's
own ledger lives under the temporary directory; a canonical file, topic or DSN is refused.
The ``onex-work-ledger render --repair`` command that first carried this guard is retired
(OMN-26513), so the guard's file check is exercised directly here.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from omnibase_core.handlers import handler_ledger_write_guard as guard
from omnibase_core.models.bootstrap.model_environment_bootstrap import (
    ModelEnvironmentBootstrap,
)
from tests.conftest import LEDGER_PATH_ENV

pytestmark = pytest.mark.unit


def test_a_canonical_ledger_file_is_refused_under_a_test_runner(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(scratch))
    canonical = tmp_path / "canonical" / "ledger.md"
    assert guard.file_is_canonical(canonical)
    with pytest.raises(guard.ModelLedgerTestWriteRefusedError, match=guard.GUARD_NAME):
        guard.check_file(canonical)


def test_a_scratch_ledger_file_is_not_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(scratch))
    own = scratch / "ledger.md"
    assert not guard.file_is_canonical(own)
    guard.check_file(own)


def test_the_same_canonical_file_is_not_refused_outside_a_test_runner(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The guard keys on the test signal: with none present the check passes."""
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(scratch))
    monkeypatch.setattr(guard, "runner_signal", lambda: None)
    guard.check_file(tmp_path / "canonical" / "ledger.md")


def test_a_real_topic_and_a_real_dsn_are_refused_under_a_test_runner() -> None:
    topic = "onex.evt.omnimarket.work-ledger-row-appended.v1"
    with pytest.raises(guard.ModelLedgerTestWriteRefusedError, match=guard.GUARD_NAME):
        guard.check_topic(topic)
    with pytest.raises(guard.ModelLedgerTestWriteRefusedError, match=guard.GUARD_NAME):
        guard.check_dsn("postgresql://u@db.internal.example:5432/ledger")
    guard.check_topic("onex.evt.test.scratch.v1")
    guard.check_dsn("postgresql://u@localhost:5432/scratch")


def test_the_scratch_ledger_fixture_gives_each_test_its_own_ledger(
    tmp_path: Path,
) -> None:
    names = (LEDGER_PATH_ENV, "ONEX_LEDGER_WRITE_VIA", "ONEX_LEDGER_BUS_APPEND_COMMAND")
    env = ModelEnvironmentBootstrap.capture_process_environment(
        declared_keys=names
    ).environment
    assert Path(env.optional(LEDGER_PATH_ENV) or "").parent == tmp_path
    assert env.optional("ONEX_LEDGER_WRITE_VIA") is None
    assert env.optional("ONEX_LEDGER_BUS_APPEND_COMMAND") is None
