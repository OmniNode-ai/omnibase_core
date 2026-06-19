# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
ValidatorNodePurity — enforce the "pure compute / no I/O" node invariant.

AST-based static analysis that flags forbidden I/O patterns inside ONEX node
code. This is the canonical, fleet-wide replacement for the per-repo
``io_audit`` packages (OMN-13283 consolidation). It enforces three rules:

- ``net-client``  — importing network/DB client libraries (httpx, asyncpg, ...)
- ``env-access``  — reading/mutating environment variables (os.getenv, os.environ[...])
- ``file-io``     — file system operations (open(), Path.read_text(), FileHandler)

Only files whose path contains a ``nodes`` directory segment are scanned: node
purity is a node-scoped invariant. Imports inside ``TYPE_CHECKING`` blocks are
allowed (no runtime dependency).

Usage Examples:
    CLI — check staged files (pre-commit mode)::

        python -m omnibase_core.validation.validator_node_purity node_a.py node_b.py

    CLI — check a directory recursively::

        python -m omnibase_core.validation.validator_node_purity src/

Suppression:
    Add ``# node-purity-ok: <reason>`` anywhere on the offending line::

        value = os.getenv("X")  # node-purity-ok: bootstrap shim, tracked in OMN-1234

Schema Version:
    v1.0.0 - Initial port from omniintelligence/omnimemory io_audit (OMN-13283).
"""

from __future__ import annotations

import ast
import sys
from enum import Enum
from pathlib import Path
from typing import Final

from pydantic import BaseModel, ConfigDict

# ---------------------------------------------------------------------------
# Rule taxonomy
# ---------------------------------------------------------------------------


class EnumNodePurityRule(Enum):
    """Node-purity rule identifiers."""

    NET_CLIENT = "net-client"
    ENV_ACCESS = "env-access"
    FILE_IO = "file-io"


_REMEDIATION: Final[dict[EnumNodePurityRule, str]] = {
    EnumNodePurityRule.NET_CLIENT: (
        "Move to an EFFECT node or inject the client via the DI container."
    ),
    EnumNodePurityRule.ENV_ACCESS: (
        "Resolve configuration from the contract; do not read env vars in a node."
    ),
    EnumNodePurityRule.FILE_IO: (
        "Move file I/O to an EFFECT node or pass file content as an input parameter."
    ),
}

# Forbidden network/DB client imports (exact or dotted-prefix match).
FORBIDDEN_IMPORTS: Final[frozenset[str]] = frozenset(
    {
        "aiokafka",
        "confluent_kafka",
        "kafka",
        "asyncpg",
        "httpx",
        "aiohttp",
        "aiofiles",
        "redis",
        "aioredis",
        "psycopg2",
        "psycopg",
    }
)

PATHLIB_IO_METHODS: Final[frozenset[str]] = frozenset(
    {"read_text", "write_text", "read_bytes", "write_bytes", "open"}
)

PATHLIB_VARIABLE_PATTERNS: Final[frozenset[str]] = frozenset(
    {
        "path",
        "file_path",
        "filepath",
        "dir_path",
        "dirpath",
        "p",
        "fp",
        "source_path",
        "target_path",
        "config_path",
    }
)

LOGGING_FILE_HANDLERS: Final[frozenset[str]] = frozenset(
    {
        "FileHandler",
        "RotatingFileHandler",
        "TimedRotatingFileHandler",
        "WatchedFileHandler",
    }
)

ENVIRON_MUTATION_METHODS: Final[frozenset[str]] = frozenset(
    {"get", "pop", "setdefault", "clear", "update"}
)

_SUPPRESSION_MARKER: Final[str] = "node-purity-ok"

# Path segment that scopes this validator: only node code is checked.
_NODE_SEGMENT: Final[str] = "nodes"

_SKIP_DIRS: Final[frozenset[str]] = frozenset(
    {
        ".git",
        "__pycache__",
        "node_modules",
        ".tox",
        ".venv",
        "venv",
        "build",
        "dist",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".eggs",
    }
)

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


class ModelNodePurityViolation(BaseModel):
    """A single node-purity violation."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    file: Path
    line: int
    column: int
    rule: EnumNodePurityRule
    message: str

    def __str__(self) -> str:
        return f"{self.file}:{self.line}: {self.rule.value}: {self.message}"


# ---------------------------------------------------------------------------
# AST visitor
# ---------------------------------------------------------------------------


