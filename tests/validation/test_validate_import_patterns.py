# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Equivalence tests for scripts/validation/validate-import-patterns.py (OMN-12177).

Captures current pass/fail behavior as a regression baseline before any refactoring.
Does NOT modify the script. Tests the ImportPatternValidator class directly.

Pass cases (exit 0 / zero violations):
    - File with only sibling (single-dot) imports
    - File with no imports
    - File with absolute imports

Fail cases (violations detected):
    - File with double-dot relative import (from ..parent import X)
    - File with triple-dot relative import (from ...grandparent import X)
    - Multiple violations in a single file
    - Directory containing violating files

Boundary cases:
    - max_violations threshold allows some violations through
    - File with mixed sibling and multi-level imports
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Module loading
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = _REPO_ROOT / "scripts" / "validation" / "validate-import-patterns.py"


def _load_module():  # type: ignore[return]
    spec = importlib.util.spec_from_file_location("validate_import_patterns", _SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


_mod = _load_module()
ImportPatternValidator = _mod.ImportPatternValidator


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _write_py(tmp_path: Path, name: str, content: str) -> Path:
    f = tmp_path / name
    f.write_text(content)
    return f


# ---------------------------------------------------------------------------
# Pass cases
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_no_imports_no_violations(tmp_path: Path) -> None:
    """A file with no imports at all produces zero violations."""
    _write_py(tmp_path, "no_imports.py", "x = 1\n")
    v = ImportPatternValidator()
    v.validate_directory(tmp_path)
    assert v.violations == []


@pytest.mark.unit
def test_absolute_imports_no_violations(tmp_path: Path) -> None:
    """Absolute imports are always accepted."""
    _write_py(
        tmp_path,
        "abs_imports.py",
        "from omnibase_core.enums.enum_type import EnumType\n"
        "from omnibase_core.models.model_foo import ModelFoo\n",
    )
    v = ImportPatternValidator()
    v.validate_directory(tmp_path)
    assert v.violations == []


@pytest.mark.unit
def test_sibling_single_dot_import_no_violations(tmp_path: Path) -> None:
    """Single-dot (sibling) imports are not flagged."""
    _write_py(tmp_path, "sibling.py", "from .model_sibling import ModelSibling\n")
    v = ImportPatternValidator()
    v.validate_directory(tmp_path)
    assert v.violations == []


@pytest.mark.unit
def test_mixed_sibling_and_absolute_no_violations(tmp_path: Path) -> None:
    """Sibling + absolute imports together: no violations."""
    _write_py(
        tmp_path,
        "mixed.py",
        "from .util import helper\n"
        "from omnibase_core.models.model_base import ModelBase\n",
    )
    v = ImportPatternValidator()
    v.validate_directory(tmp_path)
    assert v.violations == []


@pytest.mark.unit
def test_empty_directory_no_violations(tmp_path: Path) -> None:
    """An empty directory (no Python files) produces no violations."""
    v = ImportPatternValidator()
    v.validate_directory(tmp_path)
    assert v.violations == []


# ---------------------------------------------------------------------------
# Fail cases
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_double_dot_relative_import_detected(tmp_path: Path) -> None:
    """from ..parent import Something is flagged as a violation."""
    _write_py(
        tmp_path,
        "double_dot.py",
        "from ..parent_module import ParentThing\n",
    )
    v = ImportPatternValidator()
    v.validate_directory(tmp_path)
    assert len(v.violations) == 1
    assert v.violations[0]["level"] == 2


@pytest.mark.unit
def test_triple_dot_relative_import_detected(tmp_path: Path) -> None:
    r"""from ...grandparent.module import Thing is flagged.

    The script uses overlapping regex patterns: the level-2 pattern (\.\.x)
    also matches the prefix of level-3 (\.\.\.x), so a triple-dot import
    produces TWO violation entries — one at level 2 and one at level 3.
    This test captures that actual behavior.
    """
    _write_py(
        tmp_path,
        "triple_dot.py",
        "from ...grandparent.module import Thing\n",
    )
    v = ImportPatternValidator()
    v.validate_directory(tmp_path)
    # Overlapping patterns: both level-2 and level-3 match one triple-dot import
    assert len(v.violations) == 2
    levels = {viol["level"] for viol in v.violations}
    assert 3 in levels


@pytest.mark.unit
def test_multiple_violations_in_single_file(tmp_path: Path) -> None:
    """Multiple multi-level imports in one file produce multiple violations.

    The triple-dot import (from ...c) triggers both the level-2 and level-3
    patterns, so the total count is 4 (2 double-dot + 2 from triple-dot).
    This test captures that actual behavior.
    """
    _write_py(
        tmp_path,
        "multi_violations.py",
        "from ..a import A\nfrom ..b import B\nfrom ...c import C\n",
    )
    v = ImportPatternValidator()
    v.validate_directory(tmp_path)
    # 2 double-dot imports + 1 triple-dot that fires both level-2 and level-3 = 4
    assert len(v.violations) == 4


@pytest.mark.unit
def test_violation_contains_file_and_line(tmp_path: Path) -> None:
    """Violation dict contains file path and correct line number."""
    target = _write_py(tmp_path, "lineno.py", "x = 1\nfrom ..foo import Bar\n")
    v = ImportPatternValidator()
    v.validate_directory(tmp_path)
    assert len(v.violations) == 1
    viol = v.violations[0]
    assert str(target) == viol["file"]
    assert viol["line"] == 2


@pytest.mark.unit
def test_violation_suggests_absolute_import(tmp_path: Path) -> None:
    """suggested_absolute field is populated and non-empty."""
    _write_py(tmp_path, "suggest.py", "from ..models.model_foo import ModelFoo\n")
    v = ImportPatternValidator()
    v.validate_directory(tmp_path)
    assert v.violations
    assert v.violations[0]["suggested_absolute"]


# ---------------------------------------------------------------------------
# Boundary / max_violations
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_max_violations_zero_fails_on_any(tmp_path: Path) -> None:
    """Default max_violations=0 means any violation counts as a failure."""
    _write_py(tmp_path, "bad.py", "from ..x import X\n")
    v = ImportPatternValidator(max_violations=0)
    v.validate_directory(tmp_path)
    assert len(v.violations) > v.max_violations


@pytest.mark.unit
def test_max_violations_allows_under_threshold(tmp_path: Path) -> None:
    """Violations <= max_violations is within acceptable limit (exit 0 semantics)."""
    _write_py(tmp_path, "bad.py", "from ..x import X\n")
    v = ImportPatternValidator(max_violations=5)
    v.validate_directory(tmp_path)
    assert len(v.violations) <= v.max_violations


@pytest.mark.unit
def test_skips_venv_directory(tmp_path: Path) -> None:
    """Files under .venv are skipped during discovery."""
    venv = tmp_path / ".venv" / "lib"
    venv.mkdir(parents=True)
    _write_py(venv, "bad.py", "from ..x import X\n")
    v = ImportPatternValidator()
    v.validate_directory(tmp_path)
    assert v.violations == []


@pytest.mark.unit
def test_skips_archived_directory(tmp_path: Path) -> None:
    """Files under 'archived' subdirectory are excluded."""
    archived = tmp_path / "archived"
    archived.mkdir()
    _write_py(archived, "bad.py", "from ..x import X\n")
    v = ImportPatternValidator()
    v.validate_directory(tmp_path)
    assert v.violations == []


@pytest.mark.unit
def test_multiple_files_violations_aggregated(tmp_path: Path) -> None:
    """Violations from multiple files are all collected."""
    _write_py(tmp_path, "file_a.py", "from ..a import A\n")
    _write_py(tmp_path, "file_b.py", "from ..b import B\n")
    v = ImportPatternValidator()
    v.validate_directory(tmp_path)
    assert len(v.violations) == 2
    files = {viol["file"] for viol in v.violations}
    assert len(files) == 2
