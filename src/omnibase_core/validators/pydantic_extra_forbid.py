# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Ratchet gate asserting explicit ``extra="forbid"`` on every Pydantic model (OMN-14515).

Operator ruling: ``extra`` is ``"forbid"`` for everything. ``extra="ignore"`` and
``extra="allow"`` are default-deny.

**This gate asserts the positive.** Pydantic's own default, when a model declares no
``model_config`` at all, is ``extra="ignore"`` — unknown fields are silently dropped.
So a model with *no config whatsoever* is already broken; it just never said so. A gate
that greps for the literal string ``extra="ignore"`` catches only the honest minority
(platform census: 858 implicit-default violations vs. 514 explicit ignore/allow).
Therefore: **absence of an explicit, inherited-or-declared ``extra="forbid"`` is a
violation.**

Four confirmed live silent-data-loss bugs came from exactly this — a consumer
hand-rolled a slim copy of a producer's event model with a permissive ``extra``, so
fields vanished on every message (OMN-14490, OMN-14506, OMN-14513, OMN-14514).
``extra="ignore"`` is what converts a *loud* schema mismatch into a *silent* one.

Resolution
----------
Two engines, runtime-authoritative:

1. **Runtime** (preferred): import the module, read the real ``cls.model_config``.
   Pydantic has already merged config down the MRO, so inheritance is exact — a model
   inheriting ``forbid`` from a compliant base IS compliant, with no hand-rolled MRO
   walk to get wrong.
2. **Static AST** (fallback, for files that cannot be imported): walk the class body,
   the class *keyword arguments*, and then the base classes recursively through the
   import graph.

The static engine handles the four extractor bugs a prior census lane hit — each of
which produces FALSE violations:

* ``model_config`` as an ``ast.AnnAssign`` (annotated), not just ``ast.Assign``.
* ``model_config = {"extra": "forbid"}`` as a plain **dict literal**, not only
  ``ConfigDict(...)`` (70 files platform-wide).
* ``class Foo(Base, extra="forbid")`` — ``extra`` as a **class keyword argument**, not
  in the body at all (14 files, incl. the whole ``ModelContextBundleL0``-``L4`` chain).
* Path-format (relative vs. absolute) mismatch when resolving modules to files.

``RootModel`` subclasses are exempt: Pydantic *rejects* ``extra`` on a ``RootModel``
(``PydanticUserError``), so demanding it would be an impossible-to-satisfy gate.

Ratchet, not allowlist
----------------------
* Any violation NOT in the frozen baseline fails — new models are blocked on day one.
* ``--enforce-modified <ref>`` also fails any *baselined* violation whose class body was
  touched by the diff: you may not edit a broken model and leave it broken.
* ``--check-stale`` fails when a baselined FQN is now compliant/absent — the baseline
  may only shrink, never coast.
* The only sanctioned suppression is an **expiring waiver** keyed to an open ticket AND
  PR (``extra_forbid_waivers.yaml``). An expired waiver is a hard failure, so a waiver
  cannot rot into an allowlist entry.

The existing violations are NOT burned down by hand: RSD regenerates the corpus with
``extra="forbid"`` emitted by construction. This gate exists so the *next* hand-written
model cannot be born broken.

Usage::

    # pre-commit (staged files) — full-tree ratchet + modified-model enforcement
    python -m omnibase_core.validators.pydantic_extra_forbid \
        --enforce-modified :staged src/omnibase_core

    # CI — full scan, stale-entry enforcement, modified-model enforcement vs. dev
    python -m omnibase_core.validators.pydantic_extra_forbid \
        --check-stale --enforce-modified origin/dev src/omnibase_core

    # (re)generate the frozen baseline
    python -m omnibase_core.validators.pydantic_extra_forbid \
        --write-baseline src/omnibase_core

