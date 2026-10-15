# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Unit tests: importing dependency-injector must not leave an unraisable exception.

dependency-injector 4.48.3 probes ``pydantic_settings`` at import time and, when
that package is absent, falls back to ``from pydantic import BaseSettings``.
Pydantic 2 routes that access through ``pydantic.__getattr__`` and raises
``PydanticImportError`` from inside ``PyObject_HasAttr()``, which Python 3.13
reports as an unraisable exception. Under a warnings-as-errors run pytest turns
that into a fatal ``PytestUnraisableExceptionWarning`` (OMN-17866).

The repository has no runtime ``pydantic_settings`` dependency, so the fix is a
dependency-injector release that does not touch ``pydantic.BaseSettings`` on
Pydantic 2. The check runs in a subprocess pytest session so the global
``PytestUnraisableExceptionWarning`` stays un-suppressed in this repository.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

_PROBE_MODULE = textwrap.dedent(
    """\
    import pydantic
    from dependency_injector import providers


    def test_import_leaves_no_unraisable_exception():
        assert pydantic.VERSION.startswith("2.")
        assert providers.Singleton(dict)() == {}
    """
)


@pytest.mark.unit
def test_dependency_injector_import_is_clean_under_unraisable_as_error(
    tmp_path: Path,
) -> None:
    """A module importing dependency-injector passes with unraisable warnings fatal."""
    probe = tmp_path / "test_probe.py"
    probe.write_text(_PROBE_MODULE)

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            str(probe),
            "-c",
            "/dev/null",
            "--rootdir",
            str(tmp_path),
            "-p",
            "no:cacheprovider",
            "-p",
            "no:xdist",
            "-q",
            "-W",
            "error::pytest.PytestUnraisableExceptionWarning",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "1 passed" in result.stdout


@pytest.mark.unit
def test_pydantic_settings_is_not_a_hidden_requirement() -> None:
    """The clean import must not depend on ``pydantic_settings`` being installed.

    The project declares no ``pydantic-settings`` dependency, so the regression
    above only proves the fix when the package is absent from the environment.
    """
    assert importlib.util.find_spec("pydantic_settings") is None
