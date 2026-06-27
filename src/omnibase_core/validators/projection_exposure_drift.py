# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Projection exposure⇄column drift validator (OMN-13663).

Reconciles every projection node ``contract.yaml``'s ``projection_api.exposures``
against the materialized columns of the table/view each exposure reads from. The
materialized columns are extracted from the node's own migration DDL
(``CREATE TABLE`` / ``ALTER TABLE ... ADD COLUMN`` / ``CREATE [OR REPLACE] VIEW
... AS ... SELECT col AS name``).

Two checks run:

1. **EXISTENCE (hard fail, blocking).** Every exposure ``columns`` / ``json_columns``
   entry MUST exist among the materialized columns of its table/view. A phantom
   column makes the projection query fail at runtime. Fires only when the table's
   DDL is found in the node's migrations — an exposure over an externally-defined
   table is skipped (never falsely blocked), not silently passed.

2. **OMISSION HEURISTIC (warn + annotated allowlist).** Materialized columns
   matching identity/tier/cost keywords (``cost_tier``, ``tier``, ``*_id``,
   ``correlation_id``, ``cost_*``, ``savings_*``, ``tokens_*``) that are NOT in
   ANY exposure of that table → warn. This is the ``cost_tier_name`` class of bug
   (OMN-13649): the column existed in DDL (migration 0018) but was omitted from
   the ``decisions.v1`` exposure column list, so the tier silently dropped at the
   projection boundary. A per-repo annotated allowlist
   (``.projection-exposure-allowlist.yaml``) makes intentional omissions explicit.

Usage::

    check-projection-exposure-drift [ROOT] [--allowlist PATH] [--fail-on-omission]
    python -m omnibase_core.validators.projection_exposure_drift src/

ROOT defaults to the current working directory. Exit code is 1 iff any EXISTENCE
error is found; omission warnings never change the exit code unless
``--fail-on-omission`` is passed.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

import yaml

from omnibase_core.enums.enum_projection_exposure_drift import (
    EnumProjectionDriftKind,
    EnumProjectionDriftSeverity,
)
from omnibase_core.models.validation.model_projection_exposure_finding import (
    ModelProjectionExposureFinding,
)

DEFAULT_ALLOWLIST_NAME = ".projection-exposure-allowlist.yaml"

# Column-name keywords that, when present in DDL but absent from every exposure,
# indicate a likely silently-dropped identity/tier/cost dimension. Matched as
# substrings (or, for ``*_id``, a suffix) against the lower-cased column name.
_OMISSION_SUBSTRING_KEYWORDS: tuple[str, ...] = (
    "cost_tier",
    "correlation_id",
    "cost_",
    "savings_",
    "tokens_",
)
_OMISSION_EXACT_KEYWORDS: tuple[str, ...] = ("tier",)

# SQL constraint/clause leading tokens that are NOT column definitions inside a
# CREATE TABLE body.
_NON_COLUMN_LEADERS: frozenset[str] = frozenset(
    (
        "PRIMARY",
        "FOREIGN",
        "UNIQUE",
        "CONSTRAINT",
        "CHECK",
        "EXCLUDE",
        "LIKE",
        "INDEX",
        "KEY",
    )
)

_IDENT = r'(?:"[^"]+"|[A-Za-z_][\w$]*)'
_QUALIFIED_IDENT = rf"(?:{_IDENT}\.)?{_IDENT}"

_CREATE_TABLE_RE = re.compile(
    rf"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?({_QUALIFIED_IDENT})\s*\(",
    re.IGNORECASE,
)
_ALTER_TABLE_RE = re.compile(
    rf"ALTER\s+TABLE\s+(?:IF\s+EXISTS\s+)?(?:ONLY\s+)?({_QUALIFIED_IDENT})",
    re.IGNORECASE,
)
_ADD_COLUMN_RE = re.compile(
    rf"ADD\s+COLUMN\s+(?:IF\s+NOT\s+EXISTS\s+)?({_IDENT})",
    re.IGNORECASE,
)
_CREATE_VIEW_RE = re.compile(
    rf"CREATE\s+(?:OR\s+REPLACE\s+)?(?:MATERIALIZED\s+)?VIEW\s+"
    rf"(?:IF\s+NOT\s+EXISTS\s+)?({_QUALIFIED_IDENT})",
    re.IGNORECASE,
)
_AS_ALIAS_RE = re.compile(rf"\bAS\s+({_IDENT})", re.IGNORECASE)


