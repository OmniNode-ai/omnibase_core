# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Cross-repo SQL migration conflict check (OMN-20074).

Ported from onex_change_control (``check-migration-conflicts``, rev
a89a6f30fabf, identical at dev da751e728024) for OCC retirement step S8. The
decisions are the source's:

* ``NAME_CONFLICT`` / ``EXACT_DUPLICATE``: two migrations inside one logical
  database create the same table with different, or identical, columns. The
  logical database of a migration file comes from the migration inventory,
  copied from dev da751e728024 to
  ``contracts/migration_inventory.yaml``; a table with any definition outside
  the inventory is judged in one global boundary.
* ``MISSING_COLUMN`` (``--check-columns``): a single-table SQL string literal in
  ``<repo>/src/**/*.py`` names a column the migration DDL never defines. A table
  defined with different columns by different repositories is reported as
  ambiguous and its columns are not checked.

The handler is pure over an explicit snapshot
(:class:`ModelMigrationConflictsInput`); ``main`` finds the files under
``--repos-root`` exactly as the source did, reads them through the source-file
gather EFFECT and prints the source's report text without colour codes (the
source stripped them when stdout was not a terminal).

Usage::

    python -m omnibase_core.handlers.handler_migration_conflicts --repos-root DIR \\
        [--repos R ...] [--warn-only] [--check-columns] [--warn-columns] \\
        [--suppressions-file PATH] [--migration-inventory PATH]