DoD reference: OMN-14515 (parent OMN-14208).
"""

from __future__ import annotations

import argparse
import ast
import importlib
import importlib.util
import json
import subprocess
import sys
from collections.abc import Iterator, Sequence
from datetime import UTC, date, datetime
from pathlib import Path
from types import ModuleType

import yaml

from omnibase_core.models.validation.model_extra_forbid_finding import (
    ENGINE_RUNTIME,
    ENGINE_STATIC,
    STATUS_EXPLICIT_ALLOW,
    STATUS_EXPLICIT_FORBID,
    STATUS_EXPLICIT_IGNORE,
    STATUS_IMPLICIT_DEFAULT,
    STATUS_UNRESOLVED,
    ModelExtraForbidFinding,
)

DEFAULT_SCAN_ROOT = Path("src/omnibase_core")
DEFAULT_BASELINE_PATH = Path(__file__).with_name("extra_forbid_baseline.yaml")
DEFAULT_WAIVERS_PATH = Path(__file__).with_name("extra_forbid_waivers.yaml")

COMPLIANT_EXTRA = "forbid"
STAGED_REF = ":staged"
# `extra=` declared, but as a non-literal (a constant/enum reference) the AST cannot
# evaluate. Declared-but-unknowable is UNRESOLVED, never silently "implicit default".
UNKNOWN_EXTRA = "<unknown>"

# Pydantic model roots. A class whose static base chain reaches one of these is a model.
_PYDANTIC_MODEL_BASES: frozenset[str] = frozenset(
    {"BaseModel", "BaseSettings", "RootModel"}
)
# RootModel rejects `extra` outright (PydanticUserError), so it cannot comply and is exempt.
_EXEMPT_BASES: frozenset[str] = frozenset({"RootModel"})

_STATUS_BY_EXTRA: dict[str, str] = {
    "forbid": STATUS_EXPLICIT_FORBID,
    "ignore": STATUS_EXPLICIT_IGNORE,
    "allow": STATUS_EXPLICIT_ALLOW,
}


# ---------------------------------------------------------------------------
# Module <-> path resolution (extractor bug #4: path-format mismatch)
# ---------------------------------------------------------------------------
def module_for_path(path: Path) -> tuple[str, Path]:
    """Return the dotted module name for *path* and the sys.path root it hangs off.

    Anchors on the ``src/`` root when there is one, and only otherwise falls back to
    walking up while ``__init__.py`` exists. The ``src/`` anchor is required because
    the ``__init__.py`` walk is WRONG for an implicit namespace package — e.g.
    ``src/omnibase_core/models/registry/`` has no ``__init__.py``, and the walk would
    resolve its modules to bare top-level names, breaking both the import and the FQN.

    Always operates on resolved absolute paths — the relative/absolute mismatch is one
    of the four known extractor bugs.
    """
    resolved = path.resolve()
    parts_list = resolved.parts
    src_indices = [i for i, part in enumerate(parts_list) if part == "src"]

    if src_indices:
        root = Path(*parts_list[: src_indices[-1] + 1])
        parts = list(parts_list[src_indices[-1] + 1 : -1])
    else:
        parts = []
        directory = resolved.parent
        while (directory / "__init__.py").exists():
            parts.insert(0, directory.name)
            directory = directory.parent
        root = directory

    stem = resolved.stem
    if stem != "__init__":
        parts.append(stem)
    return ".".join(parts), root


# ---------------------------------------------------------------------------
# Static AST engine
# ---------------------------------------------------------------------------
class _ModuleIndex:
    """Parsed view of one module: its classes and its import bindings."""

    __slots__ = ("classes", "imports", "module", "path")

    def __init__(self, path: Path, module: str, tree: ast.Module) -> None:
        self.path = path
        self.module = module
        self.classes: dict[str, ast.ClassDef] = {}
        # local binding name -> (defining module, original class name)
        self.imports: dict[str, tuple[str, str]] = {}

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                self.classes.setdefault(node.name, node)

        package = module.rsplit(".", 1)[0] if "." in module else ""
        for node in tree.body:
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.imports[alias.asname or alias.name.split(".")[0]] = (
                        alias.name,
                        "",
                    )
            elif isinstance(node, ast.ImportFrom):
                source = _absolute_import_module(node, package)
                if source is None:
                    continue
                for alias in node.names:
                    self.imports[alias.asname or alias.name] = (source, alias.name)


def _absolute_import_module(node: ast.ImportFrom, package: str) -> str | None:
    """Resolve a possibly-relative ``from ... import`` to an absolute dotted module."""
    if not node.level:
        return node.module
    parts = package.split(".") if package else []
    if node.level - 1 > len(parts):
        return None
    base = parts[: len(parts) - (node.level - 1)]
    if node.module:
        base = base + node.module.split(".")
    return ".".join(base) if base else None


class _StaticResolver:
    """Resolves a class's effective ``extra`` by walking bases through the import graph."""

    def __init__(self, roots: Sequence[Path]) -> None:
        self._by_module: dict[str, _ModuleIndex | None] = {}
        self._sys_roots: list[Path] = []
        for root in roots:
            resolved = root.resolve()
            base = resolved if resolved.is_dir() else resolved.parent
            _, sys_root = module_for_path(base / "__probe__.py")
            if sys_root not in self._sys_roots:
                self._sys_roots.append(sys_root)

    # -- module loading -----------------------------------------------------
    def index_for_path(self, path: Path) -> _ModuleIndex | None:
        module, sys_root = module_for_path(path)
        if sys_root not in self._sys_roots:
            self._sys_roots.append(sys_root)
        cached = self._by_module.get(module)
        if cached is not None:
            return cached
        index = _parse_module(path, module)
        self._by_module[module] = index
        return index

    def _index_for_module(self, module: str) -> _ModuleIndex | None:
        if module in self._by_module:
            return self._by_module[module]
        self._by_module[module] = None  # cycle guard / negative cache
        path = self._locate(module)
        if path is None:
            return None
        index = _parse_module(path, module)
        self._by_module[module] = index
        return index

    def _locate(self, module: str) -> Path | None:
        relative = Path(*module.split("."))
        for root in self._sys_roots:
            candidate = root / relative.with_suffix(".py")
            if candidate.is_file():
                return candidate
            package_init = root / relative / "__init__.py"
            if package_init.is_file():
                return package_init
        return None

    # -- resolution ---------------------------------------------------------
    def is_pydantic_model(self, module: str, node: ast.ClassDef) -> bool:
        return self._reaches_model_base(module, node, set())

    def is_exempt(self, module: str, node: ast.ClassDef) -> bool:
        for base_module, base_name, base_node in self._bases(module, node):
            if base_name in _EXEMPT_BASES:
                return True
            if base_node is not None and self.is_exempt(base_module, base_node):
                return True
        return False

    def _reaches_model_base(
        self, module: str, node: ast.ClassDef, seen: set[tuple[str, str]]
    ) -> bool:
        key = (module, node.name)
        if key in seen:
            return False
        seen.add(key)
        for base_module, base_name, base_node in self._bases(module, node):
            if base_name in _PYDANTIC_MODEL_BASES:
                return True
            if base_node is not None and self._reaches_model_base(
                base_module, base_node, seen
            ):
                return True
        return False

    def resolve_extra(
        self, module: str, node: ast.ClassDef, seen: set[tuple[str, str]] | None = None
    ) -> tuple[str, str | None]:
        """Return ``(status, effective_extra)`` for a class, walking bases in MRO order."""
        seen = seen if seen is not None else set()
        key = (module, node.name)
        if key in seen:
            return STATUS_UNRESOLVED, None
        seen.add(key)

        own = _extra_from_class(node)
        if own is not None:
            return _STATUS_BY_EXTRA.get(own, STATUS_UNRESOLVED), own

        unresolved_base = False
        for base_module, base_name, base_node in self._bases(module, node):
            if base_name in _PYDANTIC_MODEL_BASES:
                continue  # pydantic's own root: contributes the implicit default only
            if base_node is None:
                unresolved_base = True
                continue
            status, extra = self.resolve_extra(base_module, base_node, seen)
            if extra is not None:
                return status, extra
            if status == STATUS_UNRESOLVED:
                unresolved_base = True

        if unresolved_base:
            return STATUS_UNRESOLVED, None
        return STATUS_IMPLICIT_DEFAULT, None

    def _bases(
        self, module: str, node: ast.ClassDef
    ) -> list[tuple[str, str, ast.ClassDef | None]]:
        """Return ``(defining_module, base_name, base_node|None)`` for each base."""
        out: list[tuple[str, str, ast.ClassDef | None]] = []
        index = self._by_module.get(module)
        for base in node.bases:
            name = _base_name(base)
            if name is None:
                continue
            simple = name.rsplit(".", maxsplit=1)[-1]
            if simple in _PYDANTIC_MODEL_BASES:
                out.append((module, simple, None))
                continue
            if simple in {"Generic", "ABC", "Protocol", "object"}:
                continue

            target_module: str | None = None
            target_name = simple
            if index is not None:
                binding = index.imports.get(simple)
                if binding is not None:
                    bound_module, bound_name = binding
                    target_module = bound_module
                    target_name = bound_name or simple
                elif simple in index.classes:
                    out.append((module, simple, index.classes[simple]))
                    continue

            if target_module is None:
                out.append((module, simple, None))
                continue
            if target_name in _PYDANTIC_MODEL_BASES:
                out.append((target_module, target_name, None))
                continue

            base_index = self._index_for_module(target_module)
            base_node = (
                base_index.classes.get(target_name) if base_index is not None else None
            )
            out.append((target_module, target_name, base_node))
        return out