# --------------------------------------------------------------------------- #
# Name normalization
# --------------------------------------------------------------------------- #
def _normalize_object(name: str) -> str:
    """Normalize a table/view name: drop schema qualifier, strip quotes, lower."""
    last = name.split(".")[-1]
    return last.strip().strip('"').casefold()


def _normalize_column(name: str) -> str:
    """Normalize a column name for comparison: strip quotes, casefold."""
    return name.strip().strip('"').casefold()


# --------------------------------------------------------------------------- #
# SQL DDL extraction
# --------------------------------------------------------------------------- #
_SELECT_KW_RE = re.compile(r"\bSELECT\b", re.IGNORECASE)
_FROM_KW_RE = re.compile(r"\bFROM\b", re.IGNORECASE)
_AS_KW_RE = re.compile(r"\bAS\b", re.IGNORECASE)
_DOLLAR_TAG_RE = re.compile(r"\$[A-Za-z_]*\$")


def _annotate(text: str) -> tuple[list[int], list[bool]]:
    """Return per-character (paren-depth, is-code) arrays for SQL text.

    ``is_code`` is False inside string literals (``'...'``), line comments
    (``--``), block comments (``/* */``), and dollar-quoted bodies; paren depth
    and statement terminators inside those spans are therefore ignored. Quoted
    identifiers (``"..."``) stay code so an ``AS "alias"`` output name is seen.
    This is what makes a ``;`` or ``(`` embedded in a string literal — e.g.
    ``'... savings_estimates; token KPIs ...'`` — not split a statement.
    """
    n = len(text)
    depth = [0] * n
    code = [True] * n
    d = 0
    i = 0
    while i < n:
        ch = text[i]
        # line comment
        if ch == "-" and i + 1 < n and text[i + 1] == "-":
            while i < n and text[i] != "\n":
                code[i] = False
                depth[i] = d
                i += 1
            continue
        # block comment
        if ch == "/" and i + 1 < n and text[i + 1] == "*":
            while i < n and not (text[i] == "*" and i + 1 < n and text[i + 1] == "/"):
                code[i] = False
                depth[i] = d
                i += 1
            for _ in range(2):
                if i < n:
                    code[i] = False
                    depth[i] = d
                    i += 1
            continue
        # single-quoted string (with '' escape)
        if ch == "'":
            code[i] = False
            depth[i] = d
            i += 1
            while i < n:
                code[i] = False
                depth[i] = d
                if text[i] == "'":
                    if i + 1 < n and text[i + 1] == "'":
                        code[i + 1] = False
                        depth[i + 1] = d
                        i += 2
                        continue
                    i += 1
                    break
                i += 1
            continue
        # dollar-quoted string: $tag$ ... $tag$
        if ch == "$":
            tag_match = _DOLLAR_TAG_RE.match(text, i)
            if tag_match is not None:
                tag = tag_match.group(0)
                for j in range(i, min(i + len(tag), n)):
                    code[j] = False
                    depth[j] = d
                i += len(tag)
                while i < n and not text.startswith(tag, i):
                    code[i] = False
                    depth[i] = d
                    i += 1
                for j in range(i, min(i + len(tag), n)):
                    code[j] = False
                    depth[j] = d
                i += len(tag)
                continue
        # quoted identifier: stays code, but inner chars don't affect depth
        if ch == '"':
            depth[i] = d
            i += 1
            while i < n and text[i] != '"':
                depth[i] = d
                i += 1
            if i < n:
                depth[i] = d
                i += 1
            continue
        if ch == "(":
            depth[i] = d
            d += 1
            i += 1
            continue
        if ch == ")":
            d = max(0, d - 1)
            depth[i] = d
            i += 1
            continue
        depth[i] = d
        i += 1
    return depth, code