Exit code 0 = no conflicts (or ``--warn-only``). Exit code 1 = a conflict, a
column-reference violation without ``--warn-columns``, a missing repos root or
an unreadable file.
"""

from __future__ import annotations

import argparse
import importlib.resources
import posixpath
import re
import sys
from collections.abc import Iterator, Mapping, Sequence
from pathlib import Path, PurePosixPath
from typing import Final, Literal

from omnibase_core.enums.enum_migration_conflict_type import EnumMigrationConflictType
from omnibase_core.models.nodes.boundary_validation.model_migration_conflict import (
    ModelMigrationConflict,
)
from omnibase_core.models.nodes.boundary_validation.model_migration_conflicts_input import (
    ModelMigrationConflictsInput,
)
from omnibase_core.models.nodes.boundary_validation.model_migration_table_definition import (
    ModelMigrationTableDefinition,
)
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile
from omnibase_core.models.nodes.source_file_gather.model_source_file_gather_input import (
    ModelSourceFileGatherInput,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationFindingEmbed,
    ModelValidationReport,
    ModelValidationRequestRef,
)
from omnibase_core.nodes.node_source_file_gather_effect.handler import (
    NodeSourceFileGatherEffect,
)
from omnibase_core.utils.util_safe_yaml_loader import load_yaml_mapping_no_duplicates

VALIDATOR_ID: Final[str] = "migration-conflicts"
INVENTORY_RESOURCE: Final[str] = "migration_inventory.yaml"
UNINVENTORIED_BOUNDARY: Final[str] = "__uninventoried__"
RULE_MISSING_COLUMN: Final[str] = "missing_column"
RULE_SCHEMA_AMBIGUOUS: Final[str] = "schema_ambiguous"


# Regex to extract CREATE TABLE statements and their columns
CREATE_TABLE_RE: Final[re.Pattern[str]] = re.compile(
    r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)\s*\((.*?)\);",
    re.IGNORECASE | re.DOTALL,
)

# Regex to extract column definitions (name + type, ignoring constraints)
COLUMN_RE: Final[re.Pattern[str]] = re.compile(
    r"^\s*(\w+)\s+([\w\[\]()]+)",
    re.MULTILINE,
)

# Keywords that are NOT column names (constraint keywords)
CONSTRAINT_KEYWORDS: Final[frozenset[str]] = frozenset(
    {
        "PRIMARY",
        "UNIQUE",
        "CHECK",
        "FOREIGN",
        "CONSTRAINT",
        "INDEX",
        "CREATE",
        "REFERENCES",
    }
)

MIGRATION_SCAN_EXCLUDED_PATH_PARTS: Final[frozenset[str]] = frozenset(
    {
        ".cache",
        ".claude",
        ".mypy_cache",
        ".nox",
        ".pytest_cache",
        ".ruff_cache",
        ".tox",
        ".turbo",
        ".venv",
        "__pycache__",
        "build",
        "dist",
        "htmlcov",
        "node_modules",
        "omni_worktrees",
        "site-packages",
        "venv",
    }
)
_MIN_TEST_FIXTURE_PATH_PARTS: Final[int] = 3
_ASSIGNMENT_PARTS: Final[int] = 2

# High-confidence SQL patterns for extracting column references.
# V1 scope: single-table statements only.

# INSERT INTO table (col1, col2, ...)
_INSERT_RE: Final[re.Pattern[str]] = re.compile(
    r"INSERT\s+INTO\s+(\w+)\s*\(([^)]+)\)",
    re.IGNORECASE,
)

# SELECT col1, col2 FROM table
_SELECT_RE: Final[re.Pattern[str]] = re.compile(
    r"SELECT\s+(.*?)\s+FROM\s+(\w+)",
    re.IGNORECASE | re.DOTALL,
)

# UPDATE table SET col = ...
_UPDATE_RE: Final[re.Pattern[str]] = re.compile(
    r"UPDATE\s+(\w+)\s+SET\s+(.*?)(?:\s+WHERE|\s+RETURNING|\s*;|\s*$)",
    re.IGNORECASE | re.DOTALL,
)

# ON CONFLICT (col1, col2)
_ON_CONFLICT_RE: Final[re.Pattern[str]] = re.compile(
    r"ON\s+CONFLICT\s*\(([^)]+)\)",
    re.IGNORECASE,
)

# RETURNING col1, col2
_RETURNING_RE: Final[re.Pattern[str]] = re.compile(
    r"RETURNING\s+(.*?)(?:\s*;|\s*$|\s*\))",
    re.IGNORECASE | re.DOTALL,
)

# ALTER TABLE t ADD COLUMN col type ...
_ALTER_ADD_RE: Final[re.Pattern[str]] = re.compile(
    r"ALTER\s+TABLE\s+(?:IF\s+EXISTS\s+)?(\w+)\s+ADD\s+(?:COLUMN\s+)?(\w+)\s+",
    re.IGNORECASE,
)

# ALTER TABLE t DROP COLUMN col
_ALTER_DROP_RE: Final[re.Pattern[str]] = re.compile(
    r"ALTER\s+TABLE\s+(?:IF\s+EXISTS\s+)?(\w+)\s+DROP\s+(?:COLUMN\s+)?(?:IF\s+EXISTS\s+)?(\w+)",
    re.IGNORECASE,
)

# Tokens that are SQL keywords / expressions, not column names
_SQL_KEYWORDS: Final[frozenset[str]] = frozenset(
    {
        "*",
        "null",
        "true",
        "false",
        "default",
        "now",
        "current_timestamp",
        "count",
        "sum",
        "avg",
        "min",
        "max",
        "coalesce",
        "case",
        "when",
        "then",
        "else",
        "end",
        "as",
        "distinct",
        "all",
    }
)

_IDENTIFIER_RE: Final[re.Pattern[str]] = re.compile(r"^[a-z_]\w*$")


def load_inventory_yaml() -> str:
    """Return the packaged migration inventory as text."""
    ref = importlib.resources.files("omnibase_core.contracts") / INVENTORY_RESOURCE
    return ref.read_text(encoding="utf-8")


def _repo_of(path: str) -> str:
    return path.split("/", 1)[0]


def _name_of(path: str) -> str:
    return PurePosixPath(path).name


def _dict_items(value: object) -> Iterator[tuple[object, object]]:
    if isinstance(value, Mapping):
        yield from value.items()


def _list_items(value: object) -> Iterator[object]:
    if isinstance(value, list):
        yield from value


def _load_boundaries(inventory_yaml: str | None) -> dict[str, str]:
    """Map ``<repo>/<directory>/<file>`` of each inventoried migration to its database."""
    if inventory_yaml is None or not inventory_yaml.strip():
        return {}
    data = load_yaml_mapping_no_duplicates(inventory_yaml, source="migration inventory")
    boundaries: dict[str, str] = {}
    for db_name, db_config in _dict_items(data.get("databases", {})):
        if not isinstance(db_config, Mapping):
            continue
        for migration_set in _list_items(db_config.get("migration_sets", [])):
            if not isinstance(migration_set, Mapping):
                continue
            source_repo = migration_set.get("source_repo")
            directory = migration_set.get("directory")
            if not isinstance(source_repo, str) or not isinstance(directory, str):
                continue
            for entry in _list_items(migration_set.get("migrations", [])):
                if not isinstance(entry, Mapping):
                    continue
                filename = entry.get("file")
                if not isinstance(filename, str) or not filename.endswith(".sql"):
                    continue
                key = posixpath.normpath(f"{source_repo}/{directory}/{filename}")
                boundaries[key] = str(db_name)
    return boundaries


def _extract_tables(source: str, path: str) -> list[ModelMigrationTableDefinition]:
    """Extract CREATE TABLE definitions from one SQL migration file."""
    tables: list[ModelMigrationTableDefinition] = []
    for match in CREATE_TABLE_RE.finditer(source):
        columns: set[str] = set()
        for col_match in COLUMN_RE.finditer(match.group(2)):
            if col_match.group(1).upper() not in CONSTRAINT_KEYWORDS:
                columns.add(col_match.group(1).lower())
        if columns:
            tables.append(
                ModelMigrationTableDefinition(
                    table_name=match.group(1).lower(),
                    columns=frozenset(columns),
                    path=path,
                    repo_name=_repo_of(path),
                )
            )
    return tables


def _defs_by_boundary(
    definitions: list[ModelMigrationTableDefinition], boundaries: Mapping[str, str]
) -> dict[str, list[ModelMigrationTableDefinition]]:
    """Group definitions by logical database; any uninventoried one makes it global."""
    grouped: dict[str, list[ModelMigrationTableDefinition]] = {}
    for definition in definitions:
        boundary = boundaries.get(posixpath.normpath(definition.path))
        if boundary is None:
            return {UNINVENTORIED_BOUNDARY: definitions}
        grouped.setdefault(boundary, []).append(definition)
    return grouped


def _detect_conflicts(
    migration_files: Sequence[ModelSourceFile], boundaries: Mapping[str, str]
) -> list[ModelMigrationConflict]:
    table_defs: dict[str, list[ModelMigrationTableDefinition]] = {}
    for sql in migration_files:
        for table_def in _extract_tables(sql.source, sql.path):
            table_defs.setdefault(table_def.table_name, []).append(table_def)

    conflicts: list[ModelMigrationConflict] = []
    for table_name, defs in table_defs.items():
        for boundary_defs in _defs_by_boundary(defs, boundaries).values():
            if len(boundary_defs) <= 1:
                continue
            column_sets = [d.columns for d in boundary_defs]
            conflict_type = (
                EnumMigrationConflictType.EXACT_DUPLICATE
                if all(c == column_sets[0] for c in column_sets)
                else EnumMigrationConflictType.NAME_CONFLICT
            )
            conflicts.append(
                ModelMigrationConflict(
                    conflict_type=conflict_type,
                    table_name=table_name,
                    definitions=tuple(boundary_defs),
                )
            )
    return conflicts


def _conflict_lines(conflict: ModelMigrationConflict) -> list[str]:
    """The source's ``format_conflicts`` block for one conflict, colour stripped."""
    label = conflict.conflict_type.name
    lines = [f"  {label}: table `{conflict.table_name}`"]
    for defn in conflict.definitions:
        lines.append(
            f"    - {defn.repo_name}: {_name_of(defn.path)} "
            f"({len(defn.columns)} columns)"
        )
    if conflict.conflict_type == EnumMigrationConflictType.NAME_CONFLICT:
        all_columns: set[str] = set()
        for defn in conflict.definitions:
            all_columns |= defn.columns
        for defn in conflict.definitions:
            missing = all_columns - defn.columns
            if missing:
                lines.append(
                    f"      missing in {_name_of(defn.path)}: "
                    f"{', '.join(sorted(missing))}"
                )
    return lines


