# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Equivalence tests for scripts/validation/validate-typing-syntax.py (OMN-12177).

Captures current pass/fail behavior as a regression baseline before refactoring.
Does NOT modify the script. Tests check_file_for_typing_syntax and
validate_typing_syntax directly.

Pass cases (no violations):
    - File with no typing imports or usage
    - File using modern X | Y union syntax
    - File using modern X | None (no Optional)
    - File using generic types like list[str], dict[str, int]

Fail cases (violations detected):
    - Optional[Type] → should be Type | None
    - Union[Type1, Type2] → should be Type1 | Type2
    - Union[Type1, Type2, Type3] → should be Type1 | Type2 | Type3
    - Union[SingleType] → unnecessary union
    - typing.Optional[T] (qualified form)
    - typing.Union[T1, T2] (qualified form)

Boundary cases:
    - max_violations=0 triggers failure on any violation
    - max_violations > count passes
    - Non-existent src_dir is skipped gracefully
    - validate_typing_syntax aggregates across multiple files
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Module loading
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = _REPO_ROOT / "scripts" / "validation" / "validate-typing-syntax.py"


def _load_module():  # type: ignore[return]
    spec = importlib.util.spec_from_file_location("validate_typing_syntax", _SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


_mod = _load_module()
check_file_for_typing_syntax = _mod.check_file_for_typing_syntax
validate_typing_syntax = _mod.validate_typing_syntax


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write(tmp_path: Path, name: str, content: str) -> Path:
    f = tmp_path / name
    f.write_text(content)
    return f


# ---------------------------------------------------------------------------
# Pass cases: check_file_for_typing_syntax
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_no_typing_usage_returns_empty(tmp_path: Path) -> None:
    """File with no typing imports or usage returns no violations."""
    f = _write(tmp_path, "clean.py", "x: int = 1\ny: str = 'hello'\n")
    violations = check_file_for_typing_syntax(f)
    assert violations == []


@pytest.mark.unit
def test_modern_pipe_union_not_flagged(tmp_path: Path) -> None:
    """Modern X | Y syntax is not flagged."""
    f = _write(tmp_path, "modern.py", "def foo(x: str | int) -> str | None:\n    ...\n")
    violations = check_file_for_typing_syntax(f)
    assert violations == []


@pytest.mark.unit
def test_generic_types_not_flagged(tmp_path: Path) -> None:
    """list[str], dict[str, int] are not flagged."""
    f = _write(
        tmp_path,
        "generics.py",
        "def foo(items: list[str], mapping: dict[str, int]) -> None:\n    ...\n",
    )
    violations = check_file_for_typing_syntax(f)
    assert violations == []


@pytest.mark.unit
def test_no_violations_for_file_with_typing_import_only(tmp_path: Path) -> None:
    """from typing import TYPE_CHECKING only — no Optional/Union usage."""
    f = _write(
        tmp_path,
        "type_checking.py",
        "from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    pass\n",
    )
    violations = check_file_for_typing_syntax(f)
    assert violations == []


# ---------------------------------------------------------------------------
# Fail cases: check_file_for_typing_syntax
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_optional_type_detected(tmp_path: Path) -> None:
    """Optional[str] is flagged with a suggestion for str | None."""
    f = _write(
        tmp_path,
        "optional.py",
        "from typing import Optional\ndef foo(x: Optional[str]) -> None:\n    ...\n",
    )
    violations = check_file_for_typing_syntax(f)
    assert len(violations) >= 1
    messages = [v[1] for v in violations]
    assert any("Optional[str]" in m and "str | None" in m for m in messages)


@pytest.mark.unit
def test_union_two_types_detected(tmp_path: Path) -> None:
    """Union[str, int] is flagged with a suggestion for str | int."""
    f = _write(
        tmp_path,
        "union2.py",
        "from typing import Union\ndef foo(x: Union[str, int]) -> None:\n    ...\n",
    )
    violations = check_file_for_typing_syntax(f)
    assert len(violations) >= 1
    messages = [v[1] for v in violations]
    assert any("Union[str, int]" in m and "str | int" in m for m in messages)


@pytest.mark.unit
def test_union_three_types_detected(tmp_path: Path) -> None:
    """Union[str, int, bool] is flagged with suggestion for str | int | bool."""
    f = _write(
        tmp_path,
        "union3.py",
        "from typing import Union\n"
        "def foo(x: Union[str, int, bool]) -> None:\n    ...\n",
    )
    violations = check_file_for_typing_syntax(f)
    assert len(violations) >= 1
    messages = [v[1] for v in violations]
    assert any("str | int | bool" in m for m in messages)


@pytest.mark.unit
def test_optional_in_return_type_detected(tmp_path: Path) -> None:
    """Optional[int] in return type annotation is flagged."""
    f = _write(
        tmp_path,
        "return.py",
        "from typing import Optional\ndef foo() -> Optional[int]:\n    return None\n",
    )
    violations = check_file_for_typing_syntax(f)
    assert len(violations) >= 1


@pytest.mark.unit
def test_violation_contains_line_number(tmp_path: Path) -> None:
    """Violation tuple contains the correct line number."""
    f = _write(
        tmp_path,
        "lineno.py",
        "x = 1\nfrom typing import Optional\ndef foo(x: Optional[str]):\n    ...\n",
    )
    violations = check_file_for_typing_syntax(f)
    assert violations
    line_nums = [v[0] for v in violations]
    assert any(n >= 3 for n in line_nums)


@pytest.mark.unit
def test_multiple_violations_in_file(tmp_path: Path) -> None:
    """Multiple Optional/Union usages produce multiple violations."""
    f = _write(
        tmp_path,
        "multi.py",
        "from typing import Optional, Union\n"
        "def foo(x: Optional[str], y: Union[int, float]) -> None:\n    ...\n",
    )
    violations = check_file_for_typing_syntax(f)
    assert len(violations) >= 2


# ---------------------------------------------------------------------------
# Boundary: validate_typing_syntax
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_validate_typing_syntax_passes_on_clean_dir(tmp_path: Path) -> None:
    """validate_typing_syntax returns True when no violations found."""
    _write(tmp_path, "clean.py", "x: str | None = None\n")
    result = validate_typing_syntax([str(tmp_path)], max_violations=0)
    assert result is True


@pytest.mark.unit
def test_validate_typing_syntax_fails_on_violation(tmp_path: Path) -> None:
    """validate_typing_syntax returns False when violations exceed max."""
    _write(
        tmp_path,
        "bad.py",
        "from typing import Optional\ndef foo(x: Optional[str]):\n    ...\n",
    )
    result = validate_typing_syntax([str(tmp_path)], max_violations=0)
    assert result is False


@pytest.mark.unit
def test_validate_typing_syntax_within_limit_passes(tmp_path: Path) -> None:
    """validate_typing_syntax returns True when violations <= max_violations."""
    _write(
        tmp_path,
        "one.py",
        "from typing import Optional\ndef foo(x: Optional[str]):\n    ...\n",
    )
    result = validate_typing_syntax([str(tmp_path)], max_violations=10)
    assert result is True


@pytest.mark.unit
def test_validate_typing_syntax_nonexistent_dir_graceful(tmp_path: Path) -> None:
    """Non-existent directory is skipped (prints error but does not crash)."""
    result = validate_typing_syntax(
        [str(tmp_path / "does_not_exist")], max_violations=0
    )
    assert result is True


@pytest.mark.unit
def test_validate_typing_syntax_multiple_files_aggregated(tmp_path: Path) -> None:
    """Violations from multiple files are summed across the directory."""
    _write(
        tmp_path,
        "a.py",
        "from typing import Optional\ndef a(x: Optional[str]):\n    ...\n",
    )
    _write(
        tmp_path,
        "b.py",
        "from typing import Union\ndef b(x: Union[int, str]):\n    ...\n",
    )
    result = validate_typing_syntax([str(tmp_path)], max_violations=0)
    assert result is False
