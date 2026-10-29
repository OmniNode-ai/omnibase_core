# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""CLI runtime of the migration conflicts check (OMN-20074): discovery, reads and main."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Final

from omnibase_core.models.nodes.migration_conflicts.model_migration_conflict_input import (
    ModelMigrationConflictInput,
)
from omnibase_core.models.nodes.migration_conflicts.model_repo_source_file import (
    ModelRepoSourceFile,
)
from omnibase_core.models.nodes.source_file_gather.model_source_file_gather_input import (
    ModelSourceFileGatherInput,
)
from omnibase_core.nodes.node_cross_repo_boundary_check_effect.handler_migration_conflicts import (
    INVENTORY_RESOURCE,
    HandlerMigrationConflicts,
    format_column_violations,
    format_conflicts,
    iter_inventory_files,
    load_inventory_yaml,
)
from omnibase_core.nodes.node_source_file_gather_effect.handler import (
    NodeSourceFileGatherEffect,
)
from omnibase_core.utils.util_safe_yaml_loader import load_yaml_mapping_no_duplicates

__all__ = ["find_migration_files", "main"]

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