def _scrub(text: str, code: list[bool]) -> str:
    """Replace every non-code character (comment/string body) with a space.

    Offsets are preserved so a ``depth`` array computed on the original text stays
    aligned. After scrubbing, the extraction regexes see only code: a ``CREATE
    TABLE`` inside a comment vanishes, a ``--`` comment line inside a table body no
    longer hides the column that follows it, and a ``;`` inside a string literal is
    blanked. Quoted identifiers (``"alias"``) are code and survive intact.
    """
    return "".join(ch if code[i] else " " for i, ch in enumerate(text))


def _statement_end(text: str, start: int, depth: list[int], code: list[bool]) -> int:
    """Index of the first top-level (depth-0, code) ``;`` at/after ``start``."""
    for i in range(start, len(text)):
        if code[i] and depth[i] == 0 and text[i] == ";":
            return i
    return len(text)


def _match_balanced_parens(
    text: str, open_index: int, code: list[bool]
) -> tuple[str, int]:
    """Return (inner_body, index_after_closing_paren) for a ``(`` at ``open_index``."""
    depth = 0
    for i in range(open_index, len(text)):
        if not code[i]:
            continue
        if text[i] == "(":
            depth += 1
        elif text[i] == ")":
            depth -= 1
            if depth == 0:
                return text[open_index + 1 : i], i + 1
    return text[open_index + 1 :], len(text)


def _split_top_level_commas(body: str) -> list[str]:
    depth, code = _annotate(body)
    items: list[str] = []
    last = 0
    for i in range(len(body)):
        if code[i] and depth[i] == 0 and body[i] == ",":
            items.append(body[last:i])
            last = i + 1
    items.append(body[last:])
    return items


def _columns_from_create_table_body(body: str) -> set[str]:
    columns: set[str] = set()
    for item in _split_top_level_commas(body):
        stripped = item.strip()
        if not stripped:
            continue
        leader_match = re.match(rf"({_IDENT})", stripped)
        if leader_match is None:
            continue
        leader = leader_match.group(1)
        if leader.strip('"').upper() in _NON_COLUMN_LEADERS:
            continue
        columns.add(_normalize_column(leader))
    return columns


def _find_depth0(
    text: str,
    pattern: re.Pattern[str],
    depth: list[int],
    code: list[bool],
    start: int,
) -> re.Match[str] | None:
    """First regex match whose start is at paren-depth 0 and in code."""
    for match in pattern.finditer(text, start):
        s = match.start()
        if code[s] and depth[s] == 0:
            return match
    return None


def _output_name(item: str) -> str:
    """Resolve the output column name of one SELECT-list item.

    ``expr AS alias`` → ``alias``; a bare/qualified column (``c.created_at``,
    ``capsule_id``) → its last identifier token. This is what captures the bare
    pass-through columns that ``AS``-only extraction silently drops.
    """
    depth, code = _annotate(item)
    last_as: re.Match[str] | None = None
    for match in _AS_KW_RE.finditer(item):
        s = match.start()
        if code[s] and depth[s] == 0:
            last_as = match
    if last_as is not None:
        tail = item[last_as.end() :]
        ident = re.match(rf"\s*({_IDENT})", tail)
        if ident is not None:
            return _normalize_column(ident.group(1))
    idents = re.findall(_IDENT, item)
    return _normalize_column(idents[-1]) if idents else ""