def _parse_module(path: Path, module: str) -> _ModuleIndex | None:
    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
    except (OSError, UnicodeDecodeError, SyntaxError, ValueError):
        return None
    return _ModuleIndex(path, module, tree)


def _base_name(node: ast.expr) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _base_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    if isinstance(node, ast.Subscript):  # e.g. Generic[T], ModelBase[T]
        return _base_name(node.value)
    if isinstance(node, ast.Call):
        return _base_name(node.func)
    return None


def _extra_from_class(node: ast.ClassDef) -> str | None:
    """Extract an ``extra`` declared on the class itself, or None if it declares none.

    Covers all three declaration forms (extractor bugs #1-#3):
    class keyword arg, ``model_config = ConfigDict(...)`` / ``= {...}`` as either an
    ``Assign`` or an ``AnnAssign``, and the legacy pydantic-v1 nested ``class Config``.
    """
    # (bug #3) class keyword argument: class Foo(Base, extra="forbid")
    for keyword in node.keywords:
        if keyword.arg == "extra":
            return _literal_str(keyword.value) or UNKNOWN_EXTRA

    for stmt in node.body:
        # (bug #1) model_config as Assign OR AnnAssign
        value_node: ast.expr | None = None
        if isinstance(stmt, ast.Assign):
            if any(
                isinstance(t, ast.Name) and t.id == "model_config" for t in stmt.targets
            ):
                value_node = stmt.value
        elif isinstance(stmt, ast.AnnAssign):
            if (
                isinstance(stmt.target, ast.Name)
                and stmt.target.id == "model_config"
                and stmt.value is not None
            ):
                value_node = stmt.value

        if value_node is not None:
            extra = _extra_from_config_value(value_node)
            if extra is not None:
                return extra

        # legacy pydantic v1: class Config: extra = "forbid"
        if isinstance(stmt, ast.ClassDef) and stmt.name == "Config":
            for inner in stmt.body:
                if isinstance(inner, ast.Assign) and any(
                    isinstance(t, ast.Name) and t.id == "extra" for t in inner.targets
                ):
                    return _literal_str(inner.value) or UNKNOWN_EXTRA
    return None


