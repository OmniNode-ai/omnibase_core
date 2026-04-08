# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for ModelDbOwnershipSubcontract and ModelDbTableDeclaration."""

import pytest


def test_db_tables_field_exists():
    """Contract db_ownership_subcontract must support declaring owned tables with role."""
    from omnibase_core.models.contracts.subcontracts.model_db_ownership_subcontract import (
        ModelDbOwnershipSubcontract,
    )

    config = ModelDbOwnershipSubcontract(
        db_tables=[
            {
                "name": "delegation_events",
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
                "migration": "0007_delegation_events.sql",
                "access": "write",
                "role": "events",
            },
            {
                "name": "delegation_shadow_comparisons",
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
    """access field must be Literal['read','write','read_write']."""
    from omnibase_core.models.contracts.subcontracts.model_db_ownership_subcontract import (
        ModelDbTableDeclaration,
    )

    t = ModelDbTableDeclaration(
        name="llm_cost_aggregates",
        migration="0003_llm_cost_aggregates.sql",
        access="read_write",
        role="aggregates",
    )
    assert t.access == "read_write"

    with pytest.raises(Exception):
        ModelDbTableDeclaration(
            name="llm_cost_aggregates",
            migration="0003_llm_cost_aggregates.sql",
            access="invalid_access",  # type: ignore[arg-type]
            role="aggregates",
        )


def test_db_table_declaration_default_database():
    """database field must default to omnidash_analytics."""
    from omnibase_core.models.contracts.subcontracts.model_db_ownership_subcontract import (
        ModelDbTableDeclaration,
    )

    t = ModelDbTableDeclaration(
        name="session_outcomes",
        migration="0021_session_outcomes.sql",
        role="outcomes",
    )
    assert t.database == "omnidash_analytics"


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
