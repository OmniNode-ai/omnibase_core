# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the projection exposure⇄column drift validator (OMN-13663)."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from omnibase_core.enums.enum_projection_exposure_drift import (
    EnumProjectionDriftKind,
    EnumProjectionDriftSeverity,
)
from omnibase_core.validators.projection_exposure_drift import (
    extract_materialized_columns,
    load_allowlist,
    main,
    validate_contract,
    validate_root,
)

pytestmark = pytest.mark.unit


def _make_node(
    root: Path,
    *,
    node: str,
    contract_yaml: str,
    migration_sql: str | None = None,
) -> Path:
    node_dir = root / "src" / "nodes" / node
    node_dir.mkdir(parents=True, exist_ok=True)
    contract_path = node_dir / "contract.yaml"
    contract_path.write_text(textwrap.dedent(contract_yaml), encoding="utf-8")
    if migration_sql is not None:
        migrations = node_dir / "migrations"
        migrations.mkdir(exist_ok=True)
        (migrations / "0001_init.sql").write_text(
            textwrap.dedent(migration_sql), encoding="utf-8"
        )
    return contract_path


# --------------------------------------------------------------------------- #
# DDL extraction
# --------------------------------------------------------------------------- #
def test_extract_create_table_columns() -> None:
    sql = """
    CREATE TABLE IF NOT EXISTS delegation_events (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        correlation_id TEXT NOT NULL UNIQUE,
        cost_usd NUMERIC NOT NULL DEFAULT 0,
        PRIMARY KEY (id),
        CONSTRAINT uq_corr UNIQUE (correlation_id)
    );
    """
    schema = extract_materialized_columns([sql])
    assert schema.columns_for("delegation_events") == {
        "id",
        "correlation_id",
        "cost_usd",
    }
    assert schema.is_table("delegation_events")


def test_extract_alter_add_column_unions_across_migrations() -> None:
    base = "CREATE TABLE delegation_events (id UUID, correlation_id TEXT);"
    alter = """
    ALTER TABLE delegation_events
        ADD COLUMN IF NOT EXISTS cost_tier_type TEXT NOT NULL DEFAULT '',
        ADD COLUMN IF NOT EXISTS cost_tier_name TEXT NOT NULL DEFAULT '';
    """
    schema = extract_materialized_columns([base, alter])
    assert schema.columns_for("delegation_events") == {
        "id",
        "correlation_id",
        "cost_tier_type",
        "cost_tier_name",
    }


def test_extract_view_collects_aliases_and_bare_passthroughs() -> None:
    sql = """
    CREATE OR REPLACE VIEW projection_delegation_summary AS
    WITH summary AS (
        SELECT COUNT(*)::int AS total_events,
               MAX(created_at) AS latest_projection_updated_at
        FROM delegation_events
    )
    SELECT s.total_events AS "totalDelegations",
           s.latest_projection_updated_at
    FROM summary s;
    """
    schema = extract_materialized_columns([sql])
    view = schema.columns_for("projection_delegation_summary")
    assert "totaldelegations" in view  # quoted AS alias, casefolded
    assert "latest_projection_updated_at" in view  # bare pass-through (no AS)
    assert not schema.is_table("projection_delegation_summary")


def test_extract_create_table_with_inline_comments() -> None:
    # Regression for agent_routing_decisions: -- comment lines INSIDE the column
    # list must not hide the column that follows them.
    sql = """
    CREATE TABLE IF NOT EXISTS agent_routing_decisions (
        -- Identity
        id UUID PRIMARY KEY,
        correlation_id UUID,

        -- Routing decision
        selected_agent VARCHAR(255),
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    """
    cols = extract_materialized_columns([sql]).columns_for("agent_routing_decisions")
    assert {"id", "correlation_id", "selected_agent", "created_at"} <= cols


def test_extract_view_bare_passthrough_columns() -> None:
    # Regression for the projection_capsule_effectiveness false positive: a view
    # whose final SELECT lists bare pass-through columns with no AS alias.
    sql = """
    CREATE OR REPLACE VIEW v AS
    WITH scored AS (
        SELECT c.capsule_id, c.factor FROM capsule_store c
    )
    SELECT
        capsule_id,
        factor,
        (1 * 2)::float AS effective_rate
    FROM scored;
    """
    view = extract_materialized_columns([sql]).columns_for("v")
    assert {"capsule_id", "factor", "effective_rate"} <= view


