# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Migration conflicts and column references from onex_change_control (OMN-20074).

The handler ports the source's decisions over explicit SQL and Python snapshots.
Discovery and reads belong to main and NodeSourceFileGatherEffect.
The source's --suppressions-file is not ported: the composite action never passed
it, and this repository does not introduce a new suppression mechanism.
Output retains the source's text without its colorama colour codes.
"""

from __future__ import annotations

import argparse
import importlib.resources
import re
import sys
from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import Final

from omnibase_core.enums.enum_migration_conflict_type import EnumMigrationConflictType
from omnibase_core.models.nodes.migration_conflicts.model_column_violation import (
    ModelColumnViolation,
)
from omnibase_core.models.nodes.migration_conflicts.model_migration_conflict import (
    ModelMigrationConflict,
)
from omnibase_core.models.nodes.migration_conflicts.model_migration_conflict_input import (
    ModelMigrationConflictInput,
)
from omnibase_core.models.nodes.migration_conflicts.model_migration_conflict_report import (
    ModelMigrationConflictReport,
)
from omnibase_core.models.nodes.migration_conflicts.model_migration_table_definition import (
    ModelMigrationTableDefinition,
)
from omnibase_core.models.nodes.migration_conflicts.model_repo_source_file import (
    ModelRepoSourceFile,
)
from omnibase_core.models.nodes.source_file_gather.model_source_file_gather_input import (
    ModelSourceFileGatherInput,
)
from omnibase_core.nodes.node_source_file_gather_effect.handler import (
    NodeSourceFileGatherEffect,
)
from omnibase_core.utils.util_safe_yaml_loader import load_yaml_mapping_no_duplicates

INVENTORY_RESOURCE: Final[str] = "migration_inventory.yaml"

UNINVENTORIED_BOUNDARY: Final[str] = "__uninventoried__"

CREATE_TABLE_RE: Final[re.Pattern[str]] = re.compile(
    r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)\s*\((.*?)\);",
    re.IGNORECASE | re.DOTALL,
)

COLUMN_RE: Final[re.Pattern[str]] = re.compile(
    r"^\s*(\w+)\s+([\w\[\]()]+)",
    re.MULTILINE,
)

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

_INSERT_RE: Final[re.Pattern[str]] = re.compile(
    r"INSERT\s+INTO\s+(\w+)\s*\(([^)]+)\)",
    re.IGNORECASE,
)

_SELECT_RE: Final[re.Pattern[str]] = re.compile(
    r"SELECT\s+(.*?)\s+FROM\s+(\w+)",
    re.IGNORECASE | re.DOTALL,
)

_UPDATE_RE: Final[re.Pattern[str]] = re.compile(
    r"UPDATE\s+(\w+)\s+SET\s+(.*?)(?:\s+WHERE|\s+RETURNING|\s*;|\s*$)",
    re.IGNORECASE | re.DOTALL,
)

_ON_CONFLICT_RE: Final[re.Pattern[str]] = re.compile(
    r"ON\s+CONFLICT\s*\(([^)]+)\)",
    re.IGNORECASE,
)

_RETURNING_RE: Final[re.Pattern[str]] = re.compile(
    r"RETURNING\s+(.*?)(?:\s*;|\s*$|\s*\))",
    re.IGNORECASE | re.DOTALL,
)

_ALTER_ADD_RE: Final[re.Pattern[str]] = re.compile(
    r"ALTER\s+TABLE\s+(?:IF\s+EXISTS\s+)?(\w+)\s+ADD\s+(?:COLUMN\s+)?(\w+)\s+",
    re.IGNORECASE,
)

_ALTER_DROP_RE: Final[re.Pattern[str]] = re.compile(
    r"ALTER\s+TABLE\s+(?:IF\s+EXISTS\s+)?(\w+)\s+DROP\s+(?:COLUMN\s+)?(?:IF\s+EXISTS\s+)?(\w+)",
    re.IGNORECASE,
)

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


def load_inventory_yaml() -> str:
    """Read the packaged byte-for-byte OCC migration inventory."""
    return (
        importlib.resources.files("omnibase_core.contracts")
        / "boundaries"
        / INVENTORY_RESOURCE
    ).read_text(encoding="utf-8")


def _dict_items(value: object) -> Iterator[tuple[object, object]]:
    """Return dict items for untyped YAML values."""
    if isinstance(value, dict):
        yield from value.items()


def _list_items(value: object) -> Iterator[object]:
    """Return list items for untyped YAML values."""
    if isinstance(value, list):
        yield from value


def iter_inventory_files(
    data: object,
) -> Iterator[tuple[str, str, str, str]]:
    """Yield database, source repo, directory, and SQL filename from inventory."""
    databases = data.get("databases", {}) if isinstance(data, dict) else {}
    for db_name, db_config in _dict_items(databases):
        if not isinstance(db_config, dict):
            continue
        for migration_set in _list_items(db_config.get("migration_sets", [])):
            if not isinstance(migration_set, dict):
                continue
            source_repo = migration_set.get("source_repo")
            directory = migration_set.get("directory")
            if not isinstance(source_repo, str) or not isinstance(directory, str):
                continue

            for entry in _list_items(migration_set.get("migrations", [])):
                if not isinstance(entry, dict):
                    continue
                filename = entry.get("file")
                if not isinstance(filename, str) or not filename.endswith(".sql"):
                    continue
                yield str(db_name), source_repo, directory, filename


def extract_tables_from_sql(
    source: str, path: str, repo_name: str
) -> list[ModelMigrationTableDefinition]:
    """Extract CREATE TABLE definitions from a SQL migration file."""
    content = source

    tables = []
    for match in CREATE_TABLE_RE.finditer(content):
        table_name = match.group(1).lower()
        body = match.group(2)

        columns: set[str] = set()
        for col_match in COLUMN_RE.finditer(body):
            col_name = col_match.group(1).upper()
            if col_name not in CONSTRAINT_KEYWORDS:
                columns.add(col_match.group(1).lower())

        if columns:
            tables.append(
                ModelMigrationTableDefinition(
                    table_name=table_name,
                    columns=frozenset(columns),
                    file_path=path,
                    repo_name=repo_name,
                )
            )

    return tables


def _collect_repo_schemas(
    migration_files: Sequence[ModelRepoSourceFile],
) -> dict[str, dict[str, set[str]]]:
    """Collect per-repo column schemas from migration files."""
    repo_schemas: dict[str, dict[str, set[str]]] = {}

    for sql_file in migration_files:
        repo_name = sql_file.repo_name

        if repo_name not in repo_schemas:
            repo_schemas[repo_name] = {}

        for table_def in extract_tables_from_sql(
            sql_file.source, sql_file.path, repo_name
        ):
            tname = table_def.table_name
            if tname not in repo_schemas[repo_name]:
                repo_schemas[repo_name][tname] = set(table_def.columns)
            else:
                repo_schemas[repo_name][tname] |= set(table_def.columns)

        _apply_alter_statements(sql_file.source, repo_name, repo_schemas)

    return repo_schemas


def _apply_alter_statements(
    content: str,
    repo_name: str,
    repo_schemas: dict[str, dict[str, set[str]]],
) -> None:
    """Apply ALTER TABLE ADD/DROP COLUMN to repo schemas."""
    for m in _ALTER_ADD_RE.finditer(content):
        tname = m.group(1).lower()
        col = m.group(2).lower()
        if tname not in repo_schemas[repo_name]:
            repo_schemas[repo_name][tname] = set()
        repo_schemas[repo_name][tname].add(col)

    for m in _ALTER_DROP_RE.finditer(content):
        tname = m.group(1).lower()
        col = m.group(2).lower()
        if tname in repo_schemas[repo_name]:
            repo_schemas[repo_name][tname].discard(col)


def _merge_schemas(
    repo_schemas: dict[str, dict[str, set[str]]],
) -> tuple[dict[str, set[str]], set[str]]:
    """Merge per-repo schemas, detecting ambiguous tables."""
    table_columns: dict[str, set[str]] = {}
    ambiguous_tables: set[str] = set()

    table_to_repos: dict[str, dict[str, set[str]]] = {}
    for repo_name, schemas in repo_schemas.items():
        for tname, cols in schemas.items():
            if tname not in table_to_repos:
                table_to_repos[tname] = {}
            table_to_repos[tname][repo_name] = cols

    for tname, repo_cols in table_to_repos.items():
        if len(repo_cols) > 1:
            col_sets = list(repo_cols.values())
            if not all(c == col_sets[0] for c in col_sets):
                ambiguous_tables.add(tname)
                continue
        merged: set[str] = set()
        for cols in repo_cols.values():
            merged |= cols
        table_columns[tname] = merged

    return table_columns, ambiguous_tables


def _extract_column_names(raw: str) -> list[str]:
    """Extract column names from a comma-separated SQL fragment.

    Filters out expressions, function calls, *, and keywords.
    """
    columns: list[str] = []
    for raw_token in raw.split(","):
        token = raw_token.strip()
        # Skip empty, expressions with parens, casts, qualified refs (foo.col)
        if not token or "(" in token or "::" in token or "." in token:
            continue
        # Take first word only (handles "col AS alias")
        word = token.split()[0].strip().lower()
        # Skip keywords and non-identifiers
        if word in _SQL_KEYWORDS or not re.match(r"^[a-z_]\w*$", word):
            continue
        columns.append(word)
    return columns


def _extract_update_targets(raw: str) -> list[str]:
    """Extract SET target column names from UPDATE ... SET fragment."""
    columns: list[str] = []
    for assignment in raw.split(","):
        parts = assignment.split("=", 1)
        if len(parts) >= 2:
            col = parts[0].strip().lower()
            if re.match(r"^[a-z_]\w*$", col):
                columns.append(col)
    return columns


def _add_column_ref(
    refs: dict[str, set[str]],
    known_tables: set[str],
    table: str,
    cols: list[str],
) -> None:
    """Add column references for a table if it's in the known set."""
    table = table.lower()
    if table in known_tables:
        if table not in refs:
            refs[table] = set()
        refs[table].update(cols)