def _view_output_columns(body: str) -> set[str]:
    """Extract a view's output columns from its definition body.

    ``body`` is the text after the view NAME up to the statement terminator. The
    final (outer) ``SELECT`` list is parsed precisely (handling both ``expr AS
    name`` and bare pass-throughs), then unioned with every ``AS`` alias in the
    body as a safety net (covers UNION arms / unusual shapes). Over-collection
    here only ADDS valid names, so the blocking existence check never falsely
    fails on a real view column.
    """
    depth, code = _annotate(body)
    columns: set[str] = set()

    # Skip the view's own defining ``AS`` keyword so ``... AS WITH`` / ``... AS
    # SELECT`` does not capture WITH/SELECT as an alias.
    defining_as = _find_depth0(body, _AS_KW_RE, depth, code, 0)
    query_start = defining_as.end() if defining_as is not None else 0

    # Optional explicit column list: CREATE VIEW v (a, b, c) AS ...
    if defining_as is not None:
        prefix = body[: defining_as.start()]
        paren = prefix.find("(")
        if paren != -1:
            inner, _ = _match_balanced_parens(body, paren, code)
            columns.update(
                _normalize_column(part)
                for part in _split_top_level_commas(inner)
                if part.strip()
            )

    # Safety net: every AS alias after the defining AS.
    for alias in _AS_ALIAS_RE.finditer(body, query_start):
        columns.add(_normalize_column(alias.group(1)))

    # Precise: outer SELECT list output names.
    select = _find_depth0(body, _SELECT_KW_RE, depth, code, query_start)
    if select is not None:
        after = _find_depth0(body, _FROM_KW_RE, depth, code, select.end())
        list_text = body[select.end() : after.start() if after else len(body)]
        for item in _split_top_level_commas(list_text):
            if item.strip():
                columns.add(_output_name(item))

    columns.discard("")
    return columns


@dataclass(frozen=True, slots=True)
class MaterializedSchema:
    """Materialized columns per object, with the subset that are base tables.

    ``columns`` maps a normalized object name to its materialized columns (precise
    for tables, output-columns for views). ``tables`` is the subset of objects
    defined by ``CREATE TABLE`` — the omission heuristic runs only over these
    (precise) columns, never over fuzzier view outputs.
    """

    columns: dict[str, set[str]]
    tables: set[str]

    def columns_for(self, obj: str) -> set[str]:
        return self.columns.get(obj, set())

    def is_table(self, obj: str) -> bool:
        return obj in self.tables


def extract_materialized_columns(sql_texts: Iterable[str]) -> MaterializedSchema:
    """Extract a :class:`MaterializedSchema` from migration DDL.

    Accumulates across every supplied SQL text (a node's migrations are unioned),
    so a base ``CREATE TABLE`` plus later ``ALTER TABLE ... ADD COLUMN`` migrations
    resolve to a single complete column set. Table columns are extracted precisely
    (CREATE TABLE body + ADD COLUMN); view columns are resolved from the outer
    SELECT list.
    """
    objects: dict[str, set[str]] = {}
    tables: set[str] = set()

    def _add(obj: str, cols: Iterable[str]) -> None:
        objects.setdefault(obj, set()).update(cols)

    for raw in sql_texts:
        depth, code = _annotate(raw)
        sql = _scrub(raw, code)

        for match in _CREATE_TABLE_RE.finditer(sql):
            obj = _normalize_object(match.group(1))
            body, _ = _match_balanced_parens(sql, match.end() - 1, code)
            _add(obj, _columns_from_create_table_body(body))
            tables.add(obj)

        for match in _ALTER_TABLE_RE.finditer(sql):
            obj = _normalize_object(match.group(1))
            end = _statement_end(sql, match.end(), depth, code)
            stmt = sql[match.end() : end]
            added = {
                _normalize_column(add.group(1)) for add in _ADD_COLUMN_RE.finditer(stmt)
            }
            if added:
                _add(obj, added)

        for match in _CREATE_VIEW_RE.finditer(sql):
            obj = _normalize_object(match.group(1))
            end = _statement_end(sql, match.end(), depth, code)
            body = sql[match.end() : end]
            _add(obj, _view_output_columns(body))

    return MaterializedSchema(columns=objects, tables=tables)


def _read_migrations(migrations_dir: Path) -> list[str]:
    if not migrations_dir.is_dir():
        return []
    texts: list[str] = []
    for sql_path in sorted(migrations_dir.glob("*.sql")):
        try:
            texts.append(sql_path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, OSError):
            continue
    return texts


# --------------------------------------------------------------------------- #
# Contract parsing
# --------------------------------------------------------------------------- #
def _exposure_columns(exposure: dict[str, object]) -> list[str]:
    cols: list[str] = []
    raw_columns = exposure.get("columns")
    if isinstance(raw_columns, list):
        cols.extend(str(c) for c in raw_columns)
    raw_json = exposure.get("json_columns")
    if isinstance(raw_json, list):
        cols.extend(str(c) for c in raw_json)
    return cols


