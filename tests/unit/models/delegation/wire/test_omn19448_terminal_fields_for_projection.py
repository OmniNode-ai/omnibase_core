# SPDX-FileCopyrightText: 2026 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OMN-19448: the terminal carries, unchanged, what delegation_events copies.

The projection in omnimarket copies the terminal's own cause, operational
outcome and content verdict onto the row (AC1), writes the trace from the
terminal (AC2), and a request refused before any dispatch lands on a typed
cause rather than NULL (AC3). Each of those starts from this wire model: a value
it drops or rewrites can never reach the row. These tests pin that the terminal
keeps each value through a JSON round trip, as the bus delivers it.
"""

from __future__ import annotations

import json
from uuid import uuid4

from omnibase_core.enums.enum_delegation_content_verdict import (
    EnumDelegationContentVerdict,
)
from omnibase_core.enums.enum_delegation_operational_outcome import (
    EnumDelegationOperationalOutcome,
)
from omnibase_core.enums.enum_delegation_terminal_failure_cause import (
    EnumDelegationTerminalFailureCause,
)
from omnibase_core.models.delegation.wire.model_delegation_result import (
    ModelDelegationResult,
)


def _failed_terminal(**overrides: object) -> ModelDelegationResult:
    fields: dict[str, object] = {
        "correlation_id": uuid4(),
        "task_type": "document",
        "model_used": "provider/model",
        "endpoint_url": "https://example.invalid/v1",
        "content": "",
        "quality_passed": False,
        "quality_score": None,
        "latency_ms": 0,
        "fallback_to_claude": False,
    }
    fields.update(overrides)
    return ModelDelegationResult(**fields)  # type: ignore[arg-type]


def _round_trip(terminal: ModelDelegationResult) -> dict[str, object]:
    wire = json.loads(json.dumps(terminal.model_dump(mode="json")))
    assert isinstance(wire, dict)
    return wire


def test_quality_gate_cause_outcome_and_verdict_survive_the_wire_unchanged() -> None:
    """AC1: the three values the projection copies leave the terminal unchanged."""
    terminal = _failed_terminal(
        terminal_failure_cause=EnumDelegationTerminalFailureCause.QUALITY_GATE_REFUSED,
        operational_outcome=EnumDelegationOperationalOutcome.QUALITY_REJECTED,
        content_verdict=EnumDelegationContentVerdict.UNUSABLE,
        content="an answer the quality gate refused",
        quality_score=0.2,
    )

    wire = _round_trip(terminal)

    assert wire["terminal_failure_cause"] == "quality_gate_refused"
    assert wire["operational_outcome"] == "quality_rejected"
    assert wire["content_verdict"] == "unusable"
    read_back = ModelDelegationResult.model_validate(wire)
    assert (
        read_back.terminal_failure_cause
        is EnumDelegationTerminalFailureCause.QUALITY_GATE_REFUSED
    )
    assert (
        read_back.operational_outcome
        is EnumDelegationOperationalOutcome.QUALITY_REJECTED
    )
    assert read_back.content_verdict is EnumDelegationContentVerdict.UNUSABLE


def test_trace_id_is_carried_on_the_terminal_the_row_is_written_from() -> None:
    """AC2: the trace column is written from the terminal, so the terminal keeps it."""
    trace_id = uuid4()

    wire = _round_trip(_failed_terminal(trace_id=trace_id))

    assert wire["trace_id"] == str(trace_id)
    assert ModelDelegationResult.model_validate(wire).trace_id == trace_id


def test_a_request_refused_before_dispatch_has_a_typed_cause_on_the_wire() -> None:
    """AC3: a pre-dispatch refusal names refused_before_dispatch, never a NULL cause."""
    terminal = _failed_terminal(
        terminal_failure_cause=EnumDelegationTerminalFailureCause.REFUSED_BEFORE_DISPATCH,
    )

    wire = _round_trip(terminal)

    assert wire["terminal_failure_cause"] == "refused_before_dispatch"
    read_back = ModelDelegationResult.model_validate(wire)
    assert (
        read_back.terminal_failure_cause
        is EnumDelegationTerminalFailureCause.REFUSED_BEFORE_DISPATCH
    )
