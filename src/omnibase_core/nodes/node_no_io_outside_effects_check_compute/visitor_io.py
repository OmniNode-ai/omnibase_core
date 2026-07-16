# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""AST visitor that detects I/O surfaces forbidden outside EFFECT nodes.

Split out of ``handler.py`` (single-class-per-file convention, OMN-14656) so
the COMPUTE handler module contains exactly one class
(``NodeNoIoOutsideEffectsCheckCompute``).

**The invariant:** I/O and direct adapter/bus instantiation are permitted ONLY
in EFFECT nodes. Every ``.py`` module co-located with a non-EFFECT contract
(COMPUTE, REDUCER, ORCHESTRATOR) must be pure/deterministic. Database is only
one forbidden surface; this visitor covers the full set:

===================  ====================================================
Surface              AST detection
===================  ====================================================
Database             import root sqlite3/aiosqlite/psycopg/psycopg2/
                     asyncpg/sqlalchemy
Network / HTTP       import root httpx/requests/aiohttp/urllib3/socket, or
                     urllib.request / urllib.error
Subprocess           import ``subprocess``; ``subprocess.<verb>(...)``;
                     ``os.system``/``os.popen``/``os.exec*``/``os.spawn*``
Git                  git-lib import (git / pygit2), OR a subprocess/os call
                     whose argv[0] resolves to ``git`` (ALL verbs — purity
                     forbids all git, not only network verbs)
Linear               Linear SDK import (linear / linear_sdk / linear_api /
                     linear_client), OR any call carrying a ``linear.app``
                     URL string literal
Filesystem (write)   ``open(..., "w"|"a"|"x"|"+")``; ``os`` mutators
                     (remove/mkdir/unlink/...); ``shutil`` mutators
                     (copy/move/rmtree/...); ``pathlib.Path`` write methods
                     (write_text/write_bytes/mkdir/unlink/touch/rmtree/...)
Direct bus           construction of an event-bus class: KafkaProducer /
                     AIOKafka* / confluent_kafka.* / ``*EventBus(...)``
Direct adapter       construction of an infra adapter class: ``*Adapter(...)``
                     (inject via ``container.get_service(...)`` instead)
===================  ====================================================

Import-root detection catches a surface at its root — a module cannot call
``psycopg.connect`` without importing ``psycopg`` first — so it has zero
call-site-aliasing false negatives. Filesystem is scoped to *write/mutation*
operations (reads are common in legitimately-pure helpers); direct-adapter and
direct-bus instantiation, git and Linear are the genuinely new surfaces that
neither the OCC imperative guard nor the DB-only seed detected.