def _collect_repo_schemas(
    migration_files: Sequence[ModelSourceFile],
) -> dict[str, dict[str, set[str]]]:
    """Per-repo column schemas from CREATE TABLE plus ALTER TABLE ADD/DROP COLUMN."""
    repo_schemas: dict[str, dict[str, set[str]]] = {}
    for sql in migration_files:
        repo_name = _repo_of(sql.path)
        schemas = repo_schemas.setdefault(repo_name, {})
        for table_def in _extract_tables(sql.source, sql.path):
            if table_def.table_name not in schemas:
                schemas[table_def.table_name] = set(table_def.columns)
            else:
                schemas[table_def.table_name] |= set(table_def.columns)
        for m in _ALTER_ADD_RE.finditer(sql.source):
            schemas.setdefault(m.group(1).lower(), set()).add(m.group(2).lower())
        for m in _ALTER_DROP_RE.finditer(sql.source):
            tname = m.group(1).lower()
            if tname in schemas:
                schemas[tname].discard(m.group(2).lower())
    return repo_schemas


def _merge_schemas(
    repo_schemas: Mapping[str, Mapping[str, set[str]]],
) -> tuple[dict[str, set[str]], set[str]]:
    """Merge per-repo schemas; a table with differing column sets is ambiguous."""
    table_to_repos: dict[str, dict[str, set[str]]] = {}
    for repo_name, schemas in repo_schemas.items():
        for tname, cols in schemas.items():
            table_to_repos.setdefault(tname, {})[repo_name] = cols

    table_columns: dict[str, set[str]] = {}
    ambiguous_tables: set[str] = set()
    for tname, repo_cols in table_to_repos.items():
        col_sets = list(repo_cols.values())
        if len(repo_cols) > 1 and not all(c == col_sets[0] for c in col_sets):
            ambiguous_tables.add(tname)
            continue
        merged: set[str] = set()
        for cols in col_sets:
            merged |= cols
        table_columns[tname] = merged
    return table_columns, ambiguous_tables


