# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for ModelDoctrineClause — OMN-11193."""

import pytest
from pydantic import ValidationError


@pytest.mark.unit
def test_model_doctrine_clause_create() -> None:
    from omnibase_core.models.governance.model_doctrine_clause import (
        ModelDoctrineClause,
    )

    clause = ModelDoctrineClause(
        clause_id="DT-001",
        title="Replay Determinism",
        check="All projections must replay deterministically",
        ci_gate="replay-determinism-check",
    )
    assert clause.clause_id == "DT-001"
    assert clause.title == "Replay Determinism"
    assert clause.adr is None
    assert clause.coverage == "uncovered"


@pytest.mark.unit
def test_model_doctrine_clause_with_adr() -> None:
    from omnibase_core.models.governance.model_doctrine_clause import (
        ModelDoctrineClause,
    )

    clause = ModelDoctrineClause(
        clause_id="DT-042",
        title="Event Ordering",
        check="Events must be ordered by sequence number",
        ci_gate="event-ordering-check",
        adr="docs/adrs/ADR-0012.md",
        coverage="covered",
    )
    assert clause.adr == "docs/adrs/ADR-0012.md"
    assert clause.coverage == "covered"


@pytest.mark.unit
def test_model_doctrine_clause_invalid_clause_id() -> None:
    from omnibase_core.models.governance.model_doctrine_clause import (
        ModelDoctrineClause,
    )

    with pytest.raises(ValidationError):
        ModelDoctrineClause(
            clause_id="INVALID",
            title="Bad ID",
            check="some check",
            ci_gate="some-gate",
        )


@pytest.mark.unit
def test_model_doctrine_clause_invalid_clause_id_short() -> None:
    from omnibase_core.models.governance.model_doctrine_clause import (
        ModelDoctrineClause,
    )

    with pytest.raises(ValidationError):
        ModelDoctrineClause(
            clause_id="DT-1",
            title="Too short",
            check="some check",
            ci_gate="some-gate",
        )


@pytest.mark.unit
def test_model_doctrine_clause_frozen() -> None:
    from omnibase_core.models.governance.model_doctrine_clause import (
        ModelDoctrineClause,
    )

    clause = ModelDoctrineClause(
        clause_id="DT-099",
        title="Immutable",
        check="Must not mutate",
        ci_gate="immutability-check",
    )
    with pytest.raises(Exception):
        clause.title = "Changed"  # type: ignore[misc]  # NOTE(OMN-11193): intentional forbidden assignment to verify frozen model rejects mutation.