def _find_preceding_table(
    content: str,
    pos: int,
) -> str | None:
    """Find the table name from the nearest preceding INSERT or UPDATE."""
    prefix = content[:pos]
    insert_match = list(_INSERT_RE.finditer(prefix))
    update_match = list(_UPDATE_RE.finditer(prefix))
    if insert_match:
        return insert_match[-1].group(1)
    if update_match:
        return update_match[-1].group(1)
    return None


def _scan_python_for_column_refs(
    content: str,
    known_tables: set[str],
) -> dict[str, set[str]]:
    """Scan a Python file for SQL string literals referencing known tables.

    Returns dict[table_name, set[referenced_column_names]].
    """
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


class HandlerMigrationConflicts:
    """Detect conflicts and column drift without accessing the filesystem."""

    def handle(
        self, request: ModelMigrationConflictInput
    ) -> ModelMigrationConflictReport:
        """Return findings in the source's table, boundary and file order."""
        table_defs: dict[str, list[tuple[ModelMigrationTableDefinition, str]]] = {}
        for file in request.sql_files:
            for definition in extract_tables_from_sql(
                file.source, file.path, file.repo_name
            ):
                table_defs.setdefault(definition.table_name, []).append(
                    (definition, file.resolved_path)
                )
        conflicts: list[ModelMigrationConflict] = []
        for table_name, defs in table_defs.items():
            grouped: dict[str, list[ModelMigrationTableDefinition]] = {}
            for definition, resolved_path in defs:
                boundary = request.inventory_boundaries.get(resolved_path)
                if boundary is None:
                    grouped = {
                        UNINVENTORIED_BOUNDARY: [definition for definition, _ in defs]
                    }
                    break
                grouped.setdefault(boundary, []).append(definition)
            for boundary_defs in grouped.values():
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
                        definitions=boundary_defs,
                    )
                )
        if not request.check_columns:
            return ModelMigrationConflictReport(conflicts=conflicts)
        table_columns, ambiguous_tables = _merge_schemas(
            _collect_repo_schemas(request.sql_files)
        )
        known_tables = set(table_columns.keys())
        violations: list[ModelColumnViolation] = []
        for file in request.python_files:
            refs = _scan_python_for_column_refs(file.source, known_tables)
            for table, columns in refs.items():
                if table in ambiguous_tables:
                    continue
                canonical = table_columns.get(table, set())
                for col in columns:
                    if col not in canonical:
                        violations.append(
                            ModelColumnViolation(
                                table=table,
                                column=col,
                                python_file=file.path,
                                repo=file.repo_name,
                            )
                        )
        return ModelMigrationConflictReport(
            conflicts=conflicts,
            columns_checked=True,
            column_violations=violations,
            ambiguous_tables=sorted(ambiguous_tables),
        )