def _extract_column_names(raw: str) -> list[str]:
    """Column names in a comma-separated SQL fragment, skipping expressions."""
    columns: list[str] = []
    for raw_token in raw.split(","):
        token = raw_token.strip()
        if not token or "(" in token or "::" in token or "." in token:
            continue
        word = token.split()[0].strip().lower()
        if word in _SQL_KEYWORDS or not _IDENTIFIER_RE.match(word):
            continue
        columns.append(word)
    return columns


def _extract_update_targets(raw: str) -> list[str]:
    """SET target column names of an UPDATE ... SET fragment."""
    columns: list[str] = []
    for assignment in raw.split(","):
        parts = assignment.split("=", 1)
        if len(parts) >= _ASSIGNMENT_PARTS:
            col = parts[0].strip().lower()
            if _IDENTIFIER_RE.match(col):
                columns.append(col)
    return columns


def _add_column_ref(
    refs: dict[str, set[str]], known_tables: set[str], table: str, cols: list[str]
) -> None:
    table = table.lower()
    if table in known_tables:
        refs.setdefault(table, set()).update(cols)


def _find_preceding_table(content: str, pos: int) -> str | None:
    """The table of the nearest preceding INSERT, else UPDATE."""
    prefix = content[:pos]
    insert_match = list(_INSERT_RE.finditer(prefix))
    update_match = list(_UPDATE_RE.finditer(prefix))
    if insert_match:
        return insert_match[-1].group(1)
    if update_match:
        return update_match[-1].group(1)
    return None


