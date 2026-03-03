# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Unit tests for ModelTicketContextBundle."""

from datetime import UTC, datetime

import pytest

from omnibase_core.models.ticket.model_ticket_context_bundle import (
    ModelTCBEntrypoint,
    ModelTCBIntent,
    ModelTCBNormalizedIntent,
    ModelTicketContextBundle,
)


@pytest.mark.unit
def test_tcb_minimal_valid() -> None:
    """TCB can be created with only required fields."""
    tcb = ModelTicketContextBundle(
        tcb_version="0.1",
        ticket_id="OMN-1234",
        created_at=datetime(2026, 2, 28, tzinfo=UTC),
        ttl_days=7,
        intent=ModelTCBIntent(
            raw="Add FK validation to routing model",
            normalized=ModelTCBNormalizedIntent(
                repos=["omnibase_core"],
                modules=["routing"],
                capability_tags=["routing"],
                risk_tags=["integration"],
            ),
        ),
    )
    assert tcb.ticket_id == "OMN-1234"
    assert tcb.ttl_days == 7
    assert len(tcb.suggested_entrypoints) == 0


@pytest.mark.unit
def test_tcb_is_stale_after_ttl() -> None:
    """is_stale returns True when bundle is past TTL."""
    old_date = datetime(2026, 1, 1, tzinfo=UTC)
    tcb = ModelTicketContextBundle(
        tcb_version="0.1",
        ticket_id="OMN-999",
        created_at=old_date,
        ttl_days=7,
        intent=ModelTCBIntent(
            raw="old intent",
            normalized=ModelTCBNormalizedIntent(
                repos=["omniclaude"], modules=[], capability_tags=[], risk_tags=[]
            ),
        ),
    )
    assert tcb.is_stale() is True


@pytest.mark.unit
def test_tcb_entrypoint_confidence_bounds() -> None:
    """Entrypoint confidence must be 0.0-1.0."""
    with pytest.raises(ValueError):
        ModelTCBEntrypoint(
            kind="file",
            ref="src/foo.py",
            why="test",
            confidence=1.5,  # invalid
            provenance={"repo": "omnibase_core", "commit": "abc123"},
        )


@pytest.mark.unit
def test_tcb_size_cap_enforced() -> None:
    """Bundle rejects more than 10 suggested_entrypoints."""
    with pytest.raises(ValueError, match="suggested_entrypoints"):
        ModelTicketContextBundle(
            tcb_version="0.1",
            ticket_id="OMN-555",
            created_at=datetime(2026, 2, 28, tzinfo=UTC),
            ttl_days=7,
            intent=ModelTCBIntent(
                raw="too many",
                normalized=ModelTCBNormalizedIntent(
                    repos=["omnibase_core"],
                    modules=[],
                    capability_tags=[],
                    risk_tags=[],
                ),
            ),
            suggested_entrypoints=[
                ModelTCBEntrypoint(
                    kind="file",
                    ref=f"src/file_{i}.py",
                    why="test",
                    confidence=0.5,
                    provenance={"repo": "omnibase_core", "commit": "abc"},
                )
                for i in range(11)  # 11 items -- over the 10 cap
            ],
        )