def _extra_from_config_value(node: ast.expr) -> str | None:
    """Read ``extra`` out of a ``ConfigDict(...)`` call or a plain dict literal (bug #2)."""
    if isinstance(node, ast.Call):
        for keyword in node.keywords:
            if keyword.arg == "extra":
                return _literal_str(keyword.value) or UNKNOWN_EXTRA
        return None
    if isinstance(node, ast.Dict):
        for key, value in zip(node.keys, node.values, strict=False):
            if isinstance(key, ast.Constant) and key.value == "extra":
                return _literal_str(value) or UNKNOWN_EXTRA
    return None


def _literal_str(node: ast.expr) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    # e.g. extra=EnumExtra.FORBID.value or a module constant — not statically knowable.
    return None


# ---------------------------------------------------------------------------
# Runtime engine (authoritative): read the real, MRO-merged cls.model_config
# ---------------------------------------------------------------------------
class _RuntimeResolver:
    """Imports modules and reads Pydantic's own merged ``model_config``."""

    def __init__(self) -> None:
        self._modules: dict[str, ModuleType] = {}
        self._failed: set[str] = set()
        self.import_failures: dict[str, str] = {}

    def load(self, path: Path) -> ModuleType | None:
        module_name, sys_root = module_for_path(path)
        if not module_name or module_name in self._failed:
            return None
        if module_name in self._modules:
            return self._modules[module_name]

        root = str(sys_root)
        if root not in sys.path:
            sys.path.insert(0, root)
        try:
            module = importlib.import_module(module_name)
        except BaseException as exc:  # noqa: BLE001 - any import failure -> static fallback
            self._failed.add(module_name)
            self.import_failures[module_name] = f"{type(exc).__name__}: {exc}"
            return None
        self._modules[module_name] = module
        return module

    def verdict(
        self, module: ModuleType, class_name: str
    ) -> tuple[str, str | None, bool] | None:
        """Return ``(status, effective_extra, exempt)``, or None if this is not a model.

        ``cls.model_config`` is Pydantic's own config, already merged down the MRO — so
        a model inheriting ``extra="forbid"`` from a compliant base reads back as
        ``forbid`` here, with no hand-rolled MRO walk to get wrong.
        """
        from pydantic import BaseModel, RootModel

        obj = getattr(module, class_name, None)
        if not isinstance(obj, type) or not issubclass(obj, BaseModel):
            return None
        # The class may be a re-export from another module; only judge it where it lives.
        if getattr(obj, "__module__", None) != getattr(module, "__name__", None):
            return None
        if obj is BaseModel or issubclass(obj, RootModel):
            # Exempt: RootModel cannot carry `extra` at all. The status is unused —
            # the caller skips on the exempt flag.
            return STATUS_EXPLICIT_FORBID, None, True

        extra = obj.model_config.get("extra")
        if extra is None:
            return STATUS_IMPLICIT_DEFAULT, None, False
        return _STATUS_BY_EXTRA.get(str(extra), STATUS_UNRESOLVED), str(extra), False