def _scan_python_for_column_refs(
    content: str, known_tables: set[str]
) -> dict[str, set[str]]:
    """Column names referenced per known table by SQL literals in one source."""
    refs: dict[str, set[str]] = {}
    for m in _INSERT_RE.finditer(content):
        _add_column_ref(
            refs, known_tables, m.group(1), _extract_column_names(m.group(2))
        )
    for m in _SELECT_RE.finditer(content):
        _add_column_ref(
            refs, known_tables, m.group(2), _extract_column_names(m.group(1))
        )
    for m in _UPDATE_RE.finditer(content):
        _add_column_ref(
            refs, known_tables, m.group(1), _extract_update_targets(m.group(2))
        )
    for m in _ON_CONFLICT_RE.finditer(content):
        insert_match = list(_INSERT_RE.finditer(content[: m.start()]))
        if insert_match:
            _add_column_ref(
                refs,
                known_tables,
                insert_match[-1].group(1),
                _extract_column_names(m.group(1)),
            )
    for m in _RETURNING_RE.finditer(content):
        table = _find_preceding_table(content, m.start())
        if table:
            _add_column_ref(
                refs, known_tables, table, _extract_column_names(m.group(1))
            )
    return refs


def _finding(
    *,
    severity: Literal["FAIL", "WARN", "SKIP"],
    rule_id: str,
    location: str | None,
    message: str,
    table: str,
) -> ModelValidationFindingEmbed:
    return ModelValidationFindingEmbed(
        validator_id=VALIDATOR_ID,
        severity=severity,
        rule_id=rule_id,
        location=location,
        message=message,
        evidence={"table": table},
    )


class HandlerMigrationConflicts:
    """Decide migration conflicts and, optionally, SQL column-reference drift."""

    def handle(self, request: ModelMigrationConflictsInput) -> ModelValidationReport:
        """Return the findings in the source's report order.

        Conflicts first (FAIL, or SKIP when suppressed), in first-seen table
        order. Then, with ``check_columns``, one WARN per ambiguous table in name
        order and one finding per missing column (FAIL, or WARN with
        ``warn_columns``) in file order.
        """
        suppressed = {t.lower() for t in request.suppressed_tables}
        findings: list[ModelValidationFindingEmbed] = []
        boundaries = _load_boundaries(request.inventory_yaml)
        for conflict in _detect_conflicts(request.migration_files, boundaries):
            findings.append(
                _finding(
                    severity="SKIP" if conflict.table_name in suppressed else "FAIL",
                    rule_id=conflict.conflict_type.value,
                    location=conflict.definitions[0].path,
                    message="\n".join(_conflict_lines(conflict)),
                    table=conflict.table_name,
                )
            )
        if request.check_columns:
            findings.extend(self._column_findings(request))
        return ModelValidationReport.from_findings(
            findings=tuple(findings),
            request=ModelValidationRequestRef(profile="default"),
            validators_run=(VALIDATOR_ID,),
        )

    @staticmethod
    def _column_findings(
        request: ModelMigrationConflictsInput,
    ) -> list[ModelValidationFindingEmbed]:
        table_columns, ambiguous = _merge_schemas(
            _collect_repo_schemas(request.migration_files)
        )
        findings = [
            _finding(
                severity="WARN",
                rule_id=RULE_SCHEMA_AMBIGUOUS,
                location=None,
                message=f"  - {table}",
                table=table,
            )
            for table in sorted(ambiguous)
        ]
        known_tables = set(table_columns)
        severity: Literal["FAIL", "WARN"] = "WARN" if request.warn_columns else "FAIL"
        for py_file in request.python_files:
            refs = _scan_python_for_column_refs(py_file.source, known_tables)
            for table, columns in refs.items():
                if table in ambiguous:
                    continue
                canonical = table_columns.get(table, set())
                for col in columns:
                    if col not in canonical:
                        findings.append(
                            _finding(
                                severity=severity,
                                rule_id=RULE_MISSING_COLUMN,
                                location=py_file.path,
                                message=(
                                    f"  MISSING_COLUMN: `{col}` in table `{table}`\n"
                                    f"    file: {_repo_of(py_file.path)}/"
                                    f"{_name_of(py_file.path)}"
                                ),
                                table=table,
                            )
                        )
        return findings


