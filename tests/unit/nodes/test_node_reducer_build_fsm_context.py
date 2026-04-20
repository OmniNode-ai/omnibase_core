# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Unit tests for NodeReducer._build_fsm_context.

Covers the OMN-592 context-construction contract:
- Builds context from ModelReducerInput (metadata + data + operation_id)
- System-assigned keys (input_data, reduction_type, operation_id) populated
- User metadata with reserved '_fsm_*' prefix is dropped with a warning
- User metadata that collides with system keys is dropped with a warning
- Non-colliding metadata keys are preserved
"""

from __future__ import annotations

import logging
from uuid import UUID

import pytest

from omnibase_core.enums.enum_reducer_types import EnumReductionType
from omnibase_core.models.common.model_reducer_metadata import ModelReducerMetadata
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.reducer.model_reducer_input import ModelReducerInput
from omnibase_core.nodes.node_reducer import NodeReducer

pytestmark = pytest.mark.unit


@pytest.fixture
def test_container() -> ModelONEXContainer:
    """Create a test container (no FSM contract needed for context build)."""
    return ModelONEXContainer()


@pytest.fixture
def reducer_node(test_container: ModelONEXContainer) -> NodeReducer[object, object]:
    """Create a NodeReducer instance.

    ``_build_fsm_context`` does not touch FSM state, so we do not need to
    install a state-machine contract on the instance for these tests.
    """
    return NodeReducer(test_container)


def _make_input(
    *,
    data: list[object] | None = None,
    metadata: ModelReducerMetadata | None = None,
    operation_id: UUID | None = None,
) -> ModelReducerInput[object]:
    """Create a ModelReducerInput with deterministic fields."""
    return ModelReducerInput(
        data=data if data is not None else [1, 2, 3],
        reduction_type=EnumReductionType.TRANSFORM,
        operation_id=operation_id or UUID("12345678-1234-5678-1234-567812345678"),
        metadata=metadata or ModelReducerMetadata(),
    )


class TestSystemAssignedContextKeys:
    """System-assigned keys must be present with correct values."""

    def test_context_contains_input_data_list(
        self, reducer_node: NodeReducer[object, object]
    ) -> None:
        data = [{"k": "v"}, {"k2": "v2"}]
        ctx = reducer_node._build_fsm_context(_make_input(data=data))
        assert ctx["input_data"] == data

    def test_context_contains_reduction_type_string(
        self, reducer_node: NodeReducer[object, object]
    ) -> None:
        ctx = reducer_node._build_fsm_context(_make_input())
        assert ctx["reduction_type"] == EnumReductionType.TRANSFORM.value

    def test_context_contains_operation_id_as_string(
        self, reducer_node: NodeReducer[object, object]
    ) -> None:
        op_id = UUID("00000000-0000-0000-0000-000000000001")
        ctx = reducer_node._build_fsm_context(_make_input(operation_id=op_id))
        assert ctx["operation_id"] == str(op_id)


class TestMetadataMerging:
    """Non-reserved, non-colliding metadata keys pass through."""

    def test_typed_metadata_fields_passed_through(
        self, reducer_node: NodeReducer[object, object]
    ) -> None:
        md = ModelReducerMetadata(
            source="unit-test",
            trace_id="trace-abc",
            correlation_id="corr-123",
            trigger="go",
            tags=["a", "b"],
        )
        ctx = reducer_node._build_fsm_context(_make_input(metadata=md))

        assert ctx["source"] == "unit-test"
        assert ctx["trace_id"] == "trace-abc"
        assert ctx["correlation_id"] == "corr-123"
        assert ctx["trigger"] == "go"
        assert ctx["tags"] == ["a", "b"]

    def test_extra_metadata_fields_passed_through(
        self, reducer_node: NodeReducer[object, object]
    ) -> None:
        # ModelReducerMetadata uses extra="allow"
        md = ModelReducerMetadata.model_validate(
            {"user_id": "u-1", "request_id": "r-1"}
        )
        ctx = reducer_node._build_fsm_context(_make_input(metadata=md))
        assert ctx["user_id"] == "u-1"
        assert ctx["request_id"] == "r-1"

    def test_none_metadata_fields_excluded(
        self, reducer_node: NodeReducer[object, object]
    ) -> None:
        # ``source`` default is None; it should NOT appear in the context.
        ctx = reducer_node._build_fsm_context(_make_input())
        assert "source" not in ctx
        assert "trace_id" not in ctx


class TestReservedFsmPrefix:
    """Keys starting with '_fsm_' are dropped + warning logged."""

    def test_reserved_prefix_key_dropped_from_context(
        self,
        reducer_node: NodeReducer[object, object],
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        md = ModelReducerMetadata.model_validate(
            {"_fsm_state": "injected", "_fsm_history": ["x"], "keep": "kept"}
        )
        with caplog.at_level(logging.WARNING):
            ctx = reducer_node._build_fsm_context(_make_input(metadata=md))

        assert "_fsm_state" not in ctx
        assert "_fsm_history" not in ctx
        # Non-reserved key preserved.
        assert ctx["keep"] == "kept"

    def test_reserved_prefix_emits_warning(
        self,
        reducer_node: NodeReducer[object, object],
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        md = ModelReducerMetadata.model_validate({"_fsm_something": 1})
        with caplog.at_level(logging.WARNING):
            reducer_node._build_fsm_context(_make_input(metadata=md))

        joined = "\n".join(rec.message for rec in caplog.records)
        assert "reserved" in joined.lower()
        assert "_fsm_" in joined

    def test_no_reserved_keys_no_warning(
        self,
        reducer_node: NodeReducer[object, object],
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        md = ModelReducerMetadata(source="src", trigger="t")
        with caplog.at_level(logging.WARNING):
            reducer_node._build_fsm_context(_make_input(metadata=md))

        # No reserved-prefix or collision warning should have been emitted.
        joined = "\n".join(rec.message for rec in caplog.records)
        assert "reserved" not in joined.lower()
        assert "colliding" not in joined.lower()


class TestSystemKeyCollision:
    """Metadata keys colliding with system-assigned keys are dropped + warning."""

    @pytest.mark.parametrize(
        "colliding_key",
        ["input_data", "reduction_type", "operation_id"],
    )
    def test_system_collision_uses_system_value(
        self,
        reducer_node: NodeReducer[object, object],
        caplog: pytest.LogCaptureFixture,
        colliding_key: str,
    ) -> None:
        # User tries to override a reserved system key.
        md = ModelReducerMetadata.model_validate({colliding_key: "USER_VALUE"})
        op_id = UUID("99999999-9999-9999-9999-999999999999")
        data = [10, 20]
        input_data = _make_input(data=data, metadata=md, operation_id=op_id)

        with caplog.at_level(logging.WARNING):
            ctx = reducer_node._build_fsm_context(input_data)

        # System values take precedence.
        assert ctx["input_data"] == data
        assert ctx["reduction_type"] == EnumReductionType.TRANSFORM.value
        assert ctx["operation_id"] == str(op_id)
        # The user-provided value must not have bled through.
        assert ctx[colliding_key] != "USER_VALUE"

    def test_system_collision_emits_warning(
        self,
        reducer_node: NodeReducer[object, object],
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        md = ModelReducerMetadata.model_validate({"operation_id": "pretend-override"})
        with caplog.at_level(logging.WARNING):
            reducer_node._build_fsm_context(_make_input(metadata=md))

        joined = "\n".join(rec.message for rec in caplog.records)
        assert "colliding" in joined.lower() or "system" in joined.lower()
        assert "operation_id" in joined


class TestContextPurity:
    """Successive builds must not leak state between calls."""

    def test_each_call_returns_fresh_dict(
        self, reducer_node: NodeReducer[object, object]
    ) -> None:
        md = ModelReducerMetadata(source="s")
        ctx1 = reducer_node._build_fsm_context(_make_input(metadata=md))
        ctx1["mutated"] = "should-not-persist"

        ctx2 = reducer_node._build_fsm_context(_make_input(metadata=md))
        assert "mutated" not in ctx2