# ---------------------------------------------------------------------------
# Scan
# ---------------------------------------------------------------------------
def scan_paths(
    paths: Sequence[Path], *, use_runtime: bool = True
) -> list[ModelExtraForbidFinding]:
    """Return one finding per Pydantic model found under *paths* (compliant included)."""
    files = list(_iter_python_files(paths))
    static = _StaticResolver(paths)
    runtime = _RuntimeResolver() if use_runtime else None

    results: list[ModelExtraForbidFinding] = []
    for path in files:
        index = static.index_for_path(path)
        if index is None:
            continue
        runtime_module = runtime.load(path) if runtime is not None else None

        for class_name, node in index.classes.items():
            verdict: tuple[str, str | None, bool] | None = None
            engine = ENGINE_STATIC

            if runtime is not None and runtime_module is not None:
                verdict = runtime.verdict(runtime_module, class_name)
                if verdict is not None:
                    engine = ENGINE_RUNTIME

            if verdict is None:
                # Runtime could not speak (module unimportable, or the class is not
                # bound at module level) -> static fallback.
                if not static.is_pydantic_model(index.module, node):
                    continue
                if static.is_exempt(index.module, node):
                    continue
                status, extra = static.resolve_extra(index.module, node)
                verdict = (status, extra, False)
            elif verdict[2]:
                continue  # exempt (RootModel) or pydantic's own BaseModel

            status, extra, _ = verdict
            results.append(
                ModelExtraForbidFinding(
                    path=path,
                    line=node.lineno,
                    column=node.col_offset,
                    class_name=class_name,
                    module=index.module,
                    status=status,
                    effective_extra=extra,
                    engine=engine,
                )
            )
    return results


def _iter_python_files(paths: Sequence[Path]) -> Iterator[Path]:
    scan_paths_ = tuple(paths) or (DEFAULT_SCAN_ROOT,)
    seen: set[Path] = set()
    for path in scan_paths_:
        if path.is_file() and path.suffix == ".py":
            candidates: Iterator[Path] = iter((path,))
        elif path.is_dir():
            candidates = (
                candidate
                for candidate in sorted(path.rglob("*.py"))
                if "__pycache__" not in candidate.parts
            )
        else:
            continue
        for candidate in candidates:
            resolved = candidate.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            yield candidate


# ---------------------------------------------------------------------------
# Baseline (frozen ratchet) + waivers (expiring, ticket+PR-keyed)
# ---------------------------------------------------------------------------
def load_baseline(path: Path) -> set[str]:
    """Load the frozen ``module:ClassName`` violation baseline.

    A missing/unreadable baseline yields the empty set — fail-closed: every violation
    is then treated as NEW.
    """
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (yaml.YAMLError, UnicodeDecodeError, OSError):
        return set()
    if not isinstance(data, dict):
        return set()
    entries = data.get("violations") or []
    if not isinstance(entries, list):
        return set()
    return {str(entry) for entry in entries if isinstance(entry, str)}