def format_conflicts(report: ModelValidationReport) -> str:
    """Render the unsuppressed conflicts in the source's text, colour stripped."""
    conflicts = [
        f
        for f in report.findings
        if f.rule_id in {t.value for t in EnumMigrationConflictType}
        and f.severity == "FAIL"
    ]
    if not conflicts:
        return "No migration conflicts found."
    lines = [f"Found {len(conflicts)} migration conflict(s):", ""]
    for finding in conflicts:
        lines += [finding.message, ""]
    return "\n".join(lines)


def format_column_violations(report: ModelValidationReport) -> str:
    """Render the column-reference findings in the source's text, colour stripped."""
    ambiguous = [f for f in report.findings if f.rule_id == RULE_SCHEMA_AMBIGUOUS]
    violations = [f for f in report.findings if f.rule_id == RULE_MISSING_COLUMN]
    lines: list[str] = []
    if ambiguous:
        lines.append(
            f"SCHEMA_AMBIGUOUS: {len(ambiguous)} table(s) "
            "defined with conflicting schemas across repos — "
            "column validation skipped:"
        )
        lines += [f.message for f in ambiguous]
        lines.append("")
    if not violations:
        if not ambiguous:
            lines.append("No column-reference violations found.")
        return "\n".join(lines)
    lines += [f"Found {len(violations)} column-reference violation(s):", ""]
    lines += [f.message for f in violations]
    lines.append("")
    return "\n".join(lines)


def _is_excluded_migration_path(relative_parts: tuple[str, ...]) -> bool:
    parts = tuple(part.lower() for part in relative_parts)
    if any(part in MIGRATION_SCAN_EXCLUDED_PATH_PARTS for part in parts):
        return True
    return (
        len(parts) >= _MIN_TEST_FIXTURE_PATH_PARTS
        and parts[0] in {"test", "tests"}
        and "fixtures" in parts[1:]
    )


def _repo_dirs(repos_root: Path, repos: Sequence[str] | None) -> list[Path]:
    if repos:
        return [repos_root / r for r in repos]
    return [
        d for d in repos_root.iterdir() if d.is_dir() and not d.name.startswith(".")
    ]


def find_migration_files(repos_root: Path, repos: Sequence[str] | None) -> list[Path]:
    """Every non-rollback ``**/migrations/**/*.sql`` file, in the source's order."""
    migration_files: list[Path] = []
    for repo_dir in _repo_dirs(repos_root, repos):
        if not repo_dir.is_dir():
            continue
        for sql_file in repo_dir.rglob("**/migrations/**/*.sql"):
            if _is_excluded_migration_path(sql_file.relative_to(repo_dir).parts):
                continue
            if "rollback" in str(sql_file).lower():
                continue
            migration_files.append(sql_file)
    return sorted(migration_files)


def find_python_files(repos_root: Path, repos: Sequence[str] | None) -> list[Path]:
    """Every ``<repo>/src/**/*.py`` file, in the source's scan order."""
    python_files: list[Path] = []
    for repo_dir in _repo_dirs(repos_root, repos):
        src_dir = repo_dir / "src"
        if src_dir.is_dir():
            python_files.extend(src_dir.rglob("*.py"))
    return python_files