class _NodePurityVisitor(ast.NodeVisitor):
    """AST visitor detecting I/O violations in node code."""

    def __init__(self, file_path: Path, source_lines: list[str]) -> None:
        self.file_path = file_path
        self.source_lines = source_lines
        self.violations: list[ModelNodePurityViolation] = []
        self._imported_names: dict[str, str] = {}
        self._in_type_checking_block = False
        self._type_checking_module_aliases: set[str] = set()
        self._type_checking_constant_aliases: set[str] = set()

    def _suppressed(self, lineno: int) -> bool:
        if 1 <= lineno <= len(self.source_lines):
            return _SUPPRESSION_MARKER in self.source_lines[lineno - 1]
        return False

    def _add(self, node: ast.AST, rule: EnumNodePurityRule, message: str) -> None:
        line = getattr(node, "lineno", 0)
        if self._suppressed(line):
            return
        self.violations.append(
            ModelNodePurityViolation(
                file=self.file_path,
                line=line,
                column=getattr(node, "col_offset", 0),
                rule=rule,
                message=message,
            )
        )

    def _is_type_checking_guard(self, node: ast.If) -> bool:
        test = node.test
        if isinstance(test, ast.Name) and (
            test.id == "TYPE_CHECKING"
            or test.id in self._type_checking_constant_aliases
        ):
            return True
        if isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING":
            if isinstance(test.value, ast.Name):
                return (
                    test.value.id == "typing"
                    or test.value.id in self._type_checking_module_aliases
                )
            return False
        return False

    def visit_If(self, node: ast.If) -> None:
        if self._is_type_checking_guard(node):
            old_state = self._in_type_checking_block
            self._in_type_checking_block = True
            for child in node.body:
                self.visit(child)
            self._in_type_checking_block = old_state
            for child in node.orelse:
                self.visit(child)
        else:
            self.generic_visit(node)

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            module = alias.name
            self._imported_names[alias.asname or alias.name] = module
            if module == "typing" and alias.asname:
                self._type_checking_module_aliases.add(alias.asname)
            if self._in_type_checking_block:
                continue
            for forbidden in FORBIDDEN_IMPORTS:
                if module == forbidden or module.startswith(f"{forbidden}."):
                    self._add(
                        node,
                        EnumNodePurityRule.NET_CLIENT,
                        f"Forbidden import: {module}",
                    )
                    break
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = node.module or ""
        for alias in node.names:
            self._imported_names[alias.asname or alias.name] = f"{module}.{alias.name}"
            if alias.name == "TYPE_CHECKING" and alias.asname:
                self._type_checking_constant_aliases.add(alias.asname)
        if self._in_type_checking_block:
            self.generic_visit(node)
            return
        for forbidden in FORBIDDEN_IMPORTS:
            if module == forbidden or module.startswith(f"{forbidden}."):
                self._add(
                    node,
                    EnumNodePurityRule.NET_CLIENT,
                    f"Forbidden import: from {module}",
                )
                self.generic_visit(node)
                return
        if module in ("logging", "logging.handlers"):
            for alias in node.names:
                if alias.name in LOGGING_FILE_HANDLERS:
                    self._add(
                        node,
                        EnumNodePurityRule.FILE_IO,
                        f"Forbidden import: {alias.name} from {module}",
                    )
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        self._check_open(node)
        self._check_env_access(node)
        self._check_pathlib_io(node)
        self._check_logging_handler(node)
        self.generic_visit(node)

    def _check_open(self, node: ast.Call) -> None:
        func = node.func
        if isinstance(func, ast.Name) and func.id == "open":
            self._add(node, EnumNodePurityRule.FILE_IO, "Forbidden call: open()")
            return
        if isinstance(func, ast.Attribute) and func.attr == "open":
            if isinstance(func.value, ast.Name) and func.value.id == "io":
                self._add(node, EnumNodePurityRule.FILE_IO, "Forbidden call: io.open()")

    def _check_env_access(self, node: ast.Call) -> None:
        func = node.func
        if not isinstance(func, ast.Attribute):
            return
        if isinstance(func.value, ast.Name) and func.value.id == "os":
            if func.attr == "getenv":
                self._add(
                    node, EnumNodePurityRule.ENV_ACCESS, "Forbidden call: os.getenv()"
                )
            elif func.attr == "putenv":
                self._add(
                    node, EnumNodePurityRule.ENV_ACCESS, "Forbidden call: os.putenv()"
                )
        elif (
            isinstance(func.value, ast.Attribute)
            and isinstance(func.value.value, ast.Name)
            and func.value.value.id == "os"
            and func.value.attr == "environ"
            and func.attr in ENVIRON_MUTATION_METHODS
        ):
            self._add(
                node,
                EnumNodePurityRule.ENV_ACCESS,
                f"Forbidden call: os.environ.{func.attr}()",
            )

    def _has_pathlib_import(self) -> bool:
        for alias, module in self._imported_names.items():
            if module == "pathlib" or module.startswith("pathlib."):
                return True
            if alias in {"Path", "pathlib"}:
                return True
        return False

    def _is_likely_path_object(self, node: ast.expr) -> bool:
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == "Path":
                return True
        if isinstance(node, ast.Name):
            name = node.id.lower()
            return name in PATHLIB_VARIABLE_PATTERNS or name.endswith(("_path", "path"))
        if isinstance(node, ast.Attribute):
            attr = node.attr.lower()
            return attr in PATHLIB_VARIABLE_PATTERNS or attr.endswith(("_path", "path"))
        return False

    def _check_pathlib_io(self, node: ast.Call) -> None:
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr in PATHLIB_IO_METHODS:
            if not self._has_pathlib_import():
                return
            if not self._is_likely_path_object(func.value):
                return
            self._add(
                node, EnumNodePurityRule.FILE_IO, f"Forbidden call: Path.{func.attr}()"
            )

    def _check_logging_handler(self, node: ast.Call) -> None:
        func = node.func
        if isinstance(func, ast.Name) and func.id in LOGGING_FILE_HANDLERS:
            self._add(node, EnumNodePurityRule.FILE_IO, f"Forbidden call: {func.id}()")
        elif isinstance(func, ast.Attribute) and func.attr in LOGGING_FILE_HANDLERS:
            self._add(
                node, EnumNodePurityRule.FILE_IO, f"Forbidden call: {func.attr}()"
            )

    def visit_Subscript(self, node: ast.Subscript) -> None:
        value = node.value
        if (
            isinstance(value, ast.Attribute)
            and isinstance(value.value, ast.Name)
            and value.value.id == "os"
            and value.attr == "environ"
        ):
            self._add(
                node, EnumNodePurityRule.ENV_ACCESS, "Forbidden access: os.environ[...]"
            )
        self.generic_visit(node)


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------


