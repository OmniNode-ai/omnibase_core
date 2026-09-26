# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Validation coverage for the signed execution-graph terminal payload."""

from __future__ import annotations

from typing import Literal
from uuid import uuid4

import pytest

from omnibase_core.models.execution_graph_replay.model_execution_graph_terminal_refusal import (
    ModelExecutionGraphTerminalRefusal,
)
from omnibase_core.models.execution_graph_replay.model_execution_graph_terminal_result import (
    ModelExecutionGraphTerminalResult,
)


def test_failed_terminal_result_binds_request_identity_and_refusal() -> None:
    """A failure carries the tenant/correlation/workflow binding and a reason."""
    result = ModelExecutionGraphTerminalResult(
        tenant_id=uuid4(),
        correlation_id=uuid4(),
        workflow_type="delegation_execution_graph_read",
        status="failed",
        refusal=ModelExecutionGraphTerminalRefusal(
            code="ownership_denied",
            message="tenant does not own the requested correlation",
        ),
    )

    assert result.result is None
    assert result.refusal is not None


@pytest.mark.parametrize(
    ("status", "result", "refusal", "message"),
    [
        ("completed", None, None, "completed terminal result requires result"),
        (
            "failed",
            None,
            None,
            "failed terminal result requires refusal",
        ),
    ],
)
def test_terminal_result_refuses_ambiguous_terminal_shapes(
    status: Literal["completed", "failed"],
    result: None,
    refusal: ModelExecutionGraphTerminalRefusal | None,
    message: str,
) -> None:
    """A signed terminal payload cannot claim a terminal state without its body."""
    with pytest.raises(ValueError, match=message):
        ModelExecutionGraphTerminalResult(
            tenant_id=uuid4(),
            correlation_id=uuid4(),
            workflow_type="delegation_execution_graph_read",
            status=status,
            result=result,
            refusal=refusal,
        )


def test_terminal_refusal_rejects_blank_identity_fields() -> None:
    """Opaque refusal text cannot replace an actionable typed refusal identity."""
    with pytest.raises(ValueError):
        ModelExecutionGraphTerminalRefusal(code="", message="failure")


def test_terminal_result_rejects_blank_workflow_type() -> None:
    """A terminal payload cannot be bound to an unnamed workflow class."""
    with pytest.raises(ValueError):
        ModelExecutionGraphTerminalResult(
            tenant_id=uuid4(),
            correlation_id=uuid4(),
            workflow_type="",
            status="failed",
            refusal=ModelExecutionGraphTerminalRefusal(
                code="ownership_denied",
                message="tenant does not own the requested correlation",
            ),
        )