def test_extract_view_with_semicolon_inside_string_literal() -> None:
    # Regression for the projection_cost_savings_overview false positive: a ';'
    # embedded in a single-quoted string must NOT truncate the view body.
    sql = """
    CREATE OR REPLACE VIEW v AS
    WITH warns AS (
        SELECT 'Token counts unavailable; KPIs remain zero.' AS note
    )
    SELECT
        'all'::text AS "window",
        warns.note AS warnings
    FROM warns;
    """
    view = extract_materialized_columns([sql]).columns_for("v")
    assert "window" in view  # output AFTER the in-string semicolon
    assert "warnings" in view


# --------------------------------------------------------------------------- #
# (c) clean contract → PASS
# --------------------------------------------------------------------------- #
def test_clean_contract_passes(tmp_path: Path) -> None:
    contract = _make_node(
        tmp_path,
        node="node_projection_clean",
        contract_yaml="""
        projection_api:
          expose: true
          exposures:
            - topic: decisions
              table: events
              columns:
                - id
                - correlation_id
                - cost_tier_name
        """,
        migration_sql="""
        CREATE TABLE events (
            id UUID PRIMARY KEY,
            correlation_id TEXT,
            cost_tier_name TEXT
        );
        """,
    )
    assert validate_contract(contract) == []


# --------------------------------------------------------------------------- #
# (a) non-existent column → FAIL (existence error)
# --------------------------------------------------------------------------- #
def test_phantom_column_fails(tmp_path: Path) -> None:
    contract = _make_node(
        tmp_path,
        node="node_projection_phantom",
        contract_yaml="""
        projection_api:
          expose: true
          exposures:
            - topic: decisions
              table: events
              columns:
                - id
                - this_column_does_not_exist
        """,
        migration_sql="CREATE TABLE events (id UUID PRIMARY KEY, correlation_id TEXT);",
    )
    findings = validate_contract(contract)
    errors = [f for f in findings if f.severity is EnumProjectionDriftSeverity.ERROR]
    assert len(errors) == 1
    assert errors[0].kind is EnumProjectionDriftKind.MISSING_COLUMN
    assert errors[0].column == "this_column_does_not_exist"
    assert errors[0].table == "events"


# --------------------------------------------------------------------------- #
# (b) omitted tier column → WARN  (the cost_tier_name bug)
# --------------------------------------------------------------------------- #
def test_omitted_tier_column_warns(tmp_path: Path) -> None:
    contract = _make_node(
        tmp_path,
        node="node_projection_delegation",
        contract_yaml="""
        projection_api:
          expose: true
          exposures:
            - topic: decisions
              table: delegation_events
              columns:
                - id
                - correlation_id
        """,
        migration_sql="""
        CREATE TABLE delegation_events (id UUID PRIMARY KEY, correlation_id TEXT);
        ALTER TABLE delegation_events
            ADD COLUMN IF NOT EXISTS cost_tier_name TEXT NOT NULL DEFAULT '';
        """,
    )
    findings = validate_contract(contract)
    errors = [f for f in findings if f.severity is EnumProjectionDriftSeverity.ERROR]
    warns = [f for f in findings if f.severity is EnumProjectionDriftSeverity.WARN]
    assert errors == []
    # correlation_id is exposed → not flagged; cost_tier_name omitted → flagged.
    omitted = {f.column for f in warns}
    assert "cost_tier_name" in omitted
    assert "correlation_id" not in omitted
    assert all(f.kind is EnumProjectionDriftKind.OMITTED_COLUMN for f in warns)


def test_omission_suppressed_by_allowlist(tmp_path: Path) -> None:
    contract = _make_node(
        tmp_path,
        node="node_projection_delegation",
        contract_yaml="""
        projection_api:
          expose: true
          exposures:
            - topic: decisions
              table: delegation_events
              columns:
                - id
        """,
        migration_sql="""
        CREATE TABLE delegation_events (id UUID PRIMARY KEY);
        ALTER TABLE delegation_events
            ADD COLUMN IF NOT EXISTS cost_tier_name TEXT NOT NULL DEFAULT '';
        """,
    )
    allowlist = tmp_path / ".projection-exposure-allowlist.yaml"
    allowlist.write_text(
        textwrap.dedent(
            """
            omissions:
              - node: node_projection_delegation
                table: delegation_events
                column: cost_tier_name
                reason: "internal tier discriminator; not surfaced (OMN-13663)"
            """
        ),
        encoding="utf-8",
    )
    loaded = load_allowlist(allowlist)
    findings = validate_contract(contract, loaded)
    assert findings == []


