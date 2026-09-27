# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for ModelDbOwnershipSubcontract and ModelDbTableDeclaration."""

import pytest
from pydantic import ValidationError

pytestmark = pytest.mark.unit


def test_db_tables_field_exists():
    """Contract db_ownership_subcontract must support declaring owned tables with role."""
    from omnibase_core.models.contracts.subcontracts.model_db_ownership_subcontract import (
        ModelDbOwnershipSubcontract,
    )

    config = ModelDbOwnershipSubcontract(
        db_tables=[
            {
                "name": "delegation_events",
                "database_ref": "application",
                "schema": "tenant",
                "migration": "0007_delegation_events.sql",
                "access": "write",
                "role": "events",
            },
        ]
    )
    assert len(config.db_tables) == 1
    assert config.db_tables[0].name == "delegation_events"
    assert config.db_tables[0].role == "events"


def test_db_tables_role_lookup():
    """Handlers must be able to resolve tables by semantic role."""
    from omnibase_core.models.contracts.subcontracts.model_db_ownership_subcontract import (
        ModelDbOwnershipSubcontract,
    )

    config = ModelDbOwnershipSubcontract(
        db_tables=[
            {
                "name": "delegation_events",
                "database_ref": "application",
                "schema": "tenant",
                "migration": "0007_delegation_events.sql",
                "access": "write",
                "role": "events",
            },
            {
                "name": "delegation_shadow_comparisons",
                "database_ref": "application",
                "schema": "tenant",
                "migration": "0007_delegation_events.sql",
                "access": "write",
                "role": "shadow_comparisons",
            },
        ]
    )
    by_role = {t.role: t for t in config.db_tables}
    assert by_role["events"].name == "delegation_events"
    assert by_role["shadow_comparisons"].name == "delegation_shadow_comparisons"


def test_db_tables_default_empty():
    """db_tables must default to an empty list (backwards compatible)."""
    from omnibase_core.models.contracts.subcontracts.model_db_ownership_subcontract import (
        ModelDbOwnershipSubcontract,
    )

    config = ModelDbOwnershipSubcontract()
    assert config.db_tables == []


def test_db_table_declaration_access_literal():
    """Unknown access modes must not enter a deployment contract."""
    from omnibase_core.models.contracts.subcontracts.model_db_ownership_subcontract import (
        ModelDbTableDeclaration,
    )

    t = ModelDbTableDeclaration(
        name="llm_cost_aggregates",
        database_ref="application",
        schema="omninode_internal",
        migration="0003_llm_cost_aggregates.sql",
        access="read_write",
        role="aggregates",
    )
    assert t.access == "read_write"

    with pytest.raises(Exception):
        ModelDbTableDeclaration(
            name="llm_cost_aggregates",
            database_ref="application",
            schema="omninode_internal",
            migration="0003_llm_cost_aggregates.sql",
            access="invalid_access",  # type: ignore[arg-type]
            role="aggregates",
        )


@pytest.mark.parametrize("access", ["read_insert", "read_write_delete"])
def test_new_access_modes_survive_contract_round_trip(access: str):
    """Deployment contracts must preserve both new modes for downstream grant checks."""
    from omnibase_core.models.contracts.subcontracts.model_db_ownership_subcontract import (
        ModelDbOwnershipSubcontract,
    )

    payload = {
        "db_tables": [
            {
                "name": "runner_fleet_liveness",
                "database_ref": "application",
                "schema": "omninode_internal",
                "migration": "0001_runner_fleet_liveness.sql",
                "access": access,
                "role": "liveness",
            }
        ]
    }
    contract = ModelDbOwnershipSubcontract.model_validate(payload)
    serialized = contract.model_dump(mode="json")

    assert serialized["db_tables"][0]["access"] == access
    assert ModelDbOwnershipSubcontract.model_validate(serialized) == contract


def test_db_table_declaration_requires_database_ref_and_schema():
    """Table location must be explicit; no physical-database default is allowed."""
    from omnibase_core.models.contracts.subcontracts.model_db_ownership_subcontract import (
        ModelDbTableDeclaration,
    )

    with pytest.raises(ValidationError):
        ModelDbTableDeclaration(
            name="session_outcomes",
            migration="0021_session_outcomes.sql",
            role="outcomes",
        )


def test_db_table_declaration_rejects_retired_database_field():
    """The retired physical database field cannot coexist with database_ref."""
    from omnibase_core.models.contracts.subcontracts.model_db_ownership_subcontract import (
        ModelDbTableDeclaration,
    )

    with pytest.raises(ValidationError, match="database"):
        ModelDbTableDeclaration(
            name="session_outcomes",
            database_ref="application",
            schema="tenant",
            migration="0021_session_outcomes.sql",
            role="outcomes",
            database="omnidash_analytics",  # type: ignore[call-arg]
        )


def test_exports_from_subcontracts_init():
    """Both types must be importable from the subcontracts __init__."""
    from omnibase_core.models.contracts.subcontracts import (
        ModelDbOwnershipSubcontract,
        ModelDbTableDeclaration,
    )

    assert ModelDbOwnershipSubcontract is not None
    assert ModelDbTableDeclaration is not None


def test_exports_from_contracts_init():
    """Both types must be importable from the contracts __init__."""
    from omnibase_core.models.contracts import (
        ModelDbOwnershipSubcontract,
        ModelDbTableDeclaration,
    )

    assert ModelDbOwnershipSubcontract is not None
    assert ModelDbTableDeclaration is not None