def load_waivers(path: Path, today: date) -> tuple[set[str], list[str]]:
    """Return ``(active_waived_fqns, errors)``.

    A waiver MUST carry ``fqn``, ``ticket`` (OMN-NNNN), ``pr``, and an ``expires_at``
    date. Anything missing, malformed, or expired is an ERROR (hard failure) — never a
    silent pass. That is what keeps a waiver from decaying into an allowlist entry.
    """
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return set(), []
    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        return set(), [f"waivers file is not valid YAML: {exc}"]
    if not isinstance(data, dict):
        return set(), []
    entries = data.get("waivers") or []
    if not isinstance(entries, list):
        return set(), ["waivers: expected a list under the 'waivers' key"]

    active: set[str] = set()
    errors: list[str] = []
    for raw_entry in entries:
        if not isinstance(raw_entry, dict):
            errors.append(f"waiver entry is not a mapping: {raw_entry!r}")
            continue
        fqn = str(raw_entry.get("fqn", "")).strip()
        ticket = str(raw_entry.get("ticket", "")).strip()
        pr = str(raw_entry.get("pr", "")).strip()
        expires_raw = raw_entry.get("expires_at")

        if not fqn:
            errors.append(f"waiver entry missing 'fqn': {raw_entry!r}")
            continue
        if not ticket.startswith("OMN-") or not ticket[4:].isdigit():
            errors.append(f"waiver {fqn}: 'ticket' must be an OMN-NNNN reference")
            continue
        if not pr:
            errors.append(f"waiver {fqn}: 'pr' (the in-flight PR) is required")
            continue

        expires = _coerce_date(expires_raw)
        if expires is None:
            errors.append(
                f"waiver {fqn}: 'expires_at' must be an ISO date (YYYY-MM-DD); "
                f"got {expires_raw!r}"
            )
            continue
        if expires < today:
            errors.append(
                f"waiver {fqn}: EXPIRED on {expires.isoformat()} (ticket {ticket}, {pr}) "
                f'— fix the model (extra="forbid") or renew the waiver with a new '
                f"expiry; an expired waiver is a hard failure by design"
            )
            continue
        active.add(fqn)
    return active, errors


def today_utc() -> date:
    """UTC "today" for waiver expiry — machine-timezone-independent by construction."""
    return datetime.now(UTC).date()


def _coerce_date(value: object) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value.strip())
        except ValueError:
            return None
    return None


def render_baseline(
    violations: Sequence[ModelExtraForbidFinding], scan_roots: Sequence[Path]
) -> str:
    fqns = sorted({finding.fqn for finding in violations})
    roots = ", ".join(str(root) for root in scan_roots)
    lines = [
        '# Frozen baseline for the extra="forbid" ratchet (OMN-14515).',
        "#",
        "# This is NOT an allowlist. It is a shrink-only ratchet of models that predate",
        "# the gate. New/modified models are blocked outright; --check-stale fails when",
        "# an entry here becomes compliant, forcing the count down. Do not hand-add.",
        "#",
        f"# scan roots: {roots}",
        f"# count: {len(fqns)}",
        "#",
        "# Regenerate: python -m omnibase_core.validators.pydantic_extra_forbid \\",
        f"#     --write-baseline {roots}",
        "",
        "violations:",
    ]
    lines.extend(f'  - "{fqn}"' for fqn in fqns)
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Modified-model enforcement (git diff -> changed line ranges)
# ---------------------------------------------------------------------------
def changed_line_ranges(ref: str, cwd: Path) -> dict[Path, list[tuple[int, int]]]:
    """Map absolute file path -> changed line ranges for *ref*.

    ``ref`` is either ``":staged"`` (pre-commit) or a git ref such as ``origin/dev``
    (CI, diffed as ``<ref>...HEAD``). Raises ``RuntimeError`` on git failure — the
    caller fails closed rather than silently skipping the check.
    """
    if ref == STAGED_REF:
        args = ["git", "diff", "--cached", "--unified=0", "--no-color"]
    else:
        args = ["git", "diff", "--unified=0", "--no-color", f"{ref}...HEAD"]

    try:
        proc = subprocess.run(
            args, cwd=cwd, capture_output=True, text=True, check=False
        )
    except OSError as exc:
        raise RuntimeError(f"could not run git: {exc}") from exc
    if proc.returncode != 0:
        raise RuntimeError(
            f"`{' '.join(args)}` failed (exit {proc.returncode}): "
            f"{proc.stderr.strip() or 'no stderr'}"
        )

    try:
        top = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise RuntimeError(f"could not resolve the git worktree root: {exc}") from exc

    root = Path(top)
    ranges: dict[Path, list[tuple[int, int]]] = {}
    current: Path | None = None
    for line in proc.stdout.splitlines():
        if line.startswith("+++ "):
            target = line[4:].strip()
            if target == "/dev/null":
                current = None
            else:
                current = (
                    (root / target[2:]).resolve() if target.startswith("b/") else None
                )
        elif line.startswith("@@") and current is not None:
            span = _parse_hunk(line)
            if span is not None:
                ranges.setdefault(current, []).append(span)
    return ranges