def _is_projection_contract(data: object) -> bool:
    return (
        isinstance(data, dict)
        and isinstance(data.get("projection_api"), dict)
        and isinstance(data["projection_api"].get("exposures"), list)
    )


def discover_projection_contracts(root: Path) -> list[Path]:
    """Return every ``contract.yaml`` under ``root`` that declares a projection_api."""
    found: list[Path] = []
    for contract_path in sorted(root.rglob("contract.yaml")):
        if any(part in {"__pycache__", ".git"} for part in contract_path.parts):
            continue
        try:
            data = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
        except (yaml.YAMLError, UnicodeDecodeError, OSError):
            continue
        if _is_projection_contract(data):
            found.append(contract_path)
    return found


# --------------------------------------------------------------------------- #
# Allowlist
# --------------------------------------------------------------------------- #
def load_allowlist(path: Path) -> set[tuple[str, str, str]]:
    """Load the (node, table, column) omission allowlist.

    Only entries with a non-empty ``reason`` are honored — an unannotated entry is
    ignored so intentional omissions stay explicit, not silent.
    """
    if not path.is_file():
        return set()
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (yaml.YAMLError, UnicodeDecodeError, OSError):
        return set()
    allow: set[tuple[str, str, str]] = set()
    if not isinstance(data, dict):
        return allow
    entries = data.get("omissions")
    if not isinstance(entries, list):
        return allow
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        reason = entry.get("reason")
        if not isinstance(reason, str) or not reason.strip():
            continue
        node = entry.get("node")
        table = entry.get("table")
        column = entry.get("column")
        if not (
            isinstance(node, str) and isinstance(table, str) and isinstance(column, str)
        ):
            continue
        allow.add((node, _normalize_object(table), _normalize_column(column)))
    return allow


# --------------------------------------------------------------------------- #
# Omission keyword test
# --------------------------------------------------------------------------- #
def _is_omission_candidate(column_norm: str) -> bool:
    if column_norm in _OMISSION_EXACT_KEYWORDS:
        return True
    if column_norm.endswith("_id"):
        return True
    return any(keyword in column_norm for keyword in _OMISSION_SUBSTRING_KEYWORDS)


# --------------------------------------------------------------------------- #
# Per-contract validation
# --------------------------------------------------------------------------- #
def validate_contract(
    contract_path: Path,
    allowlist: set[tuple[str, str, str]] | None = None,
) -> list[ModelProjectionExposureFinding]:
    """Validate one projection contract against its node's migration DDL."""
    allowlist = allowlist or set()
    findings: list[ModelProjectionExposureFinding] = []

    try:
        data = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
    except (yaml.YAMLError, UnicodeDecodeError, OSError):
        return findings
    if not _is_projection_contract(data):
        return findings

    node_dir = contract_path.parent
    node = node_dir.name
    materialized = extract_materialized_columns(
        _read_migrations(node_dir / "migrations")
    )

    exposures = data["projection_api"]["exposures"]

    # (node-local) table -> set of every column exposed across all its exposures.
    exposed_by_table: dict[str, set[str]] = {}
    for exposure in exposures:
        if not isinstance(exposure, dict):
            continue
        table_raw = exposure.get("table")
        if not isinstance(table_raw, str):
            continue
        table_norm = _normalize_object(table_raw)
        cols = {_normalize_column(c) for c in _exposure_columns(exposure)}
        exposed_by_table.setdefault(table_norm, set()).update(cols)

    # (1) EXISTENCE — exposure column must exist in materialized DDL columns.
    for exposure in exposures:
        if not isinstance(exposure, dict):
            continue
        table_raw = exposure.get("table")
        if not isinstance(table_raw, str):
            continue
        table_norm = _normalize_object(table_raw)
        materialized_cols = materialized.columns_for(table_norm)
        if not materialized_cols:
            # DDL for this table not found in the node's own migrations (e.g. an
            # externally-defined table). Skip existence — do NOT falsely block.
            continue
        topic = exposure.get("topic")
        topic_str = topic if isinstance(topic, str) else None
        for col in _exposure_columns(exposure):
            if _normalize_column(col) not in materialized_cols:
                findings.append(
                    ModelProjectionExposureFinding(
                        severity=EnumProjectionDriftSeverity.ERROR,
                        kind=EnumProjectionDriftKind.MISSING_COLUMN,
                        node=node,
                        contract_path=contract_path,
                        table=table_raw,
                        column=col,
                        exposure_topic=topic_str,
                        detail=(
                            "exposure references a column that does not exist among "
                            f"the materialized columns of '{table_raw}'"
                        ),
                    )
                )

    # (2) OMISSION HEURISTIC — keyword-matching materialized column not surfaced.
    # Runs only over base TABLE columns (precise extraction); view outputs are
    # too fuzzy to omission-check without noise.
    for table_norm, exposed_cols in exposed_by_table.items():
        if not materialized.is_table(table_norm):
            continue
        materialized_cols = materialized.columns_for(table_norm)
        if not materialized_cols:
            continue
        for col_norm in sorted(materialized_cols):
            if col_norm in exposed_cols:
                continue
            if not _is_omission_candidate(col_norm):
                continue
            if (node, table_norm, col_norm) in allowlist:
                continue
            findings.append(
                ModelProjectionExposureFinding(
                    severity=EnumProjectionDriftSeverity.WARN,
                    kind=EnumProjectionDriftKind.OMITTED_COLUMN,
                    node=node,
                    contract_path=contract_path,
                    table=table_norm,
                    column=col_norm,
                    exposure_topic=None,
                    detail=(
                        "materialized identity/tier/cost column is not surfaced by "
                        "any exposure (silent projection-boundary drop); add it to an "
                        "exposure or annotate it in the allowlist"
                    ),
                )
            )

    return findings


