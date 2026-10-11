# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Decisions of the OCC ``check-migration-conflicts`` script, ported (OMN-20074).

The handler must reach the verdict of onex_change_control rev a89a6f30fa
(``src/onex_change_control/scripts/check_migration_conflicts.py``) over fixture
repositories: one table created with different columns by two migrations in the
same (uninventoried) boundary is a NAME_CONFLICT, the same columns an
EXACT_DUPLICATE, two logical databases of the inventory never conflict, and a
Python SQL literal naming an undeclared column is a column violation.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
import yaml

from omnibase_core.enums.enum_migration_conflict_type import (
    EnumMigrationConflictType,
)
from omnibase_core.handlers.handler_migration_conflicts import (
    load_inventory_yaml,
    main,
)

pytestmark = pytest.mark.unit

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "occ_boundaries"

FOO_TWO_COLUMNS = "CREATE TABLE foo (\n    id UUID PRIMARY KEY,\n    name TEXT\n);\n"
FOO_THREE_COLUMNS = (
    "CREATE TABLE IF NOT EXISTS foo (\n"
    "    id UUID PRIMARY KEY,\n"
    "    name TEXT,\n"
    "    created_at TIMESTAMPTZ\n"
    ");\n"
)
BAR = "CREATE TABLE bar (\n    id UUID PRIMARY KEY\n);\n"
EMPTY_INVENTORY = '---\nversion: "1"\ndatabases: {}\n'


def _write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _run(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    *extra: str,
    inventory: str = EMPTY_INVENTORY,
) -> tuple[int, str]:
    _write(tmp_path, "inventory.yaml", inventory)
    code = main(
        [
            "--repos-root",
            str(tmp_path / "repos"),
            "--migration-inventory",
            str(tmp_path / "inventory.yaml"),
            *extra,
        ]
    )
    return code, capsys.readouterr().out


def test_name_conflict_fails_naming_table_and_files(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repos = tmp_path / "repos"
    _write(repos / "repo_a", "docker/migrations/001_foo.sql", FOO_TWO_COLUMNS)
    _write(repos / "repo_b", "sql/migrations/007_foo.sql", FOO_THREE_COLUMNS)
    code, out = _run(tmp_path, capsys)
    assert code == 1
    assert "Found 1 migration conflict(s):" in out
    assert "  NAME_CONFLICT: table `foo`" in out
    assert "    - repo_a: 001_foo.sql (2 columns)" in out
    assert "    - repo_b: 007_foo.sql (3 columns)" in out
    assert "      missing in 001_foo.sql: created_at" in out


def test_warn_only_reports_but_exits_zero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repos = tmp_path / "repos"
    _write(repos / "repo_a", "docker/migrations/001_foo.sql", FOO_TWO_COLUMNS)
    _write(repos / "repo_b", "sql/migrations/007_foo.sql", FOO_THREE_COLUMNS)
    code, out = _run(tmp_path, capsys, "--warn-only")
    assert code == 0
    assert "  NAME_CONFLICT: table `foo`" in out


def test_exact_duplicate(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    repos = tmp_path / "repos"
    _write(repos / "repo_a", "docker/migrations/001_foo.sql", FOO_TWO_COLUMNS)
    _write(repos / "repo_b", "sql/migrations/002_foo.sql", FOO_TWO_COLUMNS)
    code, out = _run(tmp_path, capsys)
    assert code == 1
    assert "  EXACT_DUPLICATE: table `foo`" in out


def test_clean_fixture_passes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repos = tmp_path / "repos"
    _write(repos / "repo_a", "docker/migrations/001_foo.sql", FOO_TWO_COLUMNS)
    _write(repos / "repo_b", "sql/migrations/001_bar.sql", BAR)
    code, out = _run(tmp_path, capsys)
    assert code == 0
    assert "No migration conflicts found." in out


def test_inventory_separates_logical_databases(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repos = tmp_path / "repos"
    _write(repos / "repo_a", "docker/migrations/001_foo.sql", FOO_TWO_COLUMNS)
    _write(repos / "repo_b", "sql/migrations/007_foo.sql", FOO_THREE_COLUMNS)
    inventory = """---
version: "1"
databases:
  db_a:
    migration_sets:
      - source_repo: repo_a
        directory: docker/migrations
        migrations:
          - file: "001_foo.sql"
  db_b:
    migration_sets:
      - source_repo: repo_b
        directory: sql/migrations
        migrations:
          - file: "007_foo.sql"
"""
    code, out = _run(tmp_path, capsys, inventory=inventory)
    assert code == 0
    assert "No migration conflicts found." in out


def test_excluded_paths_are_not_scanned(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repos = tmp_path / "repos"
    _write(repos / "repo_a", "docker/migrations/001_foo.sql", FOO_TWO_COLUMNS)
    _write(
        repos / "repo_a",
        "tests/fixtures/x/migrations/001_foo.sql",
        FOO_THREE_COLUMNS,
    )
    _write(repos / "repo_b", "migrations/rollback/001_foo.sql", FOO_THREE_COLUMNS)
    _write(repos / "repo_b", ".venv/migrations/001_foo.sql", FOO_THREE_COLUMNS)
    code, out = _run(tmp_path, capsys)
    assert code == 0
    assert "No migration conflicts found." in out


def test_column_reference_to_undeclared_column(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repos = tmp_path / "repos"
    _write(repos / "repo_a", "docker/migrations/001_foo.sql", FOO_TWO_COLUMNS)
    _write(
        repos / "repo_a",
        "src/repo_a/writer.py",
        'SQL = "INSERT INTO foo (id, name, nope) VALUES ($1, $2, $3)"\n',
    )
    code, out = _run(tmp_path, capsys, "--check-columns")
    assert code == 1
    assert "No migration conflicts found." in out
    assert "Found 1 column-reference violation(s):" in out
    assert "  MISSING_COLUMN: `nope` in table `foo`" in out
    assert "    file: repo_a/writer.py" in out
    code, _ = _run(tmp_path, capsys, "--check-columns", "--warn-columns")
    assert code == 0


def test_conflict_types_are_the_core_enum() -> None:
    assert EnumMigrationConflictType.NAME_CONFLICT.value == "name_conflict"
    assert EnumMigrationConflictType.EXACT_DUPLICATE.value == "exact_duplicate"


def test_packaged_inventory_is_the_occ_inventory() -> None:
    expected = yaml.safe_load((FIXTURES / "manifest.yaml").read_text(encoding="utf-8"))
    parsed = json.dumps(yaml.safe_load(load_inventory_yaml()), sort_keys=True)
    digest = hashlib.sha256(parsed.encode("utf-8")).hexdigest()
    assert digest == expected["migration_inventory_parsed_sha256"]