Suppress a proven-legitimate exception with an ``# io-ok:`` annotation on the
statement's opening line, its closing line, or the line immediately preceding
it.
"""

from __future__ import annotations

import ast
from typing import Final

from omnibase_core.models.validation.model_validation_finding import (
    ModelValidationFinding,
)

__all__ = [
    "VALIDATOR_ID",
    "FORBIDDEN_IMPORT_ROOTS",
    "IoSurfaceVisitor",
]

VALIDATOR_ID: Final[str] = "arch-no-io-outside-effects"

_SEVERITY_FAIL: Final = "FAIL"
_IO_OK_MARKER: Final[str] = "# io-ok"
_REMEDIATION: Final[str] = (
    "Only EFFECT nodes may perform I/O. Move the I/O into a dedicated EFFECT "
    "node (inject adapters/buses via container.get_service instead of "
    "constructing them). Add '# io-ok: <reason>' only for a proven-legitimate "
    "exception."
)

# --- Import-root classification -------------------------------------------
# Leading dotted segment → surface. Matched on the root so 'sqlalchemy.orm' and
# 'psycopg.rows' both resolve to their forbidden root.
_DB_ROOTS: Final[frozenset[str]] = frozenset(
    {"sqlite3", "aiosqlite", "psycopg", "psycopg2", "asyncpg", "sqlalchemy"}
)
_NET_ROOTS: Final[frozenset[str]] = frozenset(
    {"httpx", "requests", "aiohttp", "urllib3", "socket"}
)
# GitPython imports as ``git``; pygit2 as ``pygit2``.
_GIT_ROOTS: Final[frozenset[str]] = frozenset({"git", "pygit2"})
_LINEAR_ROOTS: Final[frozenset[str]] = frozenset(
    {"linear", "linear_sdk", "linear_api", "linear_client"}
)

# Convenience export: every import root that trips the gate (excludes the
# subpath-scoped urllib.request/error, handled explicitly below).
FORBIDDEN_IMPORT_ROOTS: Final[frozenset[str]] = (
    _DB_ROOTS | _NET_ROOTS | _GIT_ROOTS | _LINEAR_ROOTS | frozenset({"subprocess"})
)

# --- Call-surface classification ------------------------------------------
# Filesystem *mutation* operations only (reads are not flagged). 'replace' and
# 'rename' are intentionally EXCLUDED from the Path methods — ``str.replace`` is
# ubiquitous and method-name-only matching cannot tell it from ``Path.replace``.
_PATH_WRITE_METHODS: Final[frozenset[str]] = frozenset(
    {
        "write_text",
        "write_bytes",
        "mkdir",
        "rmdir",
        "unlink",
        "touch",
        "rmtree",
        "symlink_to",
        "hardlink_to",
        "chmod",
        "lchmod",
    }
)
_OS_WRITE_FUNCS: Final[frozenset[str]] = frozenset(
    {
        "remove",
        "mkdir",
        "makedirs",
        "rmdir",
        "removedirs",
        "unlink",
        "rename",
        "renames",
        "replace",
        "chmod",
        "chown",
        "symlink",
        "link",
        "truncate",
        "mkfifo",
        "mknod",
    }
)
_SHUTIL_WRITE_FUNCS: Final[frozenset[str]] = frozenset(
    {
        "copy",
        "copy2",
        "copyfile",
        "copytree",
        "copymode",
        "copystat",
        "move",
        "rmtree",
        "make_archive",
        "unpack_archive",
        "chown",
    }
)
# os process-spawning surface (subprocess-equivalent).
_OS_PROC_FUNCS: Final[frozenset[str]] = frozenset(
    {
        "system",
        "popen",
        "spawnl",
        "spawnle",
        "spawnlp",
        "spawnlpe",
        "spawnv",
        "spawnve",
        "spawnvp",
        "spawnvpe",
        "execl",
        "execle",
        "execlp",
        "execlpe",
        "execv",
        "execve",
        "execvp",
        "execvpe",
    }
)
_KAFKA_BUS_NAMES: Final[frozenset[str]] = frozenset(
    {"KafkaProducer", "AIOKafkaProducer", "AIOKafkaConsumer", "KafkaConsumer"}
)
_OPEN_WRITE_MODE_CHARS: Final[str] = "wax+"

# Human-readable surface label used in the finding message.
_SURFACE_LABEL: Final[dict[str, str]] = {
    "database": "database driver",
    "network": "network/HTTP client",
    "subprocess": "subprocess execution",
    "git": "git invocation",
    "linear": "Linear API access",
    "filesystem": "filesystem write",
    "direct-bus": "direct event-bus instantiation",
    "direct-adapter": "direct infra-adapter instantiation",
}


def _module_surface(dotted_module: str) -> str | None:
    """Classify an imported dotted module into a forbidden surface, else None."""
    root = dotted_module.split(".", 1)[0]
    if root in _DB_ROOTS:
        return "database"
    if root in _NET_ROOTS:
        return "network"
    if dotted_module == "urllib.request" or dotted_module.startswith(
        ("urllib.request.", "urllib.error")
    ):
        return "network"
    if root == "subprocess":
        return "subprocess"
    if root in _GIT_ROOTS:
        return "git"
    if root in _LINEAR_ROOTS:
        return "linear"
    return None


def _first_command_word(call: ast.Call) -> str | None:
    """Return the first command token of a subprocess/os call, if a literal.

    Handles both ``run("git status")`` (string) and ``run(["git", ...])``
    (list/tuple whose first element is a string literal).
    """
    if not call.args:
        return None
    first = call.args[0]
    if isinstance(first, ast.Constant) and isinstance(first.value, str):
        return first.value
    if isinstance(first, (ast.List, ast.Tuple)) and first.elts:
        head = first.elts[0]
        if isinstance(head, ast.Constant) and isinstance(head.value, str):
            return head.value
    return None


def _is_git_command(command: str | None) -> bool:
    """True when a command string/argv resolves to the ``git`` executable."""
    if command is None:
        return False
    tokens = command.strip().split()
    if not tokens:
        return False
    exe = tokens[0]
    return exe == "git" or exe.endswith("/git")


def _open_is_write_mode(call: ast.Call) -> bool:
    """True when a bare ``open(...)`` call uses a write/append/create mode."""

    def _is_write(value: object) -> bool:
        return isinstance(value, str) and any(
            c in value for c in _OPEN_WRITE_MODE_CHARS
        )

    if len(call.args) >= 2 and isinstance(call.args[1], ast.Constant):
        return _is_write(call.args[1].value)
    for keyword in call.keywords:
        if keyword.arg == "mode" and isinstance(keyword.value, ast.Constant):
            return _is_write(keyword.value.value)
    return False


def _has_linear_url_arg(call: ast.Call) -> bool:
    """True when any string-literal argument targets a ``linear.app`` host."""
    for arg in call.args:
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            if "linear.app" in arg.value:
                return True
    return False


def _import_has_annotation(source_lines: list[str], node: ast.stmt | ast.expr) -> bool:
    """Whether the statement carries an ``# io-ok`` annotation.

    Checks the statement's opening line, closing line (``end_lineno``), and the
    line immediately preceding it — handling reformatted multi-line statements.
    """
    candidates = {node.lineno}
    end_lineno = getattr(node, "end_lineno", None)
    if end_lineno:
        candidates.add(end_lineno)
    candidates.add(node.lineno - 1)
    return any(
        0 < lineno <= len(source_lines) and _IO_OK_MARKER in source_lines[lineno - 1]
        for lineno in candidates
    )


class IoSurfaceVisitor(ast.NodeVisitor):
    """Walk an AST for I/O surfaces forbidden outside EFFECT node packages."""

    def __init__(self, path: str, source_lines: list[str]) -> None:
        self._path = path
        self._source_lines = source_lines
        self.findings: list[ModelValidationFinding] = []

    # -- imports -----------------------------------------------------------
    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            surface = _module_surface(alias.name)
            if surface is not None:
                self._record(node, surface, f"import {alias.name}")
                break
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        # node.module is None for relative imports (`from . import x`) — skip.
        if node.module is not None:
            surface = _module_surface(node.module)
            if surface is not None:
                self._record(node, surface, f"from {node.module} import ...")
        self.generic_visit(node)

    # -- calls -------------------------------------------------------------
    def visit_Call(self, node: ast.Call) -> None:
        classified = self._classify_call(node)
        if classified is not None:
            surface, detail = classified
            self._record(node, surface, detail)
        self.generic_visit(node)

    def _classify_call(self, node: ast.Call) -> tuple[str, str] | None:
        func = node.func

        if isinstance(func, ast.Name):
            name = func.id
            if name == "open" and _open_is_write_mode(node):
                return "filesystem", "open(..., write mode)"
            if _is_bus_ctor(name):
                return "direct-bus", f"{name}(...)"
            if _is_adapter_ctor(name):
                return "direct-adapter", f"{name}(...)"

        if isinstance(func, ast.Attribute):
            attr = func.attr
            base = func.value.id if isinstance(func.value, ast.Name) else None

            if base == "subprocess":
                if _is_git_command(_first_command_word(node)):
                    return "git", f"subprocess.{attr}(['git', ...])"
                return "subprocess", f"subprocess.{attr}(...)"
            if base == "os" and attr in _OS_PROC_FUNCS:
                if _is_git_command(_first_command_word(node)):
                    return "git", f"os.{attr}('git ...')"
                return "subprocess", f"os.{attr}(...)"
            if base == "os" and attr in _OS_WRITE_FUNCS:
                return "filesystem", f"os.{attr}(...)"
            if base == "shutil" and attr in _SHUTIL_WRITE_FUNCS:
                return "filesystem", f"shutil.{attr}(...)"
            if base == "confluent_kafka":
                return "direct-bus", f"confluent_kafka.{attr}(...)"
            if attr in _PATH_WRITE_METHODS:
                return "filesystem", f".{attr}(...)"
            if _is_bus_ctor(attr):
                return "direct-bus", f"{attr}(...)"
            if _is_adapter_ctor(attr):
                return "direct-adapter", f"{attr}(...)"

        # Linear specialisation layered on any call carrying a linear.app URL.
        if _has_linear_url_arg(node):
            return "linear", "linear.app URL literal"
        return None

    def _record(self, node: ast.stmt | ast.expr, surface: str, detail: str) -> None:
        if _import_has_annotation(self._source_lines, node):
            return
        label = _SURFACE_LABEL[surface]
        self.findings.append(
            ModelValidationFinding(
                validator_id=VALIDATOR_ID,
                severity=_SEVERITY_FAIL,
                location=f"{self._path}:{node.lineno}",
                message=(
                    f"{self._path}:{node.lineno}: I/O in non-EFFECT node — "
                    f"{label} ({detail}); only EFFECT nodes may perform I/O. "
                    "Move it into a dedicated EFFECT node (inject "
                    "adapters/buses via DI). Add '# io-ok: <reason>' to "
                    "suppress a proven-legitimate exception."
                ),
                remediation=_REMEDIATION,
            )
        )


def _is_adapter_ctor(identifier: str) -> bool:
    """True when ``identifier`` looks like an infra-adapter class constructor."""
    return identifier.endswith("Adapter") and identifier[:1].isupper()


def _is_bus_ctor(identifier: str) -> bool:
    """True when ``identifier`` looks like an event-bus class constructor."""
    if identifier in _KAFKA_BUS_NAMES:
        return True
    return identifier.endswith("EventBus") and identifier[:1].isupper()
