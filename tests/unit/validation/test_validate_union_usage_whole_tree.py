# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The validate-union-usage hook is one whole-tree ratchet (OMN-19515).

The hook used to run with ``pass_filenames: true`` and an invalid-union cap
that the script applied to each pre-commit xargs batch. pre-commit shuffles
the file list with a fixed seed and partitions it, so adding any file
reshuffled every batch and could push one batch over the cap while the
whole-tree total barely moved (omnibase_core#1761: 440 on dev, 441 on the PR,
one batch at 188 against a cap of 160).

These tests pin the replacement: one invocation over the whole matching tree,
one ceiling equal to the measured total, and no counting of the classinfo
argument of ``isinstance``/``issubclass``, which is a runtime class check and
not a type annotation.
"""

from __future__ import annotations

import ast
import importlib.util
import re
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
import yaml

if TYPE_CHECKING:
    from types import ModuleType

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts" / "validation" / "validate-union-usage.py"
PRECOMMIT_CONFIG = REPO_ROOT / ".pre-commit-config.yaml"
HOOK_ID = "validate-union-usage"


@pytest.fixture(scope="module")
def union_script() -> ModuleType:
    """Load the validate-union-usage.py script as a module."""
    spec = importlib.util.spec_from_file_location("validate_union_usage", SCRIPT)
    module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def _check(union_script: ModuleType, code: str) -> Any:
    checker = union_script.UnionUsageChecker("/test/path.py", code)
    checker.visit(ast.parse(code))
    return checker


def _hook() -> dict[str, Any]:
    config = yaml.safe_load(PRECOMMIT_CONFIG.read_text(encoding="utf-8"))
    for repo in config["repos"]:
        for hook in repo.get("hooks", []):
            if hook.get("id") == HOOK_ID:
                return dict(hook)
    raise AssertionError(f"hook {HOOK_ID} not found in {PRECOMMIT_CONFIG}")


def _ceiling(hook: dict[str, Any]) -> int:
    args = list(hook["args"])
    return int(args[args.index("--allow-invalid") + 1])


@pytest.mark.unit
class TestClassinfoUnionsAreNotTypeUnions:
    """A ``|`` chain passed as isinstance/issubclass classinfo is not counted."""

    def test_isinstance_classinfo_union_not_counted(
        self, union_script: ModuleType
    ) -> None:
        code = "def f(x):\n    return isinstance(x, Alpha | Beta | Gamma)\n"
        checker = _check(union_script, code)
        assert checker.union_count == 0
        assert checker.invalid_union_count == 0

    def test_issubclass_classinfo_union_not_counted(
        self, union_script: ModuleType
    ) -> None:
        code = "def f(t):\n    return issubclass(t, Alpha | Beta | Gamma)\n"
        checker = _check(union_script, code)
        assert checker.union_count == 0
        assert checker.invalid_union_count == 0

    def test_union_inside_classinfo_tuple_not_counted(
        self, union_script: ModuleType
    ) -> None:
        code = "def f(x):\n    return isinstance(x, (Alpha | Beta | Gamma, Delta))\n"
        checker = _check(union_script, code)
        assert checker.union_count == 0

    def test_annotation_union_in_same_file_still_counted(
        self, union_script: ModuleType
    ) -> None:
        code = (
            "def f(x: Alpha | Beta | Gamma) -> bool:\n"
            "    return isinstance(x, Alpha | Beta | Gamma)\n"
        )
        checker = _check(union_script, code)
        assert checker.union_count >= 1
        assert checker.invalid_union_count >= 1
        assert all(p.line == 1 for p in checker.union_patterns)

    def test_union_in_first_isinstance_argument_still_counted(
        self, union_script: ModuleType
    ) -> None:
        code = "def f():\n    return isinstance(cast(Alpha | Beta | Gamma, v), Delta)\n"
        checker = _check(union_script, code)
        assert checker.union_count >= 1


@pytest.mark.unit
class TestExcludeRegex:
    """The script excludes paths itself when it scans the tree."""

    @staticmethod
    def _tree(tmp_path: Path) -> None:
        bad = "def f(x: str | int | float | bool | bytes) -> None: ...\n"
        (tmp_path / "src" / "pkg" / "protocols").mkdir(parents=True)
        (tmp_path / "src" / "pkg" / "mod.py").write_text(bad, encoding="utf-8")
        (tmp_path / "src" / "pkg" / "protocols" / "p.py").write_text(
            bad, encoding="utf-8"
        )

    def _run(self, tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=False,
        )

    @staticmethod
    def _scanned(result: subprocess.CompletedProcess[str]) -> int:
        match = re.search(r"Scanned (\d+) Python files", result.stdout)
        assert match is not None, result.stdout
        return int(match.group(1))

    def test_whole_tree_scan_counts_every_file(self, tmp_path: Path) -> None:
        self._tree(tmp_path)
        result = self._run(tmp_path, "--allow-invalid", "1000")
        assert result.returncode == 0, result.stdout
        assert self._scanned(result) == 2

    def test_exclude_regex_drops_matching_paths(self, tmp_path: Path) -> None:
        self._tree(tmp_path)
        whole = self._run(tmp_path, "--allow-invalid", "1000")
        excluded = self._run(
            tmp_path,
            "--allow-invalid",
            "1000",
            "--exclude-regex",
            "^src/pkg/protocols/",
        )
        assert excluded.returncode == 0, excluded.stdout
        assert self._scanned(excluded) == 1
        found = re.compile(r"(\d+) invalid unions")
        whole_match = found.search(whole.stdout)
        excluded_match = found.search(excluded.stdout)
        assert whole_match is not None and excluded_match is not None
        assert int(excluded_match.group(1)) < int(whole_match.group(1))


@pytest.mark.unit
class TestHookIsOneWholeTreeRatchet:
    """The hook config runs one invocation against one whole-tree ceiling."""

    def test_hook_does_not_receive_batched_filenames(self) -> None:
        hook = _hook()
        assert hook.get("pass_filenames") is False

    def test_hook_excludes_protocols_in_the_script(self) -> None:
        args = list(_hook()["args"])
        assert "--exclude-regex" in args
        assert args[args.index("--exclude-regex") + 1] == (
            "^src/omnibase_core/protocols/"
        )

    def test_configured_ceiling_equals_measured_whole_tree_total(self) -> None:
        """Ratchet: the ceiling is the tree's own count, never headroom.

        Removing an invalid union fails this test until the ceiling is
        lowered to match; adding one fails the hook itself.
        """
        hook = _hook()
        args = list(hook["args"])
        args[args.index("--allow-invalid") + 1] = "1000000"
        result = subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        match = re.search(r"(\d+) invalid unions", result.stdout)
        assert match is not None, result.stdout
        assert int(match.group(1)) == _ceiling(hook)