def format_conflicts(conflicts: list[ModelMigrationConflict]) -> str:
    """Format conflicts for human-readable output."""
    if not conflicts:
        return "No migration conflicts found."

    lines = [
        f"Found {len(conflicts)} migration conflict(s):",
        "",
    ]

    for conflict in conflicts:
        if conflict.conflict_type == EnumMigrationConflictType.NAME_CONFLICT:
            label = "NAME_CONFLICT"
        else:
            label = "EXACT_DUPLICATE"

        lines.append(f"  {label}: table `{conflict.table_name}`")

        for defn in conflict.definitions:
            lines.append(
                f"    - {defn.repo_name}: {Path(defn.file_path).name} "
                f"({len(defn.columns)} columns)"
            )

        if conflict.conflict_type == EnumMigrationConflictType.NAME_CONFLICT:
            # Show column diff
            all_columns: set[str] = set()
            for defn in conflict.definitions:
                all_columns |= defn.columns
            for defn in conflict.definitions:
                missing = all_columns - defn.columns
                if missing:
                    lines.append(
                        f"      missing in {Path(defn.file_path).name}: "
                        f"{', '.join(sorted(missing))}"
                    )

        lines.append("")

    return "\n".join(lines)


def format_column_violations(result: ModelMigrationConflictReport) -> str:
    """Format column-reference violations for human-readable output."""
    lines: list[str] = []

    if result.ambiguous_tables:
        lines.append(
            f"SCHEMA_AMBIGUOUS: {len(result.ambiguous_tables)} table(s) "
            f"defined with conflicting schemas across repos — "
            f"column validation skipped:"
        )
        for t in sorted(result.ambiguous_tables):
            lines.append(f"  - {t}")
        lines.append("")

    if not result.column_violations:
        if not result.ambiguous_tables:
            lines.append("No column-reference violations found.")
        return "\n".join(lines)

    lines.append(
        f"Found {len(result.column_violations)} column-reference violation(s):"
    )
    lines.append("")

    for v in result.column_violations:
        lines.append(f"  MISSING_COLUMN: `{v.column}` in table `{v.table}`")
        lines.append(f"    file: {v.repo}/{Path(v.python_file).name}")
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