def _parse_hunk(line: str) -> tuple[int, int] | None:
    # @@ -12,0 +13,4 @@ optional trailing context
    try:
        plus = line.split("+", 1)[1].split("@@", 1)[0].strip()
    except IndexError:
        return None
    start_str, _, count_str = plus.partition(",")
    try:
        start = int(start_str)
        count = int(count_str) if count_str else 1
    except ValueError:
        return None
    if count == 0:  # pure deletion; anchor on the surrounding line
        return start, start
    return start, start + count - 1


def _class_span(path: Path, finding: ModelExtraForbidFinding) -> tuple[int, int]:
    index = _parse_module(path, finding.module)
    node = index.classes.get(finding.class_name) if index is not None else None
    if node is None:
        return finding.line, finding.line
    return node.lineno, node.end_lineno or node.lineno


def _touched(
    finding: ModelExtraForbidFinding, ranges: dict[Path, list[tuple[int, int]]]
) -> bool:
    spans = ranges.get(finding.path.resolve())
    if not spans:
        return False
    start, end = _class_span(finding.path, finding)
    return any(not (hi < start or lo > end) for lo, hi in spans)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            'Assert every Pydantic model explicitly declares extra="forbid" '
            "(resolved through inheritance). Absence is a violation — Pydantic's "
            'default is extra="ignore", i.e. silent field-dropping (OMN-14515).'
        )
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        default=[DEFAULT_SCAN_ROOT],
        help="Python file or directory paths to scan (default: src/omnibase_core).",
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        default=DEFAULT_BASELINE_PATH,
        help="Path to the frozen violation baseline YAML.",
    )
    parser.add_argument(
        "--waivers",
        type=Path,
        default=DEFAULT_WAIVERS_PATH,
        help="Path to the expiring-waiver YAML (ticket + PR + expires_at).",
    )
    parser.add_argument(
        "--write-baseline",
        action="store_true",
        help="Regenerate the baseline from the current scan and exit 0.",
    )
    parser.add_argument(
        "--check-stale",
        action="store_true",
        help=(
            "Fail if a baselined FQN is now compliant or gone — the baseline may only "
            "shrink, never coast."
        ),
    )
    parser.add_argument(
        "--enforce-modified",
        metavar="REF",
        default=None,
        help=(
            "Also fail any BASELINED violation whose class body was touched by the "
            f"diff. REF is a git ref (diffed as REF...HEAD) or '{STAGED_REF}' for the "
            "staged diff. You may not edit a broken model and leave it broken."
        ),
    )
    parser.add_argument(
        "--no-runtime",
        action="store_true",
        help=(
            "Disable runtime introspection (real cls.model_config) and use the static "
            "AST engine only. Runtime is authoritative; this is an escape hatch."
        ),
    )
    parser.add_argument(
        "--json",
        dest="json_out",
        type=Path,
        default=None,
        help="Write the full per-class census (compliant + violations) as JSON.",
    )
    return parser.parse_args(list(argv))