def test_unannotated_allowlist_entry_not_honored(tmp_path: Path) -> None:
    allowlist = tmp_path / "allow.yaml"
    allowlist.write_text(
        textwrap.dedent(
            """
            omissions:
              - node: node_x
                table: t
                column: cost_tier_name
            """
        ),
        encoding="utf-8",
    )
    # No reason → entry ignored, so the allowlist is empty.
    assert load_allowlist(allowlist) == set()


# --------------------------------------------------------------------------- #
# External-table exposure must not falsely block
# --------------------------------------------------------------------------- #
def test_external_table_not_falsely_blocked(tmp_path: Path) -> None:
    # No migrations dir → table DDL unknown → existence skipped (no error).
    contract = _make_node(
        tmp_path,
        node="node_projection_external",
        contract_yaml="""
        projection_api:
          expose: true
          exposures:
            - topic: decisions
              table: externally_defined_table
              columns:
                - anything
                - at_all
        """,
        migration_sql=None,
    )
    assert validate_contract(contract) == []


def test_json_columns_checked_for_existence(tmp_path: Path) -> None:
    contract = _make_node(
        tmp_path,
        node="node_projection_json",
        contract_yaml="""
        projection_api:
          expose: true
          exposures:
            - topic: summary
              table: summary_view
              columns:
                - '"byModel"'
              json_columns:
                - phantom_json
        """,
        migration_sql="""
        CREATE OR REPLACE VIEW summary_view AS
        SELECT by_model.rows AS "byModel" FROM by_model;
        """,
    )
    findings = validate_contract(contract)
    errors = [f for f in findings if f.severity is EnumProjectionDriftSeverity.ERROR]
    assert {f.column for f in errors} == {"phantom_json"}


# --------------------------------------------------------------------------- #
# Non-projection contracts are ignored
# --------------------------------------------------------------------------- #
def test_non_projection_contract_ignored(tmp_path: Path) -> None:
    contract = _make_node(
        tmp_path,
        node="node_plain",
        contract_yaml="""
        name: node_plain
        node_type: COMPUTE
        """,
    )
    assert validate_contract(contract) == []


# --------------------------------------------------------------------------- #
# CLI main() exit codes
# --------------------------------------------------------------------------- #
def test_main_exit_zero_on_clean_root(tmp_path: Path) -> None:
    _make_node(
        tmp_path,
        node="node_clean",
        contract_yaml="""
        projection_api:
          expose: true
          exposures:
            - topic: t
              table: events
              columns: [id]
        """,
        migration_sql="CREATE TABLE events (id UUID PRIMARY KEY);",
    )
    assert main([str(tmp_path)]) == 0


def test_main_exit_one_on_existence_error(tmp_path: Path) -> None:
    _make_node(
        tmp_path,
        node="node_bad",
        contract_yaml="""
        projection_api:
          expose: true
          exposures:
            - topic: t
              table: events
              columns: [id, ghost]
        """,
        migration_sql="CREATE TABLE events (id UUID PRIMARY KEY);",
    )
    assert main([str(tmp_path)]) == 1


def test_main_warns_only_by_default_but_fails_with_flag(tmp_path: Path) -> None:
    _make_node(
        tmp_path,
        node="node_omits",
        contract_yaml="""
        projection_api:
          expose: true
          exposures:
            - topic: t
              table: events
              columns: [id]
        """,
        migration_sql="""
        CREATE TABLE events (id UUID PRIMARY KEY, cost_tier_name TEXT);
        """,
    )
    # Default: omission is warn-only → exit 0.
    assert main([str(tmp_path)]) == 0
    # --fail-on-omission: omission becomes blocking → exit 1.
    assert main([str(tmp_path), "--fail-on-omission"]) == 1


def test_validate_root_discovers_multiple_contracts(tmp_path: Path) -> None:
    _make_node(
        tmp_path,
        node="node_a",
        contract_yaml="""
        projection_api:
          expose: true
          exposures:
            - topic: t
              table: events
              columns: [id, ghost]
        """,
        migration_sql="CREATE TABLE events (id UUID PRIMARY KEY);",
    )
    _make_node(
        tmp_path,
        node="node_b",
        contract_yaml="""
        projection_api:
          expose: true
          exposures:
            - topic: t
              table: rows
              columns: [missing]
        """,
        migration_sql="CREATE TABLE rows (id UUID PRIMARY KEY);",
    )
    findings = validate_root(tmp_path)
    errors = [f for f in findings if f.severity is EnumProjectionDriftSeverity.ERROR]
    assert {f.column for f in errors} == {"ghost", "missing"}
