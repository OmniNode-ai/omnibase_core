# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Union discovery and the per-file replacement of the whole-tree allowance.

The hook now receives staged filenames and judges each source finding against
its baseline entry. The legacy script's directory discovery and classinfo
exclusions remain covered while its predicates await a later migration slice.
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
class TestHookUsesPerFileBaseline:
    """The staged batch cannot borrow allowance from any other file."""

    def test_hook_receives_filenames(self) -> None:
        assert _hook()["pass_filenames"] is True

    def test_hook_has_no_global_allowance(self) -> None:
        hook = _hook()
        assert "--allow-invalid" not in str(hook)
        assert "--baseline .onex_ratchets/validate-union-usage.yaml" in hook["entry"]

    def test_runtime_preserves_protocol_exclusion(self) -> None:
        from omnibase_core.nodes.node_finding_baseline_check_effect.runtime_legacy_ratchet_check import (
            load_rules,
        )

        rule = next(r for r in load_rules().rules if r.hook == HOOK_ID)
        assert "src/omnibase_core/protocols/" in rule.exclude_prefixes
