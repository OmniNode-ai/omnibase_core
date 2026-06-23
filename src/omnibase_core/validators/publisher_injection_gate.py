# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Publisher injection gate (OMN-12881).

Enforces: auto-wired handler/node classes that call ``self._xxx.publish(...)``
(side-emit events) MUST declare ``event_bus`` in their ``__init__`` so the
runtime can inject the bus. Without the injection parameter the runtime silently
skips injection and the handler tries to call ``.publish()`` on ``None`` at
runtime.

Rule
----
``missing_publisher_injection`` — a handler/node class whose method body
contains a ``self.<attr>.publish(...)`` call does not have an ``event_bus``
parameter in its ``__init__``.  The ``event_bus`` parameter may be positional,
keyword, or keyword-only; it just needs to be present so the runtime wires it.

Scanned targets
---------------
- ``**/handlers/handler_*.py``
- ``**/nodes/**/node.py``   (direct node implementation files)
- ``**/nodes/**/handler.py`` (canonical handler file inside node packages)

Suppression
-----------
Add ``# publisher-injection-ok: <reason>`` on the ``class`` line or the
``__init__`` line to suppress an individual class.

Usage::

    python -m omnibase_core.validators.publisher_injection_gate src/

"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

from omnibase_core.models.validation.model_publisher_injection_finding import (
    ModelPublisherInjectionFinding,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SUPPRESSION_MARKER = "publisher-injection-ok:"

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


def _is_node_handler_file(path: Path) -> bool:
    """True if file is named handler.py or node.py inside a nodes/ directory tree."""
    parts = path.parts
    return "nodes" in parts and path.name in {"handler.py", "node.py"}


def _is_target_file(path: Path) -> bool:
    return _is_handler_file(path) or _is_node_handler_file(path)


def _is_excluded(path: Path) -> bool:
    return any(part in _EXCLUDED_PATH_PARTS for part in path.parts)


# ---------------------------------------------------------------------------
# AST helpers
# ---------------------------------------------------------------------------


def _class_name_looks_like_handler(cls_name: str) -> bool:
    """True if the class name suggests a handler or node implementation."""
    lower = cls_name.lower()
    return (
        "handler" in lower
        or "node" in lower
        or "reducer" in lower
        or "orchestrator" in lower
        or "effect" in lower
        or "compute" in lower
    )


def _init_has_event_bus_param(cls: ast.ClassDef) -> bool:
    """True if the class ``__init__`` declares an ``event_bus`` parameter."""
    for item in cls.body:
        if not (isinstance(item, ast.FunctionDef) and item.name == "__init__"):
            continue
        args = item.args
        all_params = [a.arg for a in args.args]
        if "event_bus" in all_params:
            return True
        # keyword-only (after *)
        kw_only = [a.arg for a in args.kwonlyargs]
        if "event_bus" in kw_only:
            return True
    return False


def _class_side_emits(cls: ast.ClassDef) -> int | None:
    """Return the first line number of a ``self.<attr>.publish(...)`` call in any
    method of *cls*, or ``None`` if no such call exists.

    Only fires on calls where the receiver chain starts with ``self`` — plain
    function calls or top-level ``bus.publish(...)`` are not flagged.
    """
    for item in cls.body:
        if not isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if item.name == "__init__":
            # __init__-level publish is a construction pattern; the DI gate
            # already covers it.  Side-emission means emitting DURING handle().
            continue
        for node in ast.walk(item):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            # Must be `<something>.publish`
            if not isinstance(func, ast.Attribute):
                continue
            if func.attr != "publish":
                continue
            # The receiver must start with `self` — either `self.<attr>`
            # (one-level) or `self.<attr>.<attr>` (nested accessor).
            receiver: ast.expr = func.value
            while isinstance(receiver, ast.Attribute):
                receiver = receiver.value
            if isinstance(receiver, ast.Name) and receiver.id == "self":
                return node.lineno
    return None


# ---------------------------------------------------------------------------
# File-level dispatch
# ---------------------------------------------------------------------------


def _has_suppression(lines: list[str], lineno: int) -> bool:
    """True if the given line (1-indexed) contains the suppression marker."""
    if 1 <= lineno <= len(lines):
        return SUPPRESSION_MARKER in lines[lineno - 1]
    return False


def validate_file(
    path: Path,
) -> list[ModelPublisherInjectionFinding]:
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
    findings: list[ModelPublisherInjectionFinding] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        if not _class_name_looks_like_handler(node.name):
            continue

        # Check class line for suppression
        if _has_suppression(lines, node.lineno):
            continue

        emit_line = _class_side_emits(node)
        if emit_line is None:
            continue  # no side-emission — nothing to enforce

        if _init_has_event_bus_param(node):
            continue  # injection declared — pass

        # Suppression on any __init__ line
        for item in node.body:
            if isinstance(item, ast.FunctionDef) and item.name == "__init__":
                if _has_suppression(lines, item.lineno):
                    break
        else:
            # No suppression found — emit finding
            findings.append(
                ModelPublisherInjectionFinding(
                    path=path,
                    line=node.lineno,
                    column=node.col_offset,
                    rule="missing_publisher_injection",
                    message=(
                        f"class {node.name!r} calls self.<attr>.publish() at line "
                        f"{emit_line} but does not declare 'event_bus' in __init__ — "
                        "add 'event_bus' parameter so the runtime can inject it; "
                        "without it the handler will fail at runtime with AttributeError"
                    ),
                )
            )

    return findings


def validate_paths(
    paths: list[Path],
) -> list[ModelPublisherInjectionFinding]:
    """Validate all Python files under the given paths."""
    findings: list[ModelPublisherInjectionFinding] = []
    for path in paths:
        if path.is_file() and path.suffix == ".py":
            findings.extend(validate_file(path))
        elif path.is_dir():
            for py_file in sorted(path.rglob("*.py")):
                if not _is_excluded(py_file):
                    findings.extend(validate_file(py_file))
    return findings


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

_VALIDATOR_NAME = "publisher_injection_gate"


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for publisher injection gate validator."""
    parser = argparse.ArgumentParser(
        description=(
            "Publisher injection gate (OMN-12881): side-emitting handlers must "
            "declare event_bus in __init__ for runtime injection."
        ),
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        default=list(_DEFAULT_SCAN_ROOTS),
        help="Python files or directories to scan.",
    )
    args = parser.parse_args(argv)

    findings = validate_paths(args.paths)

    if not findings:
        return 0

    sys.stderr.write(f"{_VALIDATOR_NAME}: {len(findings)} finding(s):\n")
    for f in findings:
        sys.stderr.write(f"  {f.format()}\n")
    sys.stderr.write(
        "\nSide-emitting handlers must declare 'event_bus' in __init__.\n"
        "The runtime auto-injects it when present; omitting it leaves the bus\n"
        "as None and the handler crashes at the first .publish() call.\n"
        "Suppress individual classes with:  # publisher-injection-ok: <reason>\n"
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())  # error-ok: CLI entry point requires SystemExit