def _write_json(path: Path, findings: Sequence[ModelExtraForbidFinding]) -> None:
    payload = [
        {
            "file": str(f.path),
            "module": f.module,
            "class": f.class_name,
            "line": f.line,
            "status": f.status,
            "effective_extra": f.effective_extra,
            "engine": f.engine,
            "compliant": not f.is_violation,
        }
        for f in sorted(findings, key=lambda f: (str(f.path), f.line))
    ]
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)

    findings = scan_paths(args.paths, use_runtime=not args.no_runtime)
    violations = [f for f in findings if f.is_violation]

    if args.json_out is not None:
        _write_json(args.json_out, findings)

    if args.write_baseline:
        args.baseline.write_text(
            render_baseline(violations, args.paths), encoding="utf-8"
        )
        runtime_count = sum(1 for f in findings if f.engine == ENGINE_RUNTIME)
        sys.stdout.write(
            f"wrote {args.baseline}: {len(violations)} violation(s) of "
            f"{len(findings)} model(s) "
            f"({runtime_count} resolved via runtime introspection, "
            f"{len(findings) - runtime_count} via static AST)\n"
        )
        return 0

    baseline = load_baseline(args.baseline)
    waived, waiver_errors = load_waivers(args.waivers, today_utc())

    present = {f.fqn for f in violations}
    new_violations = [
        f for f in violations if f.fqn not in baseline and f.fqn not in waived
    ]

    modified_violations: list[ModelExtraForbidFinding] = []
    if args.enforce_modified:
        try:
            ranges = changed_line_ranges(args.enforce_modified, Path.cwd())
        except RuntimeError as exc:
            sys.stderr.write(
                f"pydantic-extra-forbid: --enforce-modified could not read the diff, "
                f"failing closed: {exc}\n"
            )
            return 1
        modified_violations = [
            f
            for f in violations
            if f.fqn in baseline and f.fqn not in waived and _touched(f, ranges)
        ]

    stale = sorted(baseline - present) if args.check_stale else []

    exit_code = 0

    if new_violations:
        exit_code = 1
        sys.stderr.write(
            "pydantic-extra-forbid: NEW Pydantic model(s) without an explicit "
            'extra="forbid":\n'
        )
        for finding in sorted(new_violations, key=lambda f: f.fqn):
            sys.stderr.write(f"  {finding.format()}\n")
        sys.stderr.write(
            '\n  Every model must declare extra="forbid" — inheriting it from a base is\n'
            '  fine. Pydantic\'s default is extra="ignore", which silently DROPS unknown\n'
            "  fields; four live data-loss bugs came from exactly that (OMN-14490,\n"
            "  OMN-14506, OMN-14513, OMN-14514). Fix:\n\n"
            '      model_config = ConfigDict(extra="forbid")\n\n'
            "  The baseline is not a place to add new entries. If this model is part of\n"
            "  sanctioned, time-boxed in-flight work, add an EXPIRING waiver keyed to the\n"
            f"  open ticket + PR in {args.waivers}. See OMN-14515.\n\n"
        )

    if modified_violations:
        exit_code = 1
        sys.stderr.write(
            "pydantic-extra-forbid: you MODIFIED baselined model(s) that still lack an "
            'explicit extra="forbid" — fix them now, do not leave them broken:\n'
        )
        for finding in sorted(modified_violations, key=lambda f: f.fqn):
            sys.stderr.write(f"  {finding.format()}\n")
        sys.stderr.write(
            "\n  Touching a model's body is your chance to fix it. Add\n"
            '  model_config = ConfigDict(extra="forbid") and remove the FQN from\n'
            f"  {args.baseline} so the ratchet counts down.\n\n"
        )

    if waiver_errors:
        exit_code = 1
        sys.stderr.write("pydantic-extra-forbid: waiver problem(s):\n")
        for error in waiver_errors:
            sys.stderr.write(f"  {error}\n")
        sys.stderr.write("\n")

    if stale:
        exit_code = 1
        sys.stderr.write(
            "pydantic-extra-forbid: STALE baseline entr(y/ies) — the model is now "
            "compliant or gone; delete the line so the ratchet counts down:\n"
        )
        for fqn in stale:
            sys.stderr.write(f"  {fqn}\n")
        sys.stderr.write("\n")

    if exit_code == 0:
        runtime_count = sum(1 for f in findings if f.engine == ENGINE_RUNTIME)
        sys.stdout.write(
            f"pydantic-extra-forbid: OK — {len(findings) - len(violations)}/"
            f'{len(findings)} model(s) declare extra="forbid"; '
            f"{len(violations)} baselined violation(s) remain "
            f"({runtime_count} resolved via runtime introspection).\n"
        )
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())  # error-ok: validator CLI process exit
