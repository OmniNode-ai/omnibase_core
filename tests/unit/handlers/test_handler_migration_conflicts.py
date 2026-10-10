# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Replay of the OCC ``check-migration-conflicts`` decisions (OMN-20074).

Each case builds a fixture tree of peer repositories under ``tmp_path`` and runs
the core handler over it. The expected output and exit status of every case was
recorded by running onex_change_control rev a89a6f30fabf
``check_migration_conflicts.py`` on the same trees (colour codes are stripped
there when stdout is not a terminal); the handler must reproduce them.
"""

from __future__ import annotations

import importlib.resources
from pathlib import Path

import pytest
import yaml

from omnibase_core.handlers.handler_migration_conflicts import (
    INVENTORY_RESOURCE,
    HandlerMigrationConflicts,
    main,
)
from omnibase_core.models.nodes.boundary_validation.model_migration_conflicts_input import (
    ModelMigrationConflictsInput,
)
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile

pytestmark = pytest.mark.unit

# Per logical database of onex_change_control dev da751e728024
# src/onex_change_control/boundaries/migration_inventory.yaml: its migration sets as
# (source repo, directory) and its number of migration files.
OCC_INVENTORY = {
    "omnibase_infra": ([("omnibase_infra", "docker/migrations/forward")], 93),
    "omniintelligence": (
        [
            ("omnibase_infra", "docker/migrations/intelligence"),
            ("omniintelligence", "deployment/database/migrations"),
        ],
        55,
    ),
    "omnidash_analytics": ([("omnidash-archived", "migrations")], 76),
    "omnimemory": ([("omnimemory", "deployment/database/migrations")], 5),
    "omninode_cloud": ([("omninode_infra", "db/migrations")], 46),
    "omniclaude": ([("omniclaude", "sql/migrations")], 3),
    "omniweb": ([("omniweb", "scripts/migrations")], 1),
}

ALPHA_WIDGETS = """\
CREATE TABLE IF NOT EXISTS widgets (
    id UUID PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT widgets_name_unique UNIQUE (name)
);
"""
BETA_WIDGETS_CONFLICT = """\
CREATE TABLE widgets (
    id UUID PRIMARY KEY,
    label TEXT
);
"""
BETA_GADGETS = """\
CREATE TABLE gadgets (
    id UUID PRIMARY KEY,
    widget_id UUID NOT NULL
);
ALTER TABLE gadgets ADD COLUMN colour TEXT;
"""
ALPHA_REPOSITORY = '''\
INSERT_SQL = """
INSERT INTO widgets (id, name, colour) VALUES ($1, $2, $3)
ON CONFLICT (id) DO NOTHING
"""
SELECT_SQL = "SELECT id, colour FROM gadgets WHERE id = $1"
'''
IGNORED_FIXTURE = "CREATE TABLE widgets (\n    other TEXT\n);\n"

INVENTORY = """\
---
version: "1"
databases:
  alpha_db:
    migration_sets:
      - source_repo: alpha
        directory: docker/migrations/forward
        migrations:
          - file: "001_create_widgets.sql"
  beta_db:
    migration_sets:
      - source_repo: beta
        directory: docker/migrations/forward
        migrations:
          - file: "001_widgets.sql"
"""


def build_repos(root: Path, *, beta_sql: str) -> None:
    """Write the two-repo migration fixture under *root*."""
    files = {
        "alpha/docker/migrations/forward/001_create_widgets.sql": ALPHA_WIDGETS,
        "alpha/docker/migrations/rollback/001_create_widgets.sql": IGNORED_FIXTURE,
        "alpha/tests/fixtures/migrations/001_fixture.sql": IGNORED_FIXTURE,
        "alpha/src/alpha/repository.py": ALPHA_REPOSITORY,
        "beta/docker/migrations/forward/001_widgets.sql": beta_sql,
    }
    for rel, text in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


# Recorded from onex_change_control rev a89a6f30fabf check_migration_conflicts.py.
EXPECTED_CONFLICT = """\
Found 1 migration conflict(s):

  NAME_CONFLICT: table `widgets`
    - alpha: 001_create_widgets.sql (3 columns)
    - beta: 001_widgets.sql (2 columns)
      missing in 001_create_widgets.sql: label
      missing in 001_widgets.sql: created_at, name

"""
EXPECTED_CLEAN = "No migration conflicts found.\n"
EXPECTED_SUPPRESSED = (
    "No migration conflicts found.\n"
    "Suppressed 1 known conflict(s) via suppressions file.\n\n"
)
EXPECTED_CLEAN_COLUMNS = """\
No migration conflicts found.
Found 1 column-reference violation(s):

  MISSING_COLUMN: `colour` in table `widgets`
    file: alpha/repository.py

