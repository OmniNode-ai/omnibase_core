# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
ValidatorTransportImport — ban transport/I/O library imports in node code.

Enforces the ARCH-002 architectural boundary: ONEX nodes never touch transport
or I/O libraries directly. Runtime owns all Kafka/HTTP/DB plumbing; nodes declare
intent via contracts. This is the canonical, fleet-wide replacement for the
per-repo ``validate_no_transport_imports.py`` scripts (OMN-13283 consolidation).

The check is AST-based: imports inside ``TYPE_CHECKING`` blocks are allowed (they
create no runtime dependency). Both ``import X`` and ``from X import Y`` are
covered, including dotted submodules and aliasing of ``typing``/``TYPE_CHECKING``.

Usage Examples:
    CLI — check staged files (pre-commit mode)::

        python -m omnibase_core.validation.validator_transport_import file1.py file2.py

    CLI — check a directory recursively::

        python -m omnibase_core.validation.validator_transport_import src/

Suppression:
    Add ``# transport-import-ok: <reason>`` anywhere on the import line to suppress
    a single violation::

        >>> import httpx  # transport-import-ok: infra boundary file, not a node

Schema Version:
    v1.0.0 - Initial port from omniintelligence/omnimemory scripts (OMN-13283).
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path
from typing import Final

from pydantic import BaseModel, ConfigDict

# ---------------------------------------------------------------------------
# Banned modules
# ---------------------------------------------------------------------------

# Transport/I/O modules that must not be imported at runtime in node code.
# Union of the omniintelligence + omnimemory banned sets (OMN-13283 port).
BANNED_MODULES: Final[frozenset[str]] = frozenset(
    {
        # HTTP clients
        "aiohttp",
        "httpx",
        "requests",
        "urllib3",
        # Kafka clients
        "kafka",
        "aiokafka",
        "confluent_kafka",
        # Redis clients
        "redis",
        "aioredis",
        # Database clients
        "asyncpg",
        "psycopg2",
        "psycopg",
        "aiomysql",
        # Async file I/O
        "aiofiles",
        # Message queues
        "pika",
        "aio_pika",
        "kombu",
        "celery",
        # gRPC (import name is "grpc", not the PyPI name "grpcio")
        "grpc",
        # WebSocket
        "websockets",
        "wsproto",
    }
)

_SUPPRESSION_MARKER: Final[str] = "transport-import-ok"

# Directories to skip during recursive scan.
_SKIP_DIRS: Final[frozenset[str]] = frozenset(
    {
        ".git",
        "__pycache__",
        "node_modules",
        ".tox",
        ".venv",
        "venv",
        ".env",
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


class ModelTransportImportViolation(BaseModel):
    """A single banned transport-import violation."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    file: Path
    line: int
    module_name: str
    context: str  # the offending source line (stripped)

    def __str__(self) -> str:
        return f"{self.file}:{self.line}: banned transport import: {self.module_name}"


# ---------------------------------------------------------------------------
# AST visitor
# ---------------------------------------------------------------------------


class _TransportImportChecker(ast.NodeVisitor):
    """Detect banned transport imports outside ``TYPE_CHECKING`` blocks."""

    def __init__(self, source_lines: list[str], file_path: Path) -> None:
        self.source_lines = source_lines
        self.file_path = file_path
        self.violations: list[ModelTransportImportViolation] = []
        self._in_type_checking_block = False
        self._type_checking_module_aliases: set[str] = set()
        self._type_checking_constant_aliases: set[str] = set()

    def _source_line(self, lineno: int) -> str:
        if 1 <= lineno <= len(self.source_lines):
            return self.source_lines[lineno - 1].strip()
        return ""

    @staticmethod
    def _root_module(module_name: str) -> str:
        return module_name.split(".", maxsplit=1)[0]

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

    def _record(self, lineno: int, module_name: str) -> None:
        context = self._source_line(lineno)
        if _SUPPRESSION_MARKER in context:
            return
        self.violations.append(
            ModelTransportImportViolation(
                file=self.file_path,
                line=lineno,
                module_name=module_name,
                context=context,
            )
        )

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            if alias.name == "typing" and alias.asname:
                self._type_checking_module_aliases.add(alias.asname)
        if not self._in_type_checking_block:
            for alias in node.names:
                root = self._root_module(alias.name)
                if root in BANNED_MODULES:
                    self._record(node.lineno, root)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.level > 0 or node.module is None:
            self.generic_visit(node)
            return
        for alias in node.names:
            if alias.name == "TYPE_CHECKING" and alias.asname:
                self._type_checking_constant_aliases.add(alias.asname)
        if not self._in_type_checking_block:
            root = self._root_module(node.module)
            if root in BANNED_MODULES:
                self._record(node.lineno, root)
        self.generic_visit(node)

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


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------


class ValidatorTransportImport(BaseModel):
    """Detect banned transport/I/O imports in node code.

    Stateless: each call returns violations without mutating instance state.
    Thread-safe (no mutable state on the instance).
    """

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    def check_file(self, path: Path) -> list[ModelTransportImportViolation]:
        """Check a single Python file. Returns violations found."""
        if path.suffix != ".py":
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
            # A syntax error is not a transport violation; other gates own it.
            return []
        checker = _TransportImportChecker(source.splitlines(), path)
        checker.visit(tree)
        return checker.violations

    def check_paths(self, paths: list[Path]) -> list[ModelTransportImportViolation]:
        """Check a list of files or directories recursively."""
        all_violations: list[ModelTransportImportViolation] = []
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
                    f"Warning: validate-no-transport-imports: skipping "
                    f"non-existent path: {p}",
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
        prog="validate-no-transport-imports",
        description=(
            "Ban transport/I/O library imports in ONEX node code (ARCH-002). "
            "TYPE_CHECKING-guarded imports are allowed."
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
        help="Suppress per-violation context lines and summary",
    )
    parsed = parser.parse_args(argv)

    validator = ValidatorTransportImport()
    violations = validator.check_paths(parsed.paths)

    for v in violations:
        print(str(v))
        if not parsed.quiet:
            print(f"  {v.context}")

    if not parsed.quiet:
        if violations:
            print(
                f"\n{len(violations)} transport-import violation(s). "
                f"Nodes must not import transport/I/O libraries at runtime "
                f"(ARCH-002). Use a protocol + DI, a TYPE_CHECKING guard, or add "
                f"`# {_SUPPRESSION_MARKER}: <reason>` to suppress a boundary file."
            )
        else:
            print("No transport-import violations found.")

    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