def find_migration_files(
    repos_root: Path, repos: list[str] | None = None
) -> list[Path]:
    """Find all SQL migration files under the given repos root."""
    if repos:
        dirs = [repos_root / r for r in repos]
    else:
        dirs = [
            d for d in repos_root.iterdir() if d.is_dir() and not d.name.startswith(".")
        ]

    migration_files = []
    for repo_dir in dirs:
        if not repo_dir.is_dir():
            continue
        for sql_file in repo_dir.rglob("**/migrations/**/*.sql"):
            try:
                relative_parts = sql_file.relative_to(repo_dir).parts
            except ValueError:
                relative_parts = sql_file.parts
            if _is_excluded_migration_path(relative_parts):
                continue
            # Skip rollback migrations
            if "rollback" in str(sql_file).lower():
                continue
            migration_files.append(sql_file)

    return sorted(migration_files)


def _build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
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


def _gather_repo_files(
    repos_root: Path, paths: list[Path], pattern: str
) -> list[ModelRepoSourceFile]:
    """Read explicit paths through the effect, retaining discovery order."""
    if not paths:
        return []
    absolute_paths = [str(path.absolute()) for path in paths]
    gathered = NodeSourceFileGatherEffect().handle(
        ModelSourceFileGatherInput(
            root=str(repos_root),
            explicit_paths=absolute_paths,
            include_patterns=[pattern],
            decode_errors="replace",
        )
    )
    texts = {file.path: file.source for file in gathered.files}
    files: list[ModelRepoSourceFile] = []
    for path, absolute_path in zip(paths, absolute_paths, strict=True):
        if absolute_path not in texts:
            continue
        try:
            repo_name = path.relative_to(repos_root).parts[0]
        except ValueError:
            repo_name = path.parent.name
        files.append(
            ModelRepoSourceFile(
                repo_name=repo_name,
                path=str(path),
                resolved_path=str(path.resolve()),
                source=texts[absolute_path],
            )
        )
    return files


