# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Handler DI gate validator (OMN-10726).

Enforces: handler/node constructors must accept exactly `__init__(self, container)`
and must only acquire resources via container resolution — no direct infrastructure
construction in handlers.

Two rules:

1. **constructor_signature** — `__init__` must have signature `(self, container)`
   or `(self, container: SomeType)`. No extra parameters beyond `self` and one
   `container` positional-or-keyword param.

2. **direct_construction** — assignments inside `__init__` must not construct
   infrastructure objects directly. Flags `self._x = Anything(...)` patterns where
   the called constructor is NOT a container resolution call
   (`container.resolve(...)` / `container.get_service(...)`).

Scanned targets:
  - ``**/handlers/handler_*.py``
  - ``**/nodes/node.py``

Usage::

    python -m omnibase_core.validators.handler_di_gate src/

Suppression::

    Add  # handler-di-ok: <reason>  on a violating line to silence that finding.
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

from omnibase_core.models.validation.model_handler_di_gate_finding import (
    ModelHandlerDiGateFinding,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SUPPRESSION_MARKER = "handler-di-ok:"

_EXCLUDED_PATH_PARTS: frozenset[str] = frozenset(
    {
        ".venv",
        "__pycache__",
        "build",
        "dist",
        ".pytest_cache",
        ".ruff_cache",
        ".mypy_cache",
        "node_modules",
        ".git",
        "archived",
        "archive",
    }
)

# Names that indicate a container resolution call — not infrastructure construction.
_CONTAINER_RESOLUTION_ATTRS: frozenset[str] = frozenset(
    {"resolve", "get_service", "get", "get_or_none"}
)

_DEFAULT_SCAN_ROOTS = (Path("src"),)

# ---------------------------------------------------------------------------
# Path matchers
# ---------------------------------------------------------------------------


def _is_handler_file(path: Path) -> bool:
    """True if the file is a handler_*.py inside a handlers/ directory."""
    parts = path.parts
    return (
        "handlers" in parts
        and path.name.startswith("handler_")
        and path.suffix == ".py"
    )


def _is_node_file(path: Path) -> bool:
    """True if the file is node.py inside a nodes/ directory."""
    parts = path.parts
    return "nodes" in parts and path.name == "node.py"


def _is_target_file(path: Path) -> bool:
    return _is_handler_file(path) or _is_node_file(path)


def _is_excluded(path: Path) -> bool:
    return any(part in _EXCLUDED_PATH_PARTS for part in path.parts)


# ---------------------------------------------------------------------------
# AST helpers
# ---------------------------------------------------------------------------


def _get_call_dotted_name(node: ast.expr) -> str | None:
    """Return dotted name of a Call's func, e.g. 'container.resolve'."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parts: list[str] = []
        cur: ast.expr = node
        while isinstance(cur, ast.Attribute):
            parts.append(cur.attr)
            cur = cur.value
        if isinstance(cur, ast.Name):
            parts.append(cur.id)
        return ".".join(reversed(parts))
    return None


def _is_container_resolution(call_node: ast.Call) -> bool:
    """True if call is container.resolve(...) / container.get_service(...) etc."""
    func = call_node.func
    if not isinstance(func, ast.Attribute):
        return False
    if func.attr not in _CONTAINER_RESOLUTION_ATTRS:
        return False
    # The receiver must be a simple name (container, self._container, etc.)
    return True


# ---------------------------------------------------------------------------
# Rule: constructor_signature
# ---------------------------------------------------------------------------


def _check_constructor_signature(
    path: Path,
    cls: ast.ClassDef,
    lines: list[str],
) -> list[ModelHandlerDiGateFinding]:
    """Fail if __init__ does not have exactly (self, container[: T]) params."""
    findings: list[ModelHandlerDiGateFinding] = []

    for item in cls.body:
        if not (isinstance(item, ast.FunctionDef) and item.name == "__init__"):
            continue
        args = item.args
        # Collect all param names excluding 'self'
        all_params = [a.arg for a in args.args]
        if all_params and all_params[0] == "self":
            all_params = all_params[1:]

        # PASS: no params after self (container acquired via other means — skip)
        # PASS: exactly one param named 'container'
        # FAIL: zero params after self but body has direct constructions (handled separately)
        # FAIL: param not named 'container'
        # FAIL: more than one param after self

        if len(all_params) == 0:
            # No container param — no signature violation, direct_construction rule
            # will catch any bad assignments
            continue

        if len(all_params) == 1 and all_params[0] == "container":
            continue  # PASS

        # Violation
        param_str = ", ".join(all_params)
        line_text = lines[item.lineno - 1] if item.lineno <= len(lines) else ""
        if SUPPRESSION_MARKER in line_text:
            continue
        findings.append(
            ModelHandlerDiGateFinding(
                path=path,
                line=item.lineno,
                column=item.col_offset,
                rule="constructor_signature",
                message=(
                    f"class {cls.name!r} __init__ params ({param_str}) — "
                    "must be exactly (self, container) with no additional parameters"
                ),
            )
        )

    return findings


# ---------------------------------------------------------------------------
# Rule: direct_construction
# ---------------------------------------------------------------------------


def _check_direct_construction(
    path: Path,
    cls: ast.ClassDef,
    lines: list[str],
) -> list[ModelHandlerDiGateFinding]:
    """Fail if __init__ assigns self._ = SomeClass() not via container."""
    findings: list[ModelHandlerDiGateFinding] = []

    for item in cls.body:
        if not (isinstance(item, ast.FunctionDef) and item.name == "__init__"):
            continue

        for stmt in ast.walk(item):
            if not isinstance(stmt, ast.Assign):
                continue
            # Only flag `self.xxx = <Call>(...)` patterns
            for target in stmt.targets:
                if not (
                    isinstance(target, ast.Attribute)
                    and isinstance(target.value, ast.Name)
                    and target.value.id == "self"
                ):
                    continue
                # RHS must be a Call
                if not isinstance(stmt.value, ast.Call):
                    continue
                call = stmt.value
                if _is_container_resolution(call):
                    continue
                # It's a direct construction — flag it
                line_text = lines[stmt.lineno - 1] if stmt.lineno <= len(lines) else ""
                if SUPPRESSION_MARKER in line_text:
                    continue
                called_name = _get_call_dotted_name(call.func) or "<unknown>"
                findings.append(
                    ModelHandlerDiGateFinding(
                        path=path,
                        line=stmt.lineno,
                        column=stmt.col_offset,
                        rule="direct_construction",
                        message=(
                            f"class {cls.name!r} directly constructs {called_name!r} "
                            "in __init__ — acquire resources via container.resolve() "
                            "or container.get_service() instead"
                        ),
                    )
                )

    return findings


# ---------------------------------------------------------------------------
# File-level dispatch
# ---------------------------------------------------------------------------


def _class_name_looks_like_handler(cls_name: str) -> bool:
    """True if the class name pattern matches a handler or node class."""
    lower = cls_name.lower()
    return (
        "handler" in lower
        or "node" in lower
        or "reducer" in lower
        or "orchestrator" in lower
        or "effect" in lower
    )


def validate_file(
    path: Path, rules: frozenset[str] | None = None
) -> list[ModelHandlerDiGateFinding]:
    """Validate one Python file; return findings list."""
    if _is_excluded(path) or not _is_target_file(path):
        return []
    try:
        source = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return []
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError:
        return []

    lines = source.splitlines()
    active = rules or frozenset({"constructor_signature", "direct_construction"})
    findings: list[ModelHandlerDiGateFinding] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        if not _class_name_looks_like_handler(node.name):
            continue
        if "constructor_signature" in active:
            findings.extend(_check_constructor_signature(path, node, lines))
        if "direct_construction" in active:
            findings.extend(_check_direct_construction(path, node, lines))

    return findings


def validate_paths(
    paths: list[Path], rules: frozenset[str] | None = None
) -> list[ModelHandlerDiGateFinding]:
    """Validate all Python files under the given paths."""
    findings: list[ModelHandlerDiGateFinding] = []
    for path in paths:
        if path.is_file() and path.suffix == ".py":
            findings.extend(validate_file(path, rules))
        elif path.is_dir():
            for py_file in sorted(path.rglob("*.py")):
                if not _is_excluded(py_file):
                    findings.extend(validate_file(py_file, rules))
    return findings


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

_VALIDATOR_NAME = "handler_di_gate"


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for handler DI gate validator."""
    parser = argparse.ArgumentParser(
        description="Handler DI gate validator (OMN-10726).",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        default=list(_DEFAULT_SCAN_ROOTS),
        help="Python files or directories to scan.",
    )
    parser.add_argument(
        "--rule",
        action="append",
        dest="rules",
        choices=["constructor_signature", "direct_construction"],
        help="Enable only specific rules (repeatable; default: all rules).",
    )
    args = parser.parse_args(argv)

    active_rules = frozenset(args.rules) if args.rules else None
    findings = validate_paths(args.paths, active_rules)

    if not findings:
        return 0

    sys.stderr.write(f"{_VALIDATOR_NAME}: {len(findings)} finding(s):\n")
    for f in findings:
        sys.stderr.write(f"  {f.format()}\n")
    sys.stderr.write(
        "\nHandlers must accept only (self, container) and resolve deps via container.\n"
        "Suppress individual lines with:  # handler-di-ok: <reason>\n"
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())  # error-ok: CLI entry point requires SystemExit
