# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Regression guard: pytest's default addopts must never re-introduce
``--timeout-method=thread`` (OMN-15977 Hole 3).

``[tool.pytest.ini_options].addopts`` is the config every bare
``uv run pytest tests/`` invocation inherits -- CI, the pre-push hook, and any
agent-launched direct run alike. ``--timeout-method=thread`` cannot kill a
CPU-bound pure-Python loop holding the GIL (the watcher thread that would fire
the kill never gets scheduled while the GIL is held continuously); this was
the config behind two 2026-08-12 local runaways (46min, 53min) that required a
manual SIGKILL. ``--timeout-method=signal`` delivers SIGALRM, which interrupts
at the next Python bytecode boundary regardless of GIL contention.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

_PYPROJECT = Path(__file__).resolve().parents[2] / "pyproject.toml"


def _addopts() -> list[str]:
    data = tomllib.loads(_PYPROJECT.read_text(encoding="utf-8"))
    addopts = data["tool"]["pytest"]["ini_options"]["addopts"]
    assert isinstance(addopts, list), (
        f"expected addopts to be a list, got {type(addopts)}"
    )
    return addopts


def test_pyproject_exists() -> None:
    assert _PYPROJECT.is_file(), f"expected {_PYPROJECT}"


def test_addopts_does_not_set_thread_timeout_method() -> None:
    addopts = _addopts()
    assert "--timeout-method=thread" not in addopts, (
        "pyproject.toml addopts must not set --timeout-method=thread -- it "
        f"cannot kill a CPU-bound runaway; got addopts={addopts!r}"
    )


def test_addopts_sets_signal_timeout_method() -> None:
    addopts = _addopts()
    assert "--timeout-method=signal" in addopts, (
        f"expected --timeout-method=signal in addopts; got {addopts!r}"
    )
