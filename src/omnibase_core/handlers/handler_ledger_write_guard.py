# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The ledger test-write guard: a test process never writes the canonical ledger (OMN-19513).

Operator ruling 2026-10-01 (lane ledger-test-write-guard): "it should be impossible to like fake
test like that". Test isolation is a convention a test can forget; this guard sits in the write
path itself, so the refusal does not depend on how a test was set up.

A write is refused when BOTH hold:

1. The process runs under a test runner: ``PYTEST_CURRENT_TEST`` is set, ``pytest`` is
   imported, or ``ONEX_TEST_CONTEXT`` is set to a non-empty value. ``unittest`` being imported is
   NOT a signal here: ``onex-work-ledger`` itself imports it through a dependency, so that signal
   would refuse every real ``--repair``. A ``unittest`` run sets ``ONEX_TEST_CONTEXT``. The
   environment signals are inherited, so a subprocess a test starts is in test context too.
2. The target is canonical:

   - a ledger FILE outside the temporary directory, or inside a ``$OMNI_HOME`` that is not itself
     under the temporary directory. A test's ledger is a ``tmp_path`` file; every other copy (the
     ledger of record, a lane's snapshot, an archive split) is canonical;
   - a canonical work-ledger TOPIC name (``onex.{evt,cmd}.omnimarket.work-ledger-*``);
   - a projection DSN whose host is not loopback or a local socket.

There is no bypass flag and no allowlist. ``onex-work-ledger render --repair`` calls
:func:`check_file` before it takes the md lock or writes a byte; the refusal is
:class:`ModelLedgerTestWriteRefusedError` and the command exit is :data:`EXIT_TEST_WRITE_REFUSED`.
"""

from __future__ import annotations

import re
import sys
import tempfile
from pathlib import Path
from typing import Final
from urllib.parse import urlsplit

from omnibase_core.enums.enum_ledger_write_target import EnumLedgerWriteTarget
from omnibase_core.models.bootstrap.model_environment_bootstrap import (
    ModelEnvironmentBootstrap,
)
from omnibase_core.models.ledger_write_guard.model_ledger_test_write_refused import (
    GUARD_NAME,
    ModelLedgerTestWriteRefusedError,
)
from omnibase_core.models.ledger_write_guard.model_ledger_write_guard_decision import (
    ModelLedgerWriteGuardDecision,
)
from omnibase_core.models.ledger_write_guard.model_ledger_write_guard_request import (
    ModelLedgerWriteGuardRequest,
)
from omnibase_core.models.runtime.model_network_defaults import (
    packaged_network_defaults,
)

__all__ = [
    "HandlerLedgerWriteGuard",
    "CANONICAL_TOPIC",
    "EXIT_TEST_WRITE_REFUSED",
    "GUARD_NAME",
    "TEST_CONTEXT_ENV",
    "ModelLedgerTestWriteRefusedError",
    "check_dsn",
    "check_file",
    "check_topic",
    "dsn_is_canonical",
    "file_is_canonical",
    "runner_signal",
    "topic_is_canonical",
]

TEST_CONTEXT_ENV: Final = "ONEX_TEST_CONTEXT"
EXIT_TEST_WRITE_REFUSED: Final = 79
CANONICAL_TOPIC: Final = re.compile(
    r"^onex\.(?:evt|cmd)\.omnimarket\.work-ledger-[a-z0-9-]+\.v\d+$"
)
_LOOPBACK_HOSTS: Final = frozenset({""}) | packaged_network_defaults().loopback_hosts
_RUNNER_MODULES: Final = ("pytest",)
_PYTEST_ENV: Final = "PYTEST_CURRENT_TEST"
_OMNI_HOME_ENV: Final = "OMNI_HOME"


def _env(name: str) -> str:
    bootstrap = ModelEnvironmentBootstrap.capture_process_environment(
        declared_keys=(name,)
    )
    return (bootstrap.environment.optional(name) or "").strip()


def runner_signal() -> str | None:
    """The first test-runner signal present, named, or None outside a test."""
    if _env(_PYTEST_ENV):
        return f"{_PYTEST_ENV} is set"
    if _env(TEST_CONTEXT_ENV):
        return f"{TEST_CONTEXT_ENV} is set"
    for name in _RUNNER_MODULES:
        if name in sys.modules:
            return f"{name} is imported"
    return None


def _inside(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def file_is_canonical(path: Path) -> bool:
    """A ledger file is a test's own only under the temporary directory, and never inside a
    registry root (``OMNI_HOME``) that is not itself a test's scratch directory."""
    resolved = path.expanduser().resolve()
    temp_root = Path(tempfile.gettempdir()).resolve()
    omni_home = _env(_OMNI_HOME_ENV)
    if omni_home:
        home = Path(omni_home).expanduser().resolve()
        if not _inside(home, temp_root) and _inside(resolved, home):
            return True
    return not _inside(resolved, temp_root)


def topic_is_canonical(topic: str) -> bool:
    return CANONICAL_TOPIC.match(topic.strip()) is not None


def dsn_is_canonical(dsn: str) -> bool:
    """A DSN reaches a shared database unless its host is loopback or a local socket."""
    text = dsn.strip()
    if "://" in text:
        host = urlsplit(text).hostname or ""
    else:
        match = re.search(r"(?:^|\s)host=(\S+)", text)
        host = match.group(1) if match else ""
    return not (host.lower() in _LOOPBACK_HOSTS or host.startswith("/"))


def _refuse_if_test(target_kind: str, target: str) -> None:
    signal = runner_signal()
    if signal is not None:
        raise ModelLedgerTestWriteRefusedError(signal, target_kind, target)


def check_file(path: Path) -> None:
    """Refuse a test's write to a canonical ledger file."""
    if file_is_canonical(path):
        _refuse_if_test("ledger file", str(path))


def check_topic(topic: str) -> None:
    """Refuse a test's publish of a canonical work-ledger topic."""
    if topic_is_canonical(topic):
        _refuse_if_test("ledger topic", topic)


def check_dsn(dsn: str) -> None:
    """Refuse a test's write to a projection DSN that is not loopback."""
    if dsn_is_canonical(dsn):
        _refuse_if_test(
            "projection DSN", urlsplit(dsn).hostname or "<non-loopback host>"
        )


class HandlerLedgerWriteGuard:
    """The ledger test-write guard as a node handler."""

    def handle(
        self, request: ModelLedgerWriteGuardRequest
    ) -> ModelLedgerWriteGuardDecision:
        """Refuse the write when a test runner is present and the target is canonical."""
        canonical = {
            EnumLedgerWriteTarget.FILE: lambda target: file_is_canonical(Path(target)),
            EnumLedgerWriteTarget.TOPIC: topic_is_canonical,
            EnumLedgerWriteTarget.DSN: dsn_is_canonical,
        }[request.target_kind](request.target)
        signal = runner_signal() if canonical else None
        return ModelLedgerWriteGuardDecision(refused=signal is not None, signal=signal)