def main(argv: Sequence[str] | None = None) -> int:
    """Discover sources and run the migration conflict CLI."""
    args = _build_parser().parse_args(argv)
    repos_root: Path = args.repos_root
    if not repos_root.is_dir():
        sys.stderr.write(f"Error: repos-root '{repos_root}' is not a directory.\n")
        return 1
    inventory_path: Path | None = args.migration_inventory
    if inventory_path is None:
        inventory_yaml = load_inventory_yaml()
    elif inventory_path.is_file():
        inventory_yaml = inventory_path.read_text(encoding="utf-8")
    else:
        # The source treats an absent inventory as no inventory at all.
        inventory_yaml = ""
    data = (
        load_yaml_mapping_no_duplicates(
            inventory_yaml, source=str(inventory_path or INVENTORY_RESOURCE)
        )
        if inventory_yaml.strip()
        else {}
    )
    boundaries = {
        str((repos_root / source_repo / directory / filename).resolve()): db_name
        for db_name, source_repo, directory, filename in iter_inventory_files(data)
    }
    sql_files = _gather_repo_files(
        repos_root, find_migration_files(repos_root, args.repos), "*.sql"
    )
    python_files: list[ModelRepoSourceFile] = []
    if args.check_columns:
        dirs = (
            [repos_root / r for r in args.repos]
            if args.repos
            else [
                d
                for d in repos_root.iterdir()
                if d.is_dir() and not d.name.startswith(".")
            ]
        )
        for repo_dir in dirs:
            src_dir = repo_dir / "src"
            if not src_dir.is_dir():
                continue
            try:
                repo_name = repo_dir.relative_to(repos_root).parts[0]
            except ValueError:
                repo_name = repo_dir.name
            python_files.extend(
                file.model_copy(update={"repo_name": repo_name})
                for file in _gather_repo_files(
                    repos_root, list(src_dir.rglob("*.py")), "*.py"
                )
            )
    report = HandlerMigrationConflicts().handle(
        ModelMigrationConflictInput(
            sql_files=sql_files,
            inventory_boundaries=boundaries,
            check_columns=args.check_columns,
            python_files=python_files,
        )
    )
    sys.stdout.write(format_conflicts(report.conflicts) + "\n")
    if report.columns_checked:
        sys.stdout.write(format_column_violations(report) + "\n")
    if args.warn_only:
        return 0
    if report.conflicts or (report.column_violations and not args.warn_columns):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
