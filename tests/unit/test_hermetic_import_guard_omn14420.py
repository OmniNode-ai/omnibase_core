# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""OMN-14420: tests must fail loudly when ``omnibase_core`` is imported from outside this checkout.

An ambient ``PYTHONPATH`` pointing at the canonical clone's ``src/`` places that clone ahead of
the worktree on ``sys.path``, so a worktree test run silently executes canonical-clone source.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tests.fixtures.hermetic_import import assert_hermetic_import

_REPO_ROOT = Path(__file__).resolve().parents[2]
_PROBE_TEST = "tests/unit/test_hermetic_import_guard_probe_omn14420.py"


@pytest.mark.unit
class TestAssertHermeticImport:
    def test_accepts_module_inside_repo(self, tmp_path: Path) -> None:
        module = tmp_path / "src" / "pkg" / "__init__.py"
        module.parent.mkdir(parents=True)
        module.touch()

        assert_hermetic_import("pkg", module, tmp_path)

    def test_rejects_module_outside_repo(self, tmp_path: Path) -> None:
        repo = tmp_path / "worktree"
        repo.mkdir()
        canonical = tmp_path / "canonical" / "src" / "pkg" / "__init__.py"
        canonical.parent.mkdir(parents=True)
        canonical.touch()

        with pytest.raises(RuntimeError, match="OMN-14420") as excinfo:
            assert_hermetic_import("pkg", canonical, repo)

        message = str(excinfo.value)
        assert str(canonical) in message
        assert str(repo) in message
        assert "env -u PYTHONPATH" in message

    def test_symlink_into_repo_is_followed(self, tmp_path: Path) -> None:
        repo = tmp_path / "worktree"
        real = repo / "src" / "pkg"
        real.mkdir(parents=True)
        (real / "__init__.py").touch()
        link = tmp_path / "decoy" / "pkg"
        link.parent.mkdir()
        link.symlink_to(real, target_is_directory=True)

        assert_hermetic_import("pkg", link / "__init__.py", repo)


@pytest.mark.unit
class TestConftestGuardUnderAmbientPythonpath:
    """Drive pytest itself with a decoy ``omnibase_core`` ahead of this checkout."""

    @staticmethod
    def _collect(
        home: Path, env_pythonpath: str | None
    ) -> subprocess.CompletedProcess[str]:
        # A minimal environment: the inherited one may itself carry an ambient PYTHONPATH.
        env = {"HOME": str(home)}
        if env_pythonpath is not None:
            env["PYTHONPATH"] = env_pythonpath
        return subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                _PROBE_TEST,
                "--collect-only",
                "-q",
                "-n",
                "0",
                "-p",
                "no:cacheprovider",
            ],
            cwd=_REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=False,
            timeout=50,
        )

    def test_collection_aborts_when_pythonpath_shadows_checkout(
        self, tmp_path: Path
    ) -> None:
        decoy = tmp_path / "decoy_src"
        shutil.copytree(
            _REPO_ROOT / "src" / "omnibase_core",
            decoy / "omnibase_core",
            ignore=shutil.ignore_patterns("__pycache__"),
        )

        result = self._collect(tmp_path, str(decoy))

        assert result.returncode != 0, result.stdout + result.stderr
        assert "Hermetic import guard failed" in result.stdout + result.stderr

    def test_collection_succeeds_without_ambient_pythonpath(
        self, tmp_path: Path
    ) -> None:
        result = self._collect(tmp_path, None)

        assert result.returncode == 0, result.stdout + result.stderr
        assert "Hermetic import guard failed" not in result.stdout + result.stderr