def validate_root(
    root: Path,
    allowlist_path: Path | None = None,
) -> list[ModelProjectionExposureFinding]:
    """Validate every projection contract discovered under ``root``."""
    resolved_allowlist = (
        allowlist_path if allowlist_path is not None else root / DEFAULT_ALLOWLIST_NAME
    )
    allowlist = load_allowlist(resolved_allowlist)
    findings: list[ModelProjectionExposureFinding] = []
    for contract_path in discover_projection_contracts(root):
        findings.extend(validate_contract(contract_path, allowlist))
    return findings


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def _parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Reconcile projection node contract.yaml exposures against the "
            "materialized columns of the table/view each reads from."
        )
    )
    parser.add_argument(
        "root",
        nargs="?",
        type=Path,
        default=Path(),
        help="Repository root to scan for projection contracts (default: cwd).",
    )
    parser.add_argument(
        "--allowlist",
        type=Path,
        default=None,
        help=(
            "Path to the omission allowlist YAML "
            f"(default: <root>/{DEFAULT_ALLOWLIST_NAME})."
        ),
    )
    parser.add_argument(
        "--fail-on-omission",
        action="store_true",
        help="Also exit non-zero on omission warnings (default: warn-only).",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    findings = validate_root(args.root, args.allowlist)

    errors = [f for f in findings if f.severity is EnumProjectionDriftSeverity.ERROR]
    warnings = [f for f in findings if f.severity is EnumProjectionDriftSeverity.WARN]

    for finding in warnings:
        sys.stderr.write(f"WARN  {finding.format()}\n")
    for finding in errors:
        sys.stderr.write(f"ERROR {finding.format()}\n")

    if errors:
        sys.stderr.write(
            f"\nprojection exposure drift: {len(errors)} blocking existence "
            "error(s) — an exposure references a column its table/view does not "
            "materialize. Fix the exposure column list or the migration DDL.\n"
        )
    if warnings:
        sys.stderr.write(
            f"\nprojection exposure drift: {len(warnings)} omission warning(s) — a "
            "materialized identity/tier/cost column is not surfaced by any "
            "exposure. Add it to an exposure, or annotate the intentional omission "
            f"in {DEFAULT_ALLOWLIST_NAME}.\n"
        )

    if errors:
        return 1
    if warnings and args.fail_on_omission:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())  # error-ok: CLI entry point requires SystemExit
