# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""AST visitor that detects database-driver imports.

Split out of ``handler.py`` (single-class-per-file convention, OMN-14656) so
the COMPUTE handler module contains exactly one class
(``NodeNoDbInOrchestratorCheckCompute``).

An ORCHESTRATOR node coordinates and emits; it must never perform database
I/O directly (``docs/architecture`` — "Orchestrators emit, never return";
database access belongs in a dedicated EFFECT node). The load-bearing,
deterministic signal for "this module does DB I/O" is an import of a database
driver / toolkit module: ``import sqlite3``, ``from sqlalchemy.orm import
Session``, ``import asyncpg``, etc. A module cannot call ``sqlite3.connect``
without importing ``sqlite3`` first, so import detection catches the violation
at its root with zero false negatives from call-site aliasing.

Suppress a proven-legitimate exception with a ``# db-io-ok`` annotation on the
import statement's opening line, its closing line, or the line immediately
preceding it.
"""

from __future__ import annotations

import ast
from typing import Final

from omnibase_core.models.validation.model_validation_finding import (
    ModelValidationFinding,
)

__all__ = ["VALIDATOR_ID", "FORBIDDEN_DB_MODULES", "DbIoImportVisitor"]

VALIDATOR_ID: Final[str] = "arch-no-db-in-orchestrator"

_SEVERITY_FAIL: Final = "FAIL"
_DB_IO_OK_MARKER: Final[str] = "# db-io-ok"
_REMEDIATION: Final[str] = (
    "Move database I/O into a dedicated EFFECT node and have the orchestrator "
    "emit an intent to it. Add '# db-io-ok' only for a proven-legitimate "
    "exception."
)

# Leading dotted segment of database drivers / toolkits an ORCHESTRATOR node
# must not import. Matched on the root module so 'sqlalchemy.orm' and
# 'psycopg.rows' both resolve to their forbidden root.
FORBIDDEN_DB_MODULES: Final[frozenset[str]] = frozenset(
    {
        "sqlite3",
        "aiosqlite",
        "psycopg",
        "psycopg2",
        "asyncpg",
        "sqlalchemy",
    }
)


def _forbidden_root(dotted_module: str) -> str | None:
    """Return the forbidden root module of ``dotted_module``, else None."""
    root = dotted_module.split(".", 1)[0]
    return root if root in FORBIDDEN_DB_MODULES else None


def _import_has_annotation(source_lines: list[str], node: ast.stmt) -> bool:
    """Check whether the import statement carries a ``# db-io-ok`` annotation.

    Checks the statement's opening line, closing line (``end_lineno``), and
    the line immediately preceding it — handling reformatted multi-line
    ``from x import (…)`` statements.
    """
    candidates = {node.lineno}
    end_lineno = getattr(node, "end_lineno", None)
    if end_lineno:
        candidates.add(end_lineno)
    candidates.add(node.lineno - 1)
    return any(
        0 < lineno <= len(source_lines) and _DB_IO_OK_MARKER in source_lines[lineno - 1]
        for lineno in candidates
    )


class DbIoImportVisitor(ast.NodeVisitor):
    """Walk an AST for forbidden database-driver imports."""

    def __init__(self, path: str, source_lines: list[str]) -> None:
        self._path = path
        self._source_lines = source_lines
        self.findings: list[ModelValidationFinding] = []

    def visit_Import(self, node: ast.Import) -> None:
        # `import sqlite3`, `import sqlalchemy.orm`, `import asyncpg as pg`
        for alias in node.names:
            module = _forbidden_root(alias.name)
            if module is not None:
                self._record(node, module)
                break
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        # `from sqlalchemy import create_engine`, `from psycopg.rows import ...`
        # node.module is None for relative imports (`from . import x`) — skip.
        if node.module is not None:
            module = _forbidden_root(node.module)
            if module is not None:
                self._record(node, module)
        self.generic_visit(node)

    def _record(self, node: ast.stmt, module: str) -> None:
        if _import_has_annotation(self._source_lines, node):
            return
        self.findings.append(
            ModelValidationFinding(
                validator_id=VALIDATOR_ID,
                severity=_SEVERITY_FAIL,
                location=f"{self._path}:{node.lineno}",
                message=(
                    f"{self._path}:{node.lineno}: DB access in ORCHESTRATOR node — "
                    f"database driver '{module}' imported in an orchestrator "
                    "package; orchestrators coordinate and emit, they must not "
                    "perform database I/O. Delegate DB access to an EFFECT node. "
                    "Add '# db-io-ok' to suppress for a proven-legitimate "
                    "exception."
                ),
                remediation=_REMEDIATION,
            )
        )
