# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Regression test for OMN-17870 — Werror teardown must not leak an event loop.

With ``PYTHONWARNINGS=error`` the teardown of
``test_dependency_unavailable_preserves_subclass.py`` failed with an
``ExceptionGroup`` of three ``PytestUnraisableExceptionWarning``s: two
``ResourceWarning: unclosed <socket.socket ... family=1>`` (AF_UNIX) and one
``ResourceWarning: unclosed event loop``. The assertions passed; the container
code was not the owner. pytest-asyncio < 1.4 calls ``asyncio.get_event_loop()``
while installing its temporary loop policy, which creates an implicit event loop
(a selector plus its AF_UNIX self-pipe socketpair) and never closes it. The
first sync test that calls ``asyncio.run()`` afterwards drops the last reference
to that loop, and the next garbage collection reports it as unraisable.
pytest-asyncio 1.4.0 closes it (upstream issue #724, PR #1430), so the project
pins ``pytest-asyncio>=1.4,<2``.

The test runs a fresh pytest process under ``PYTHONWARNINGS=error`` over the same
shape (an async test, then a sync ``asyncio.run()`` test, each followed by a
``gc.collect()``). A fresh process is the only honest observer: the warning is
raised by pytest's unraisable-exception hook while the host session is already
past it, and a Werror filter cannot be turned on for the host run without
changing every other test.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

_PYTEST_INI = """\
[pytest]
asyncio_mode = auto
asyncio_default_fixture_loop_scope = function
"""

_INNER_TESTS = """\
import asyncio
import gc

import pytest


@pytest.fixture(autouse=True)
def _collect_garbage_after_each_test():
    yield
    gc.collect()


async def test_async_test_runs_first():
    await asyncio.sleep(0)


def test_sync_asyncio_run_drops_the_implicit_loop():
    asyncio.run(asyncio.sleep(0))


def test_sync_test_after_asyncio_run():
    assert True
"""

_SESSION_FINISH_CONTROL = """\
import sys
import warnings

import pytest


class WarningControl:
    @pytest.hookimpl(trylast=True)
    def pytest_sessionfinish(self):
        for category in (ResourceWarning, pytest.PytestUnraisableExceptionWarning):
            with pytest.raises(category, match="session-finish warning control"):
                warnings.warn("session-finish warning control", category)
        print("SESSION_FINISH_WARNINGS_REMAIN_ERRORS")


raise SystemExit(pytest.main(sys.argv[1:], plugins=[WarningControl()]))
"""


@pytest.mark.unit
class TestWerrorEventLoopTeardown:
    """The test lifecycle closes every loop it opens, so Werror teardown is clean."""

    def test_service_resolution_session_finishes_with_werror_enabled(self) -> None:
        """Observe real container tests through session teardown, including warnings.

        The obsolete models session hook ignored ResourceWarning and accessed an
        implicit event loop after pytest-asyncio had already closed its loops.
        A final hook checks that warnings still raise, so suppression cannot make
        the subprocess appear clean.
        """
        repo_root = Path(__file__).resolve().parents[4]
        completed = subprocess.run(
            [
                sys.executable,
                "-c",
                _SESSION_FINISH_CONTROL,
                "-c",
                str(repo_root / "pyproject.toml"),
                "-o",
                "addopts=",
                "-p",
                "no:cacheprovider",
                "-p",
                "no:randomly",
                "-W",
                "error",
                "-q",
                str(
                    Path(__file__).with_name(
                        "test_dependency_unavailable_preserves_subclass.py"
                    )
                ),
            ],
            cwd=repo_root,
            env={"PYTHONWARNINGS": "error"},
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )

        output = completed.stdout + completed.stderr
        assert completed.returncode == 0, output
        assert "2 passed" in output, output
        assert "SESSION_FINISH_WARNINGS_REMAIN_ERRORS" in output, output
        assert "[Session Cleanup]" not in output, output
        assert "unclosed" not in output, output
        assert "PytestUnraisableExceptionWarning" not in output, output

    def test_async_then_asyncio_run_tears_down_without_unraisable_warnings(
        self, tmp_path: Path
    ) -> None:
        """An async test followed by ``asyncio.run()`` leaves nothing unclosed.

        Fails on pytest-asyncio 1.3.0 with the unclosed-socket / unclosed-loop
        ``ExceptionGroup`` from the ticket; passes on 1.4.0.
        """
        # Arrange
        (tmp_path / "pytest.ini").write_text(_PYTEST_INI)
        (tmp_path / "test_inner_lifecycle.py").write_text(_INNER_TESTS)
        # An explicit environment: the child must not inherit PYTEST_ADDOPTS,
        # coverage hooks or a parent warning filter that would change the result.
        env = {"PYTHONWARNINGS": "error"}

        # Act
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "-p",
                "no:cacheprovider",
                "-p",
                "no:randomly",
                "-p",
                "no:xdist",
                "-q",
                str(tmp_path / "test_inner_lifecycle.py"),
            ],
            cwd=tmp_path,
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )

        # Assert
        output = completed.stdout + completed.stderr
        assert "unclosed" not in output, output
        assert "PytestUnraisableExceptionWarning" not in output, output
        assert completed.returncode == 0, output
        assert "3 passed" in output, output