"""
EXPECTED_AMBIGUOUS_COLUMNS = """\
Found 1 migration conflict(s):

  NAME_CONFLICT: table `widgets`
    - alpha: 001_create_widgets.sql (3 columns)
    - beta: 001_widgets.sql (2 columns)
      missing in 001_create_widgets.sql: label
      missing in 001_widgets.sql: created_at, name

SCHEMA_AMBIGUOUS: 1 table(s) defined with conflicting schemas across repos — column validation skipped:
  - widgets

"""


def _run(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    beta_sql: str,
    *extra: str,
) -> tuple[int, str]:
    root = tmp_path / "repos"
    build_repos(root, beta_sql=beta_sql)
    empty_inventory = tmp_path / "no_inventory.yaml"
    empty_inventory.write_text("---\ndatabases: {}\n", encoding="utf-8")
    args = ["--repos-root", str(root), *extra]
    if "--migration-inventory" not in extra:
        args += ["--migration-inventory", str(empty_inventory)]
    code = main(args)
    return code, capsys.readouterr().out


def test_clean_fixture_passes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert _run(tmp_path, capsys, BETA_GADGETS) == (0, EXPECTED_CLEAN)


def test_name_conflict_fails_naming_table_and_files(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert _run(tmp_path, capsys, BETA_WIDGETS_CONFLICT) == (
        1,
        EXPECTED_CONFLICT,
    )


def test_warn_only_reports_the_conflict_and_exits_zero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert _run(tmp_path, capsys, BETA_WIDGETS_CONFLICT, "--warn-only") == (
        0,
        EXPECTED_CONFLICT,
    )


def test_inventory_separates_databases(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    inventory = tmp_path / "inventory.yaml"
    inventory.write_text(INVENTORY, encoding="utf-8")
    result = _run(
        tmp_path,
        capsys,
        BETA_WIDGETS_CONFLICT,
        "--migration-inventory",
        str(inventory),
    )
    assert result == (0, EXPECTED_CLEAN)


def test_suppressed_table_is_reported_as_suppressed(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    suppressions = tmp_path / "suppressions.yaml"
    suppressions.write_text("suppressions:\n  - table: Widgets\n", encoding="utf-8")
    result = _run(
        tmp_path,
        capsys,
        BETA_WIDGETS_CONFLICT,
        "--suppressions-file",
        str(suppressions),
    )
    assert result == (0, EXPECTED_SUPPRESSED)


def test_column_reference_violation_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert _run(tmp_path, capsys, BETA_GADGETS, "--check-columns") == (
        1,
        EXPECTED_CLEAN_COLUMNS,
    )


def test_warn_columns_keeps_the_column_report_and_exits_zero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    result = _run(tmp_path, capsys, BETA_GADGETS, "--check-columns", "--warn-columns")
    assert result == (0, EXPECTED_CLEAN_COLUMNS)


def test_ambiguous_table_skips_column_validation(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    result = _run(tmp_path, capsys, BETA_WIDGETS_CONFLICT, "--check-columns")
    assert result == (1, EXPECTED_AMBIGUOUS_COLUMNS)


def test_handler_conflict_finding_names_table_and_files() -> None:
    report = HandlerMigrationConflicts().handle(
        ModelMigrationConflictsInput(
            migration_files=[
                ModelSourceFile(
                    path="alpha/docker/migrations/forward/001_create_widgets.sql",
                    source=ALPHA_WIDGETS,
                ),
                ModelSourceFile(
                    path="beta/docker/migrations/forward/001_widgets.sql",
                    source=BETA_WIDGETS_CONFLICT,
                ),
            ],
        )
    )
    assert report.overall_status == "FAIL"
    (finding,) = report.findings
    assert finding.rule_id == "name_conflict"
    assert finding.evidence["table"] == "widgets"
    assert "alpha: 001_create_widgets.sql" in finding.message
    assert "beta: 001_widgets.sql" in finding.message


def test_missing_repos_root_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["--repos-root", str(tmp_path / "absent")]) == 1
    assert "is not a directory" in capsys.readouterr().err


def test_packaged_inventory_holds_the_occ_databases() -> None:
    text = (
        importlib.resources.files("omnibase_core.contracts") / INVENTORY_RESOURCE
    ).read_text(encoding="utf-8")
    databases = yaml.safe_load(text)["databases"]
    assert {
        name: (
            [(s["source_repo"], s["directory"]) for s in config["migration_sets"]],
            sum(len(s["migrations"]) for s in config["migration_sets"]),
        )
        for name, config in databases.items()
    } == OCC_INVENTORY
