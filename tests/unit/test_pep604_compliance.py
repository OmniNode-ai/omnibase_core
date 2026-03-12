# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""PEP 604 type annotation compliance verification tests (OMN-4813).

Verifies that the omnibase_core codebase uses modern X | Y syntax
instead of Optional[X] or Union[X, Y] in actual type annotations.

The UP ruleset (including UP007) is already enabled in ruff config.
This test provides a runtime regression guard.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

SRC_DIR = Path(__file__).parent.parent.parent / "src"

# Patterns that indicate pre-PEP 604 usage in actual type annotations
# (not in comments or string literals)
_OPTIONAL_PATTERN = re.compile(r"\bOptional\[")
_UNION_PATTERN = re.compile(r"\bUnion\[")


def _find_type_annotation_violations(src_dir: Path) -> list[tuple[Path, int, str]]:
    """Find Optional[X] or Union[X, Y] in actual type annotations (not comments)."""
    violations: list[tuple[Path, int, str]] = []

    for py_file in src_dir.rglob("*.py"):
        try:
            source = py_file.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(py_file))
        except SyntaxError:
            continue

        lines = source.splitlines()

        for node in ast.walk(tree):
            # Check function annotations
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                for arg in (
                    node.args.args + node.args.posonlyargs + node.args.kwonlyargs
                ):
                    if arg.annotation is not None:
                        ann_src = ast.unparse(arg.annotation)
                        if _OPTIONAL_PATTERN.search(ann_src) or _UNION_PATTERN.search(
                            ann_src
                        ):
                            violations.append((py_file, arg.annotation.lineno, ann_src))
                if node.returns is not None:
                    ret_src = ast.unparse(node.returns)
                    if _OPTIONAL_PATTERN.search(ret_src) or _UNION_PATTERN.search(
                        ret_src
                    ):
                        violations.append((py_file, node.returns.lineno, ret_src))
            # Check variable annotations
            elif isinstance(node, ast.AnnAssign) and node.annotation is not None:
                ann_src = ast.unparse(node.annotation)
                if _OPTIONAL_PATTERN.search(ann_src) or _UNION_PATTERN.search(ann_src):
                    violations.append((py_file, node.annotation.lineno, ann_src))

    return violations


class TestPEP604Compliance:
    """Verify omnibase_core uses PEP 604 X | Y syntax throughout."""

    @pytest.mark.unit
    def test_no_optional_in_type_annotations(self) -> None:
        """No Optional[X] in actual type annotations in src/."""
        violations = _find_type_annotation_violations(SRC_DIR)
        optional_violations = [
            (f, ln, s) for f, ln, s in violations if _OPTIONAL_PATTERN.search(s)
        ]
        assert not optional_violations, (
            f"Found {len(optional_violations)} Optional[X] annotation(s). "
            "Use X | None instead (PEP 604). Files:\n"
            + "\n".join(f"  {f}:{ln}: {s}" for f, ln, s in optional_violations[:10])
        )

    @pytest.mark.unit
    def test_no_union_in_type_annotations(self) -> None:
        """No Union[X, Y] in actual type annotations in src/."""
        violations = _find_type_annotation_violations(SRC_DIR)
        union_violations = [
            (f, ln, s) for f, ln, s in violations if _UNION_PATTERN.search(s)
        ]
        assert not union_violations, (
            f"Found {len(union_violations)} Union[X, Y] annotation(s). "
            "Use X | Y instead (PEP 604). Files:\n"
            + "\n".join(f"  {f}:{ln}: {s}" for f, ln, s in union_violations[:10])
        )

    @pytest.mark.unit
    def test_ruff_up_ruleset_enabled(self) -> None:
        """Confirm UP ruleset (which includes UP007) is enabled in ruff config."""
        pyproject = Path(__file__).parent.parent.parent / "pyproject.toml"
        content = pyproject.read_text(encoding="utf-8")
        assert '"UP"' in content, (
            "UP ruleset not found in ruff select list. "
            "Add 'UP' to [tool.ruff.lint] select to enforce PEP 604."
        )