def _is_node_scoped(path: Path) -> bool:
    """True if the file lives under a ``nodes`` directory segment."""
    return _NODE_SEGMENT in path.parts


class ValidatorNodePurity(BaseModel):
    """Enforce node purity (no net-client / env-access / file-io in nodes).

    Stateless and thread-safe: no mutable instance state.
    """

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    def check_file(self, path: Path) -> list[ModelNodePurityViolation]:
        """Check a single Python file (skips non-node files)."""
        if path.suffix != ".py" or not _is_node_scoped(path):
            return []
        try:
            source = path.read_text(encoding="utf-8")
        except (OSError, PermissionError, UnicodeDecodeError):
            return []
        if not source.strip():
            return []
        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError:
            return []
        visitor = _NodePurityVisitor(path, source.splitlines())
        visitor.visit(tree)
        return visitor.violations

    def check_paths(self, paths: list[Path]) -> list[ModelNodePurityViolation]:
        """Check a list of files or directories recursively."""
        all_violations: list[ModelNodePurityViolation] = []
        for p in paths:
            if p.is_file():
                all_violations.extend(self.check_file(p))
            elif p.is_dir():
                for child in sorted(p.rglob("*.py")):
                    if any(part in _SKIP_DIRS for part in child.parts):
                        continue
                    if child.is_file():
                        all_violations.extend(self.check_file(child))
            else:
                print(
                    f"Warning: node-purity: skipping non-existent path: {p}",
                    file=sys.stderr,
                )
        return all_violations


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint. Accepts files (pre-commit staged mode) or directories.

    Exit codes:
        0 — no violations
        1 — violations found
    """
    import argparse

    parser = argparse.ArgumentParser(
        prog="node-purity",
        description=(
            "Enforce the pure-compute / no-I/O invariant in ONEX node code. "
            "Only files under a 'nodes' directory are checked."
        ),
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        default=[Path()],
        help="Files or directories to check (default: current directory)",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress per-violation hint lines and summary",
    )
    parsed = parser.parse_args(argv)

    validator = ValidatorNodePurity()
    violations = validator.check_paths(parsed.paths)

    for v in violations:
        print(str(v))
        if not parsed.quiet:
            hint = _REMEDIATION.get(v.rule, "")
            if hint:
                print(f"  -> Hint: {hint}")

    if not parsed.quiet:
        if violations:
            print(
                f"\n{len(violations)} node-purity violation(s). Nodes must be "
                f"pure (no network/DB clients, no env reads, no file I/O). Move "
                f"I/O to an EFFECT node, inject via DI, or add "
                f"`# {_SUPPRESSION_MARKER}: <reason>` to suppress a boundary line."
            )
        else:
            print("No node-purity violations found.")

    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