def _read(
    paths: Sequence[Path], repos_root: Path
) -> tuple[list[ModelSourceFile], list[str]]:
    """Read *paths* in order; return ``<repo>/<path>`` sources and unreadable ones."""
    gathered = NodeSourceFileGatherEffect().handle(
        ModelSourceFileGatherInput(
            root=str(repos_root),
            explicit_paths=[str(p) for p in paths],
            include_patterns=["**/*"],
        )
    )
    by_path = {f.path: f.source for f in gathered.files}
    files = [
        ModelSourceFile(
            path=p.relative_to(repos_root).as_posix(), source=by_path[str(p)]
        )
        for p in paths
        if str(p) in by_path
    ]
    unreadable = [f"{s.path}: {s.reason}" for s in gathered.skipped]
    return files, unreadable


def _load_suppressions(path: Path) -> list[str]:
    if not path.is_file():
        return []
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        return []
    data = load_yaml_mapping_no_duplicates(text, source=str(path))
    tables: list[str] = []
    for entry in _list_items(data.get("suppressions")):
        if isinstance(entry, Mapping):
            table = str(entry.get("table", "")).lower()
            if table:
                tables.append(table)
    return tables


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Check for migration conflicts across repositories."
    )
    parser.add_argument(
        "--repos-root",
        type=Path,
        required=True,
        help="Root directory containing repository directories.",
    )
    parser.add_argument(
        "--repos",
        nargs="*",
        default=None,
        help="Specific repos to check (default: all under repos-root).",
    )
    parser.add_argument(
        "--warn-only",
        action="store_true",
        help="Exit 0 even if conflicts found (CI warning mode).",
    )
    parser.add_argument(
        "--check-columns",
        action="store_true",
        help="Also check that Python SQL references match migration DDL columns.",
    )
    parser.add_argument(
        "--suppressions-file",
        type=Path,
        default=None,
        help="YAML file listing known intentional conflicts to suppress.",
    )
    parser.add_argument(
        "--migration-inventory",
        type=Path,
        default=None,
        help="YAML inventory mapping migration files to logical database boundaries.",
    )
    parser.add_argument(
        "--warn-columns",
        action="store_true",
        help="Treat column-reference violations as warnings (exit 0).",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point with the source's ``check-migration-conflicts`` options."""
    args = _build_parser().parse_args(argv)
    repos_root: Path = args.repos_root
    if not repos_root.is_dir():
        sys.stderr.write(f"Error: repos-root '{repos_root}' is not a directory.\n")
        return 1

    if args.migration_inventory is None:
        inventory_yaml: str | None = load_inventory_yaml()
    elif args.migration_inventory.is_file():
        inventory_yaml = args.migration_inventory.read_text(encoding="utf-8")
    else:
        inventory_yaml = None

    migration_files, unreadable = _read(
        find_migration_files(repos_root, args.repos), repos_root
    )
    python_files: list[ModelSourceFile] = []
    if args.check_columns:
        python_files, unreadable_py = _read(
            find_python_files(repos_root, args.repos), repos_root
        )
        unreadable += unreadable_py
    if unreadable:
        for line in unreadable:
            sys.stderr.write(f"Error: unreadable file {line}\n")
        return 1

    report = HandlerMigrationConflicts().handle(
        ModelMigrationConflictsInput(
            migration_files=migration_files,
            python_files=python_files,
            inventory_yaml=inventory_yaml,
            suppressed_tables=(
                _load_suppressions(args.suppressions_file)
                if args.suppressions_file
                else []
            ),
            check_columns=args.check_columns,
            warn_columns=args.warn_columns,
        )
    )
    sys.stdout.write(f"{format_conflicts(report)}\n")
    suppressed = sum(
        1
        for f in report.findings
        if f.severity == "SKIP" and f.rule_id != RULE_MISSING_COLUMN
    )
    if suppressed:
        sys.stdout.write(
            f"Suppressed {suppressed} known conflict(s) via suppressions file.\n\n"
        )
    if args.check_columns:
        sys.stdout.write(f"{format_column_violations(report)}\n")
    if args.warn_only:
        return 0
    return 1 if report.overall_status == "FAIL" else 0


if __name__ == "__main__":
    sys.exit(main())
