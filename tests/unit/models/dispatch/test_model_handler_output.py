# SPDX-License-Identifier: MIT
# Copyright (c) 2025 OmniNode Team
"""
Comprehensive tests for ModelHandlerOutput.

Tests cover:
- Basic field validation (required fields, defaults, immutability)
- Option A node-kind constraints (ORCHESTRATOR, REDUCER, EFFECT, COMPUTE)
- Builder methods (for_orchestrator, for_reducer, for_effect, for_compute, empty)
- Correlation ID preservation requirements
- Convenience methods (has_outputs, output_count, has_metrics, has_logs)

OMN-941: Standardize handler output model
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import BaseModel, ValidationError

from omnibase_core.enums.enum_node_kind import EnumNodeKind
from omnibase_core.models.dispatch.model_handler_output import ModelHandlerOutput

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_envelope_id():
    """Create a sample input envelope ID."""
    return uuid4()


@pytest.fixture
def sample_correlation_id():
    """Create a sample correlation ID."""
    return uuid4()


@pytest.fixture
def sample_handler_id():
    """Create a sample handler ID."""
    return "test-handler-001"


@pytest.fixture
def sample_event():
    """Create a sample event object for testing."""
    return {"type": "UserCreated", "payload": {"user_id": "123"}}


@pytest.fixture
def sample_intent():
    """Create a sample intent object for testing."""
    return {"action": "SendEmail", "target": "user@example.com"}


@pytest.fixture
def sample_projection():
    """Create a sample projection object for testing."""
    return {"entity": "User", "id": "123", "state": {"name": "Test User"}}


# ============================================================================
# Basic Field Validation Tests
# ============================================================================


@pytest.mark.unit
class TestModelHandlerOutputBasic:
    """Test basic field validation."""

    def test_create_minimal_valid_output(
        self, sample_envelope_id, sample_correlation_id, sample_handler_id
    ) -> None:
        """Test creating a valid ModelHandlerOutput with minimal required fields."""
        output = ModelHandlerOutput(
            input_envelope_id=sample_envelope_id,
            correlation_id=sample_correlation_id,
            handler_id=sample_handler_id,
            node_kind=EnumNodeKind.EFFECT,
        )

        assert output.input_envelope_id == sample_envelope_id
        assert output.correlation_id == sample_correlation_id
        assert output.handler_id == sample_handler_id
        assert output.node_kind == EnumNodeKind.EFFECT

    def test_required_field_input_envelope_id(
        self, sample_correlation_id, sample_handler_id
    ) -> None:
        """Test that input_envelope_id is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelHandlerOutput(
                correlation_id=sample_correlation_id,
                handler_id=sample_handler_id,
                node_kind=EnumNodeKind.EFFECT,
            )
        assert "input_envelope_id" in str(exc_info.value)

    def test_required_field_correlation_id(
        self, sample_envelope_id, sample_handler_id
    ) -> None:
        """Test that correlation_id is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelHandlerOutput(
                input_envelope_id=sample_envelope_id,
                handler_id=sample_handler_id,
                node_kind=EnumNodeKind.EFFECT,
            )
        assert "correlation_id" in str(exc_info.value)

    def test_required_field_handler_id(
        self, sample_envelope_id, sample_correlation_id
    ) -> None:
        """Test that handler_id is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelHandlerOutput(
                input_envelope_id=sample_envelope_id,
                correlation_id=sample_correlation_id,
                node_kind=EnumNodeKind.EFFECT,
            )
        assert "handler_id" in str(exc_info.value)

    def test_required_field_node_kind(
        self, sample_envelope_id, sample_correlation_id, sample_handler_id
    ) -> None:
        """Test that node_kind is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelHandlerOutput(
                input_envelope_id=sample_envelope_id,
                correlation_id=sample_correlation_id,
                handler_id=sample_handler_id,
            )
        assert "node_kind" in str(exc_info.value)

    def test_default_empty_tuples(
        self, sample_envelope_id, sample_correlation_id, sample_handler_id
    ) -> None:
        """Test that events, intents, and projections default to empty tuples."""
        output = ModelHandlerOutput(
            input_envelope_id=sample_envelope_id,
            correlation_id=sample_correlation_id,
            handler_id=sample_handler_id,
            node_kind=EnumNodeKind.EFFECT,
        )

        assert output.events == ()
        assert output.intents == ()
        assert output.projections == ()

    def test_default_empty_metrics(
        self, sample_envelope_id, sample_correlation_id, sample_handler_id
    ) -> None:
        """Test that metrics defaults to empty dict."""
        output = ModelHandlerOutput(
            input_envelope_id=sample_envelope_id,
            correlation_id=sample_correlation_id,
            handler_id=sample_handler_id,
            node_kind=EnumNodeKind.EFFECT,
        )

        assert output.metrics == {}

    def test_default_empty_logs(
        self, sample_envelope_id, sample_correlation_id, sample_handler_id
    ) -> None:
        """Test that logs defaults to empty tuple."""
        output = ModelHandlerOutput(
            input_envelope_id=sample_envelope_id,
            correlation_id=sample_correlation_id,
            handler_id=sample_handler_id,
            node_kind=EnumNodeKind.EFFECT,
        )

        assert output.logs == ()

    def test_default_processing_time_ms(
        self, sample_envelope_id, sample_correlation_id, sample_handler_id
    ) -> None:
        """Test that processing_time_ms defaults to 0.0."""
        output = ModelHandlerOutput(
            input_envelope_id=sample_envelope_id,
            correlation_id=sample_correlation_id,
            handler_id=sample_handler_id,
            node_kind=EnumNodeKind.EFFECT,
        )

        assert output.processing_time_ms == 0.0

    def test_timestamp_auto_generated(
        self, sample_envelope_id, sample_correlation_id, sample_handler_id
    ) -> None:
        """Test that timestamp is auto-generated with UTC timezone."""
        before = datetime.now(UTC)
        output = ModelHandlerOutput(
            input_envelope_id=sample_envelope_id,
            correlation_id=sample_correlation_id,
            handler_id=sample_handler_id,
            node_kind=EnumNodeKind.EFFECT,
        )
        after = datetime.now(UTC)

        assert before <= output.timestamp <= after

    def test_frozen_immutability(
        self, sample_envelope_id, sample_correlation_id, sample_handler_id
    ) -> None:
        """Test that ModelHandlerOutput is immutable (frozen=True)."""
        output = ModelHandlerOutput(
            input_envelope_id=sample_envelope_id,
            correlation_id=sample_correlation_id,
            handler_id=sample_handler_id,
            node_kind=EnumNodeKind.EFFECT,
        )

        with pytest.raises(ValidationError):
            output.handler_id = "modified"  # type: ignore[misc]

    def test_handler_id_min_length(
        self, sample_envelope_id, sample_correlation_id
    ) -> None:
        """Test that handler_id must have at least 1 character."""
        with pytest.raises(ValidationError) as exc_info:
            ModelHandlerOutput(
                input_envelope_id=sample_envelope_id,
                correlation_id=sample_correlation_id,
                handler_id="",  # Empty string
                node_kind=EnumNodeKind.EFFECT,
            )
        assert "handler_id" in str(exc_info.value)

    def test_handler_id_max_length(
        self, sample_envelope_id, sample_correlation_id
    ) -> None:
        """Test that handler_id has a maximum length of 200."""
        with pytest.raises(ValidationError) as exc_info:
            ModelHandlerOutput(
                input_envelope_id=sample_envelope_id,
                correlation_id=sample_correlation_id,
                handler_id="x" * 201,  # 201 characters
                node_kind=EnumNodeKind.EFFECT,
            )
        assert "handler_id" in str(exc_info.value)

    def test_processing_time_ms_non_negative(
        self, sample_envelope_id, sample_correlation_id, sample_handler_id
    ) -> None:
        """Test that processing_time_ms must be non-negative."""
        with pytest.raises(ValidationError) as exc_info:
            ModelHandlerOutput(
                input_envelope_id=sample_envelope_id,
                correlation_id=sample_correlation_id,
                handler_id=sample_handler_id,
                node_kind=EnumNodeKind.EFFECT,
                processing_time_ms=-1.0,
            )
        assert "processing_time_ms" in str(exc_info.value)


# ============================================================================
# Option A Node-Kind Constraints Tests
# ============================================================================


@pytest.mark.unit
class TestModelHandlerOutputOptionAConstraints:
    """Test Option A node-kind constraints."""

    # ---- ORCHESTRATOR: events[] + intents[] allowed, projections[] forbidden ----

    def test_orchestrator_can_emit_events(
        self, sample_envelope_id, sample_correlation_id, sample_handler_id, sample_event
    ) -> None:
        """Test that ORCHESTRATOR can emit events."""
        output = ModelHandlerOutput(
            input_envelope_id=sample_envelope_id,
            correlation_id=sample_correlation_id,
            handler_id=sample_handler_id,
            node_kind=EnumNodeKind.ORCHESTRATOR,
            events=(sample_event,),
        )

        assert len(output.events) == 1
        assert output.events[0] == sample_event

    def test_orchestrator_can_emit_intents(
        self,
        sample_envelope_id,
        sample_correlation_id,
        sample_handler_id,
        sample_intent,
    ) -> None:
        """Test that ORCHESTRATOR can emit intents."""
        output = ModelHandlerOutput(
            input_envelope_id=sample_envelope_id,
            correlation_id=sample_correlation_id,
            handler_id=sample_handler_id,
            node_kind=EnumNodeKind.ORCHESTRATOR,
            intents=(sample_intent,),
        )

        assert len(output.intents) == 1
        assert output.intents[0] == sample_intent

    def test_orchestrator_can_emit_events_and_intents(
        self,
        sample_envelope_id,
        sample_correlation_id,
        sample_handler_id,
        sample_event,
        sample_intent,
    ) -> None:
        """Test that ORCHESTRATOR can emit both events and intents."""
        output = ModelHandlerOutput(
            input_envelope_id=sample_envelope_id,
            correlation_id=sample_correlation_id,
            handler_id=sample_handler_id,
            node_kind=EnumNodeKind.ORCHESTRATOR,
            events=(sample_event,),
            intents=(sample_intent,),
        )

        assert len(output.events) == 1
        assert len(output.intents) == 1

    def test_orchestrator_fails_on_projections(
        self,
        sample_envelope_id,
        sample_correlation_id,
        sample_handler_id,
        sample_projection,
    ) -> None:
        """Test that ORCHESTRATOR fails when emitting projections."""
        with pytest.raises(ValueError) as exc_info:
            ModelHandlerOutput(
                input_envelope_id=sample_envelope_id,
                correlation_id=sample_correlation_id,
                handler_id=sample_handler_id,
                node_kind=EnumNodeKind.ORCHESTRATOR,
                projections=(sample_projection,),
            )
        assert "ORCHESTRATOR cannot emit projections[]" in str(exc_info.value)

    def test_orchestrator_cannot_set_result(
        self,
        sample_envelope_id,
        sample_correlation_id,
        sample_handler_id,
    ) -> None:
        """ORCHESTRATOR cannot set result - use events[] and intents[] only."""
        with pytest.raises(ValueError) as exc_info:
            ModelHandlerOutput(
                input_envelope_id=sample_envelope_id,
                correlation_id=sample_correlation_id,
                handler_id=sample_handler_id,
                node_kind=EnumNodeKind.ORCHESTRATOR,
                result={"some": "data"},
            )
        error_msg = str(exc_info.value)
        assert "ORCHESTRATOR cannot set result" in error_msg

    # ---- REDUCER: projections[] allowed, events[] and intents[] forbidden ----

    def test_reducer_can_emit_projections(
        self,
        sample_envelope_id,
        sample_correlation_id,
        sample_handler_id,
        sample_projection,
    ) -> None:
        """Test that REDUCER can emit projections."""
        output = ModelHandlerOutput(
            input_envelope_id=sample_envelope_id,
            correlation_id=sample_correlation_id,
            handler_id=sample_handler_id,
            node_kind=EnumNodeKind.REDUCER,
            projections=(sample_projection,),
        )

        assert len(output.projections) == 1
        assert output.projections[0] == sample_projection

    def test_reducer_fails_on_events(
        self, sample_envelope_id, sample_correlation_id, sample_handler_id, sample_event
    ) -> None:
        """Test that REDUCER fails when emitting events."""
        with pytest.raises(ValueError) as exc_info:
            ModelHandlerOutput(
                input_envelope_id=sample_envelope_id,
                correlation_id=sample_correlation_id,
                handler_id=sample_handler_id,
                node_kind=EnumNodeKind.REDUCER,
                events=(sample_event,),
            )
        assert "REDUCER cannot emit events[]" in str(exc_info.value)

    def test_reducer_fails_on_intents(
        self,
        sample_envelope_id,
        sample_correlation_id,
        sample_handler_id,
        sample_intent,
    ) -> None:
        """Test that REDUCER fails when emitting intents."""
        with pytest.raises(ValueError) as exc_info:
            ModelHandlerOutput(
                input_envelope_id=sample_envelope_id,
                correlation_id=sample_correlation_id,
                handler_id=sample_handler_id,
                node_kind=EnumNodeKind.REDUCER,
                intents=(sample_intent,),
            )
        assert "REDUCER cannot emit intents[]" in str(exc_info.value)

    # ---- EFFECT: events[] allowed, intents[] and projections[] forbidden ----

    def test_effect_can_emit_events(
        self, sample_envelope_id, sample_correlation_id, sample_handler_id, sample_event
    ) -> None:
        """Test that EFFECT can emit events."""
        output = ModelHandlerOutput(
            input_envelope_id=sample_envelope_id,
            correlation_id=sample_correlation_id,
            handler_id=sample_handler_id,
            node_kind=EnumNodeKind.EFFECT,
            events=(sample_event,),
        )

        assert len(output.events) == 1
        assert output.events[0] == sample_event

    def test_effect_fails_on_intents(
        self,
        sample_envelope_id,
        sample_correlation_id,
        sample_handler_id,
        sample_intent,
    ) -> None:
        """Test that EFFECT fails when emitting intents."""
        with pytest.raises(ValueError) as exc_info:
            ModelHandlerOutput(
                input_envelope_id=sample_envelope_id,
                correlation_id=sample_correlation_id,
                handler_id=sample_handler_id,
                node_kind=EnumNodeKind.EFFECT,
                intents=(sample_intent,),
            )
        assert "EFFECT cannot emit intents[]" in str(exc_info.value)

    def test_effect_fails_on_projections(
        self,
        sample_envelope_id,
        sample_correlation_id,
        sample_handler_id,
        sample_projection,
    ) -> None:
        """Test that EFFECT fails when emitting projections."""
        with pytest.raises(ValueError) as exc_info:
            ModelHandlerOutput(
                input_envelope_id=sample_envelope_id,
                correlation_id=sample_correlation_id,
                handler_id=sample_handler_id,
                node_kind=EnumNodeKind.EFFECT,
                projections=(sample_projection,),
            )
        assert "EFFECT cannot emit projections[]" in str(exc_info.value)

    # ---- COMPUTE: result only, events[], intents[], and projections[] forbidden ----
    # (Updated per OMN-941: COMPUTE nodes are pure transformations returning result only)

    def test_compute_fails_on_events(
        self, sample_envelope_id, sample_correlation_id, sample_handler_id, sample_event
    ) -> None:
        """Test that COMPUTE fails when emitting events (OMN-941 constraint)."""
        with pytest.raises(ValueError) as exc_info:
            ModelHandlerOutput(
                input_envelope_id=sample_envelope_id,
                correlation_id=sample_correlation_id,
                handler_id=sample_handler_id,
                node_kind=EnumNodeKind.COMPUTE,
                result="some_result",  # COMPUTE requires result
                events=(sample_event,),  # COMPUTE cannot emit events
            )
        assert "COMPUTE cannot emit events[]" in str(exc_info.value)

    def test_compute_fails_on_intents(
        self,
        sample_envelope_id,
        sample_correlation_id,
        sample_handler_id,
        sample_intent,
    ) -> None:
        """Test that COMPUTE fails when emitting intents."""
        with pytest.raises(ValueError) as exc_info:
            ModelHandlerOutput(
                input_envelope_id=sample_envelope_id,
                correlation_id=sample_correlation_id,
                handler_id=sample_handler_id,
                node_kind=EnumNodeKind.COMPUTE,
                result="some_result",  # COMPUTE requires result
                intents=(sample_intent,),
            )
        assert "COMPUTE cannot emit intents[]" in str(exc_info.value)

    def test_compute_fails_on_projections(
        self,
        sample_envelope_id,
        sample_correlation_id,
        sample_handler_id,
        sample_projection,
    ) -> None:
        """Test that COMPUTE fails when emitting projections."""
        with pytest.raises(ValueError) as exc_info:
            ModelHandlerOutput(
                input_envelope_id=sample_envelope_id,
                correlation_id=sample_correlation_id,
                handler_id=sample_handler_id,
                node_kind=EnumNodeKind.COMPUTE,
                result="some_result",  # COMPUTE requires result
                projections=(sample_projection,),
            )
        assert "COMPUTE cannot emit projections[]" in str(exc_info.value)

    # ---- RUNTIME_HOST: No specific constraints ----

    def test_runtime_host_has_no_constraints(
        self,
        sample_envelope_id,
        sample_correlation_id,
        sample_handler_id,
        sample_event,
        sample_intent,
        sample_projection,
    ) -> None:
        """Test that RUNTIME_HOST has no specific constraints."""
        # RUNTIME_HOST is infrastructure and typically wouldn't be used as a handler,
        # but the model doesn't explicitly block any output combination
        output = ModelHandlerOutput(
            input_envelope_id=sample_envelope_id,
            correlation_id=sample_correlation_id,
            handler_id=sample_handler_id,
            node_kind=EnumNodeKind.RUNTIME_HOST,
            events=(sample_event,),
            intents=(sample_intent,),
            projections=(sample_projection,),
        )

        assert len(output.events) == 1
        assert len(output.intents) == 1
        assert len(output.projections) == 1


# ============================================================================
# Builder Methods Tests
# ============================================================================


@pytest.mark.unit
class TestModelHandlerOutputBuilderMethods:
    """Test builder methods."""

    def test_for_orchestrator_creates_valid_output(
        self, sample_envelope_id, sample_correlation_id, sample_handler_id, sample_event
    ) -> None:
        """Test for_orchestrator creates valid ORCHESTRATOR output."""
        output = ModelHandlerOutput.for_orchestrator(
            input_envelope_id=sample_envelope_id,
            correlation_id=sample_correlation_id,
            handler_id=sample_handler_id,
            events=(sample_event,),
        )

        assert output.node_kind == EnumNodeKind.ORCHESTRATOR
        assert output.input_envelope_id == sample_envelope_id
        assert output.correlation_id == sample_correlation_id
        assert output.handler_id == sample_handler_id
        assert len(output.events) == 1

    def test_for_orchestrator_with_intents(
        self,
        sample_envelope_id,
        sample_correlation_id,
        sample_handler_id,
        sample_intent,
    ) -> None:
        """Test for_orchestrator with intents."""
        output = ModelHandlerOutput.for_orchestrator(
            input_envelope_id=sample_envelope_id,
            correlation_id=sample_correlation_id,
            handler_id=sample_handler_id,
            intents=(sample_intent,),
        )

        assert output.node_kind == EnumNodeKind.ORCHESTRATOR
        assert len(output.intents) == 1

    def test_for_orchestrator_with_metrics(
        self, sample_envelope_id, sample_correlation_id, sample_handler_id
    ) -> None:
        """Test for_orchestrator with metrics."""
        metrics = {"events_processed": 10.0, "duration_ms": 50.5}
        output = ModelHandlerOutput.for_orchestrator(
            input_envelope_id=sample_envelope_id,
            correlation_id=sample_correlation_id,
            handler_id=sample_handler_id,
            metrics=metrics,
        )

        assert output.metrics == metrics

    def test_for_orchestrator_metrics_default_behavior(
        self, sample_envelope_id, sample_correlation_id, sample_handler_id
    ) -> None:
        """Test that metrics parameter defaults correctly for None and empty dict.

        This verifies the `metrics or {}` pattern:
        - metrics=None → {}
        - metrics={} → {}
        - No metrics parameter → {}
        """
        # Case 1: Explicit None
        output_none = ModelHandlerOutput.for_orchestrator(
            input_envelope_id=sample_envelope_id,
            correlation_id=sample_correlation_id,
            handler_id=sample_handler_id,
            metrics=None,
        )
        assert output_none.metrics == {}

        # Case 2: Explicit empty dict
        output_empty = ModelHandlerOutput.for_orchestrator(
            input_envelope_id=sample_envelope_id,
            correlation_id=sample_correlation_id,
            handler_id=sample_handler_id,
            metrics={},
        )
        assert output_empty.metrics == {}

        # Case 3: No metrics parameter (default)
        output_default = ModelHandlerOutput.for_orchestrator(
            input_envelope_id=sample_envelope_id,
            correlation_id=sample_correlation_id,
            handler_id=sample_handler_id,
        )
        assert output_default.metrics == {}

        # All three should produce the same result
        assert output_none.metrics == output_empty.metrics == output_default.metrics

    def test_for_orchestrator_with_logs(
        self, sample_envelope_id, sample_correlation_id, sample_handler_id
    ) -> None:
        """Test for_orchestrator with logs."""
        logs = ("Started processing", "Processing complete")
        output = ModelHandlerOutput.for_orchestrator(
            input_envelope_id=sample_envelope_id,
            correlation_id=sample_correlation_id,
            handler_id=sample_handler_id,
            logs=logs,
        )

        assert output.logs == logs

    def test_for_reducer_creates_valid_output(
        self,
        sample_envelope_id,
        sample_correlation_id,
        sample_handler_id,
        sample_projection,
    ) -> None:
        """Test for_reducer creates valid REDUCER output."""
        output = ModelHandlerOutput.for_reducer(
            input_envelope_id=sample_envelope_id,
            correlation_id=sample_correlation_id,
            handler_id=sample_handler_id,
            projections=(sample_projection,),
        )

        assert output.node_kind == EnumNodeKind.REDUCER
        assert output.input_envelope_id == sample_envelope_id
        assert output.correlation_id == sample_correlation_id
        assert output.handler_id == sample_handler_id
        assert len(output.projections) == 1

    def test_for_reducer_with_processing_time(
        self, sample_envelope_id, sample_correlation_id, sample_handler_id
    ) -> None:
        """Test for_reducer with processing time."""
        output = ModelHandlerOutput.for_reducer(
            input_envelope_id=sample_envelope_id,
            correlation_id=sample_correlation_id,
            handler_id=sample_handler_id,
            processing_time_ms=123.45,
        )

        assert output.processing_time_ms == 123.45

    def test_for_effect_creates_valid_output(
        self, sample_envelope_id, sample_correlation_id, sample_handler_id, sample_event
    ) -> None:
        """Test for_effect creates valid EFFECT output."""
        output = ModelHandlerOutput.for_effect(
            input_envelope_id=sample_envelope_id,
            correlation_id=sample_correlation_id,
            handler_id=sample_handler_id,
            events=(sample_event,),
        )

        assert output.node_kind == EnumNodeKind.EFFECT
        assert output.input_envelope_id == sample_envelope_id
        assert output.correlation_id == sample_correlation_id
        assert output.handler_id == sample_handler_id
        assert len(output.events) == 1

    def test_for_effect_empty_events(
        self, sample_envelope_id, sample_correlation_id, sample_handler_id
    ) -> None:
        """Test for_effect with no events (valid for filtering/idempotent handlers)."""
        output = ModelHandlerOutput.for_effect(
            input_envelope_id=sample_envelope_id,
            correlation_id=sample_correlation_id,
            handler_id=sample_handler_id,
        )

        assert output.node_kind == EnumNodeKind.EFFECT
        assert output.events == ()

    def test_for_compute_creates_valid_output(
        self, sample_envelope_id, sample_correlation_id, sample_handler_id
    ) -> None:
        """Test for_compute creates valid COMPUTE output (OMN-941 updated)."""
        output = ModelHandlerOutput.for_compute(
            input_envelope_id=sample_envelope_id,
            correlation_id=sample_correlation_id,
            handler_id=sample_handler_id,
            result={"computed": "value"},  # COMPUTE requires result
        )

        assert output.node_kind == EnumNodeKind.COMPUTE
        assert output.input_envelope_id == sample_envelope_id
        assert output.correlation_id == sample_correlation_id
        assert output.handler_id == sample_handler_id
        assert output.result == {"computed": "value"}
        assert output.has_result() is True

    def test_for_compute_with_dict_result(
        self, sample_envelope_id, sample_correlation_id, sample_handler_id
    ) -> None:
        """Test for_compute with dict result (OMN-941 updated)."""
        result = {
            "data_enriched": {"id": "1"},
            "data_validated": {"id": "2"},
        }
        output = ModelHandlerOutput.for_compute(
            input_envelope_id=sample_envelope_id,
            correlation_id=sample_correlation_id,
            handler_id=sample_handler_id,
            result=result,
        )

        assert output.result == result
        assert output.has_result() is True

    def test_empty_creates_valid_output(
        self, sample_envelope_id, sample_correlation_id, sample_handler_id
    ) -> None:
        """Test empty creates valid output with no outputs."""
        output = ModelHandlerOutput.empty(
            input_envelope_id=sample_envelope_id,
            correlation_id=sample_correlation_id,
            handler_id=sample_handler_id,
            node_kind=EnumNodeKind.COMPUTE,
        )

        assert output.input_envelope_id == sample_envelope_id
        assert output.correlation_id == sample_correlation_id
        assert output.handler_id == sample_handler_id
        assert output.node_kind == EnumNodeKind.COMPUTE
        assert output.events == ()
        assert output.intents == ()
        assert output.projections == ()

    def test_empty_with_processing_time(
        self, sample_envelope_id, sample_correlation_id, sample_handler_id
    ) -> None:
        """Test empty with processing time."""
        output = ModelHandlerOutput.empty(
            input_envelope_id=sample_envelope_id,
            correlation_id=sample_correlation_id,
            handler_id=sample_handler_id,
            node_kind=EnumNodeKind.EFFECT,
            processing_time_ms=5.0,
        )

        assert output.processing_time_ms == 5.0
        assert output.has_outputs() is False

    def test_empty_for_all_node_kinds(
        self, sample_envelope_id, sample_correlation_id, sample_handler_id
    ) -> None:
        """Test empty works for all core node kinds."""
        for node_kind in [
            EnumNodeKind.ORCHESTRATOR,
            EnumNodeKind.REDUCER,
            EnumNodeKind.EFFECT,
            EnumNodeKind.COMPUTE,
        ]:
            output = ModelHandlerOutput.empty(
                input_envelope_id=sample_envelope_id,
                correlation_id=sample_correlation_id,
                handler_id=sample_handler_id,
                node_kind=node_kind,
            )

            assert output.node_kind == node_kind
            assert output.has_outputs() is False


# ============================================================================
# Correlation ID Preservation Tests
# ============================================================================


@pytest.mark.unit
class TestModelHandlerOutputCorrelation:
    """Test correlation ID preservation."""

    def test_correlation_id_must_be_provided(self, sample_envelope_id) -> None:
        """Test that correlation_id MUST be provided (no default factory)."""
        with pytest.raises(ValidationError) as exc_info:
            ModelHandlerOutput(
                input_envelope_id=sample_envelope_id,
                handler_id="test-handler",
                node_kind=EnumNodeKind.EFFECT,
            )
        assert "correlation_id" in str(exc_info.value)

    def test_input_envelope_id_must_be_provided(self, sample_correlation_id) -> None:
        """Test that input_envelope_id MUST be provided."""
        with pytest.raises(ValidationError) as exc_info:
            ModelHandlerOutput(
                correlation_id=sample_correlation_id,
                handler_id="test-handler",
                node_kind=EnumNodeKind.EFFECT,
            )
        assert "input_envelope_id" in str(exc_info.value)

    def test_correlation_id_preserved_in_output(
        self, sample_envelope_id, sample_handler_id
    ) -> None:
        """Test that correlation_id is preserved exactly as provided."""
        correlation_id = uuid4()

        output = ModelHandlerOutput(
            input_envelope_id=sample_envelope_id,
            correlation_id=correlation_id,
            handler_id=sample_handler_id,
            node_kind=EnumNodeKind.EFFECT,
        )

        assert output.correlation_id == correlation_id

    def test_input_envelope_id_preserved_in_output(
        self, sample_correlation_id, sample_handler_id
    ) -> None:
        """Test that input_envelope_id is preserved exactly as provided."""
        envelope_id = uuid4()

        output = ModelHandlerOutput(
            input_envelope_id=envelope_id,
            correlation_id=sample_correlation_id,
            handler_id=sample_handler_id,
            node_kind=EnumNodeKind.EFFECT,
        )

        assert output.input_envelope_id == envelope_id

    def test_builder_methods_preserve_correlation_id(self) -> None:
        """Test that all builder methods preserve correlation_id."""
        envelope_id = uuid4()
        correlation_id = uuid4()
        handler_id = "test-handler"

        # Test all builder methods
        orchestrator_output = ModelHandlerOutput.for_orchestrator(
            input_envelope_id=envelope_id,
            correlation_id=correlation_id,
            handler_id=handler_id,
        )
        assert orchestrator_output.correlation_id == correlation_id

        reducer_output = ModelHandlerOutput.for_reducer(
            input_envelope_id=envelope_id,
            correlation_id=correlation_id,
            handler_id=handler_id,
        )
        assert reducer_output.correlation_id == correlation_id

        effect_output = ModelHandlerOutput.for_effect(
            input_envelope_id=envelope_id,
            correlation_id=correlation_id,
            handler_id=handler_id,
        )
        assert effect_output.correlation_id == correlation_id

        compute_output = ModelHandlerOutput.for_compute(
            input_envelope_id=envelope_id,
            correlation_id=correlation_id,
            handler_id=handler_id,
            result="test_result",  # COMPUTE requires result (OMN-941)
        )
        assert compute_output.correlation_id == correlation_id

        empty_output = ModelHandlerOutput.empty(
            input_envelope_id=envelope_id,
            correlation_id=correlation_id,
            handler_id=handler_id,
            node_kind=EnumNodeKind.EFFECT,
        )
        assert empty_output.correlation_id == correlation_id


# ============================================================================
# Convenience Methods Tests
# ============================================================================


@pytest.mark.unit
class TestModelHandlerOutputConvenienceMethods:
    """Test convenience methods."""

    def test_has_outputs_false_when_empty(
        self, sample_envelope_id, sample_correlation_id, sample_handler_id
    ) -> None:
        """Test has_outputs returns False when all collections are empty."""
        output = ModelHandlerOutput(
            input_envelope_id=sample_envelope_id,
            correlation_id=sample_correlation_id,
            handler_id=sample_handler_id,
            node_kind=EnumNodeKind.EFFECT,
        )

        assert output.has_outputs() is False

    def test_has_outputs_true_with_events(
        self, sample_envelope_id, sample_correlation_id, sample_handler_id, sample_event
    ) -> None:
        """Test has_outputs returns True when events is non-empty."""
        output = ModelHandlerOutput(
            input_envelope_id=sample_envelope_id,
            correlation_id=sample_correlation_id,
            handler_id=sample_handler_id,
            node_kind=EnumNodeKind.EFFECT,
            events=(sample_event,),
        )

        assert output.has_outputs() is True

    def test_has_outputs_true_with_intents(
        self,
        sample_envelope_id,
        sample_correlation_id,
        sample_handler_id,
        sample_intent,
    ) -> None:
        """Test has_outputs returns True when intents is non-empty."""
        output = ModelHandlerOutput(
            input_envelope_id=sample_envelope_id,
            correlation_id=sample_correlation_id,
            handler_id=sample_handler_id,
            node_kind=EnumNodeKind.ORCHESTRATOR,
            intents=(sample_intent,),
        )

        assert output.has_outputs() is True

    def test_has_outputs_true_with_projections(
        self,
        sample_envelope_id,
        sample_correlation_id,
        sample_handler_id,
        sample_projection,
    ) -> None:
        """Test has_outputs returns True when projections is non-empty."""
        output = ModelHandlerOutput(
            input_envelope_id=sample_envelope_id,
            correlation_id=sample_correlation_id,
            handler_id=sample_handler_id,
            node_kind=EnumNodeKind.REDUCER,
            projections=(sample_projection,),
        )

        assert output.has_outputs() is True

    def test_output_count_zero_when_empty(
        self, sample_envelope_id, sample_correlation_id, sample_handler_id
    ) -> None:
        """Test output_count returns 0 when all collections are empty."""
        output = ModelHandlerOutput(
            input_envelope_id=sample_envelope_id,
            correlation_id=sample_correlation_id,
            handler_id=sample_handler_id,
            node_kind=EnumNodeKind.EFFECT,
        )

        assert output.output_count() == 0

    def test_output_count_sums_all_collections(
        self,
        sample_envelope_id,
        sample_correlation_id,
        sample_handler_id,
        sample_event,
        sample_intent,
    ) -> None:
        """Test output_count sums events and intents for ORCHESTRATOR."""
        output = ModelHandlerOutput(
            input_envelope_id=sample_envelope_id,
            correlation_id=sample_correlation_id,
            handler_id=sample_handler_id,
            node_kind=EnumNodeKind.ORCHESTRATOR,
            events=(sample_event, sample_event),
            intents=(sample_intent,),
        )

        assert output.output_count() == 3

    def test_has_metrics_false_when_empty(
        self, sample_envelope_id, sample_correlation_id, sample_handler_id
    ) -> None:
        """Test has_metrics returns False when metrics is empty."""
        output = ModelHandlerOutput(
            input_envelope_id=sample_envelope_id,
            correlation_id=sample_correlation_id,
            handler_id=sample_handler_id,
            node_kind=EnumNodeKind.EFFECT,
        )

        assert output.has_metrics() is False

    def test_has_metrics_true_when_non_empty(
        self, sample_envelope_id, sample_correlation_id, sample_handler_id
    ) -> None:
        """Test has_metrics returns True when metrics is non-empty."""
        output = ModelHandlerOutput(
            input_envelope_id=sample_envelope_id,
            correlation_id=sample_correlation_id,
            handler_id=sample_handler_id,
            node_kind=EnumNodeKind.EFFECT,
            metrics={"count": 5.0},
        )

        assert output.has_metrics() is True

    def test_has_logs_false_when_empty(
        self, sample_envelope_id, sample_correlation_id, sample_handler_id
    ) -> None:
        """Test has_logs returns False when logs is empty."""
        output = ModelHandlerOutput(
            input_envelope_id=sample_envelope_id,
            correlation_id=sample_correlation_id,
            handler_id=sample_handler_id,
            node_kind=EnumNodeKind.EFFECT,
        )

        assert output.has_logs() is False

    def test_has_logs_true_when_non_empty(
        self, sample_envelope_id, sample_correlation_id, sample_handler_id
    ) -> None:
        """Test has_logs returns True when logs is non-empty."""
        output = ModelHandlerOutput(
            input_envelope_id=sample_envelope_id,
            correlation_id=sample_correlation_id,
            handler_id=sample_handler_id,
            node_kind=EnumNodeKind.EFFECT,
            logs=("Processing started",),
        )

        assert output.has_logs() is True


# ============================================================================
# Thread Safety Tests
# ============================================================================


@pytest.mark.unit
class TestModelHandlerOutputThreadSafety:
    """Tests verifying thread-safety characteristics."""

    def test_output_is_immutable(
        self, sample_envelope_id, sample_correlation_id, sample_handler_id
    ) -> None:
        """Test that ModelHandlerOutput is immutable after creation."""
        output = ModelHandlerOutput(
            input_envelope_id=sample_envelope_id,
            correlation_id=sample_correlation_id,
            handler_id=sample_handler_id,
            node_kind=EnumNodeKind.EFFECT,
        )

        # All attributes should raise on modification attempt
        with pytest.raises(ValidationError):
            output.handler_id = "modified"  # type: ignore[misc]

        with pytest.raises(ValidationError):
            output.node_kind = EnumNodeKind.COMPUTE  # type: ignore[misc]

        with pytest.raises(ValidationError):
            output.events = ({"new": "event"},)  # type: ignore[misc]

    def test_from_attributes_support(
        self, sample_envelope_id, sample_correlation_id, sample_handler_id
    ) -> None:
        """Test that from_attributes=True is configured for value object compatibility."""
        # from_attributes=True in ConfigDict enables creating instances from
        # objects with matching attributes (important for pytest-xdist)
        output = ModelHandlerOutput(
            input_envelope_id=sample_envelope_id,
            correlation_id=sample_correlation_id,
            handler_id=sample_handler_id,
            node_kind=EnumNodeKind.EFFECT,
        )

        # Verify model config
        assert output.model_config.get("from_attributes") is True
        assert output.model_config.get("frozen") is True


# ============================================================================
# Invalid Node-Kind Output Combinations Tests
# ============================================================================


@pytest.mark.unit
class TestInvalidNodeKindOutputCombinations:
    """Test that invalid node-kind/output combinations fail fast."""

    def test_orchestrator_with_projections_fails(
        self,
        sample_envelope_id,
        sample_correlation_id,
        sample_handler_id,
        sample_projection,
    ) -> None:
        """Test ORCHESTRATOR with projections raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            ModelHandlerOutput(
                input_envelope_id=sample_envelope_id,
                correlation_id=sample_correlation_id,
                handler_id=sample_handler_id,
                node_kind=EnumNodeKind.ORCHESTRATOR,
                projections=(sample_projection,),
            )

        error_msg = str(exc_info.value)
        assert "ORCHESTRATOR cannot emit projections[]" in error_msg
        assert "use events[] and intents[] only" in error_msg

    def test_reducer_with_events_fails(
        self, sample_envelope_id, sample_correlation_id, sample_handler_id, sample_event
    ) -> None:
        """Test REDUCER with events raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            ModelHandlerOutput(
                input_envelope_id=sample_envelope_id,
                correlation_id=sample_correlation_id,
                handler_id=sample_handler_id,
                node_kind=EnumNodeKind.REDUCER,
                events=(sample_event,),
            )

        error_msg = str(exc_info.value)
        assert "REDUCER cannot emit events[]" in error_msg
        assert "pure fold" in error_msg

    def test_reducer_with_intents_fails(
        self,
        sample_envelope_id,
        sample_correlation_id,
        sample_handler_id,
        sample_intent,
    ) -> None:
        """Test REDUCER with intents raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            ModelHandlerOutput(
                input_envelope_id=sample_envelope_id,
                correlation_id=sample_correlation_id,
                handler_id=sample_handler_id,
                node_kind=EnumNodeKind.REDUCER,
                intents=(sample_intent,),
            )

        error_msg = str(exc_info.value)
        assert "REDUCER cannot emit intents[]" in error_msg
        assert "pure fold" in error_msg

    def test_effect_with_intents_fails(
        self,
        sample_envelope_id,
        sample_correlation_id,
        sample_handler_id,
        sample_intent,
    ) -> None:
        """Test EFFECT with intents raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            ModelHandlerOutput(
                input_envelope_id=sample_envelope_id,
                correlation_id=sample_correlation_id,
                handler_id=sample_handler_id,
                node_kind=EnumNodeKind.EFFECT,
                intents=(sample_intent,),
            )

        error_msg = str(exc_info.value)
        assert "EFFECT cannot emit intents[]" in error_msg
        assert "events[] only" in error_msg

    def test_effect_with_projections_fails(
        self,
        sample_envelope_id,
        sample_correlation_id,
        sample_handler_id,
        sample_projection,
    ) -> None:
        """Test EFFECT with projections raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            ModelHandlerOutput(
                input_envelope_id=sample_envelope_id,
                correlation_id=sample_correlation_id,
                handler_id=sample_handler_id,
                node_kind=EnumNodeKind.EFFECT,
                projections=(sample_projection,),
            )

        error_msg = str(exc_info.value)
        assert "EFFECT cannot emit projections[]" in error_msg
        assert "events[] only" in error_msg

    def test_compute_with_intents_fails(
        self,
        sample_envelope_id,
        sample_correlation_id,
        sample_handler_id,
        sample_intent,
    ) -> None:
        """Test COMPUTE with intents raises ValueError (OMN-941 updated)."""
        with pytest.raises(ValueError) as exc_info:
            ModelHandlerOutput(
                input_envelope_id=sample_envelope_id,
                correlation_id=sample_correlation_id,
                handler_id=sample_handler_id,
                node_kind=EnumNodeKind.COMPUTE,
                result="some_result",  # COMPUTE requires result
                intents=(sample_intent,),
            )

        error_msg = str(exc_info.value)
        assert "COMPUTE cannot emit intents[]" in error_msg
        assert "result only" in error_msg  # Updated error message per OMN-941

    def test_compute_with_projections_fails(
        self,
        sample_envelope_id,
        sample_correlation_id,
        sample_handler_id,
        sample_projection,
    ) -> None:
        """Test COMPUTE with projections raises ValueError (OMN-941 updated)."""
        with pytest.raises(ValueError) as exc_info:
            ModelHandlerOutput(
                input_envelope_id=sample_envelope_id,
                correlation_id=sample_correlation_id,
                handler_id=sample_handler_id,
                node_kind=EnumNodeKind.COMPUTE,
                result="some_result",  # COMPUTE requires result
                projections=(sample_projection,),
            )

        error_msg = str(exc_info.value)
        assert "COMPUTE cannot emit projections[]" in error_msg
        assert "result only" in error_msg


# ============================================================================
# COMPUTE Node Constraints Tests (OMN-941)
# ============================================================================


@pytest.mark.unit
class TestComputeNodeConstraints:
    """
    Test COMPUTE node constraints per OMN-941.

    COMPUTE nodes are pure transformations that:
    - MUST return result (or set allow_void_compute=True)
    - CANNOT emit events[], intents[], or projections[]
    """

    def test_compute_requires_result(
        self, sample_envelope_id, sample_correlation_id, sample_handler_id
    ) -> None:
        """Test that COMPUTE node raises ValueError when result=None and allow_void_compute=False."""
        with pytest.raises(ValueError) as exc_info:
            ModelHandlerOutput(
                input_envelope_id=sample_envelope_id,
                correlation_id=sample_correlation_id,
                handler_id=sample_handler_id,
                node_kind=EnumNodeKind.COMPUTE,
                # No result provided, and allow_void_compute defaults to False
            )

        error_msg = str(exc_info.value)
        assert "COMPUTE requires result" in error_msg
        assert "allow_void_compute=True" in error_msg

    def test_compute_with_valid_result_passes(
        self, sample_envelope_id, sample_correlation_id, sample_handler_id
    ) -> None:
        """Test that COMPUTE node with valid result passes validation."""
        output = ModelHandlerOutput(
            input_envelope_id=sample_envelope_id,
            correlation_id=sample_correlation_id,
            handler_id=sample_handler_id,
            node_kind=EnumNodeKind.COMPUTE,
            result={"transformed": True, "count": 42},
        )

        assert output.result == {"transformed": True, "count": 42}
        assert output.node_kind == EnumNodeKind.COMPUTE
        assert output.has_result() is True

    def test_compute_with_allow_void_compute_passes(
        self, sample_envelope_id, sample_correlation_id, sample_handler_id
    ) -> None:
        """Test that COMPUTE node with allow_void_compute=True and None result passes."""
        output = ModelHandlerOutput(
            input_envelope_id=sample_envelope_id,
            correlation_id=sample_correlation_id,
            handler_id=sample_handler_id,
            node_kind=EnumNodeKind.COMPUTE,
            allow_void_compute=True,
            # No result - this is valid because allow_void_compute=True
        )

        assert output.result is None
        assert output.allow_void_compute is True
        assert output.has_result() is False

    def test_compute_cannot_emit_events(
        self, sample_envelope_id, sample_correlation_id, sample_handler_id, sample_event
    ) -> None:
        """Test that COMPUTE node raises ValueError when emitting events."""
        with pytest.raises(ValueError) as exc_info:
            ModelHandlerOutput(
                input_envelope_id=sample_envelope_id,
                correlation_id=sample_correlation_id,
                handler_id=sample_handler_id,
                node_kind=EnumNodeKind.COMPUTE,
                result="some_result",
                events=(sample_event,),  # COMPUTE cannot emit events
            )

        error_msg = str(exc_info.value)
        assert "COMPUTE cannot emit events[]" in error_msg
        assert "result only" in error_msg

    def test_compute_cannot_emit_intents(
        self,
        sample_envelope_id,
        sample_correlation_id,
        sample_handler_id,
        sample_intent,
    ) -> None:
        """Test that COMPUTE node raises ValueError when emitting intents."""
        with pytest.raises(ValueError) as exc_info:
            ModelHandlerOutput(
                input_envelope_id=sample_envelope_id,
                correlation_id=sample_correlation_id,
                handler_id=sample_handler_id,
                node_kind=EnumNodeKind.COMPUTE,
                result="some_result",
                intents=(sample_intent,),  # COMPUTE cannot emit intents
            )

        error_msg = str(exc_info.value)
        assert "COMPUTE cannot emit intents[]" in error_msg
        assert "result only" in error_msg

    def test_compute_cannot_emit_projections(
        self,
        sample_envelope_id,
        sample_correlation_id,
        sample_handler_id,
        sample_projection,
    ) -> None:
        """Test that COMPUTE node raises ValueError when emitting projections."""
        with pytest.raises(ValueError) as exc_info:
            ModelHandlerOutput(
                input_envelope_id=sample_envelope_id,
                correlation_id=sample_correlation_id,
                handler_id=sample_handler_id,
                node_kind=EnumNodeKind.COMPUTE,
                result="some_result",
                projections=(sample_projection,),  # COMPUTE cannot emit projections
            )

        error_msg = str(exc_info.value)
        assert "COMPUTE cannot emit projections[]" in error_msg
        assert "result only" in error_msg

    def test_compute_with_string_result(
        self, sample_envelope_id, sample_correlation_id, sample_handler_id
    ) -> None:
        """Test COMPUTE with string result."""
        output = ModelHandlerOutput(
            input_envelope_id=sample_envelope_id,
            correlation_id=sample_correlation_id,
            handler_id=sample_handler_id,
            node_kind=EnumNodeKind.COMPUTE,
            result="transformation complete",
        )

        assert output.result == "transformation complete"

    def test_compute_with_integer_result(
        self, sample_envelope_id, sample_correlation_id, sample_handler_id
    ) -> None:
        """Test COMPUTE with integer result."""
        output = ModelHandlerOutput(
            input_envelope_id=sample_envelope_id,
            correlation_id=sample_correlation_id,
            handler_id=sample_handler_id,
            node_kind=EnumNodeKind.COMPUTE,
            result=42,
        )

        assert output.result == 42

    def test_compute_with_list_result(
        self, sample_envelope_id, sample_correlation_id, sample_handler_id
    ) -> None:
        """Test COMPUTE with list result."""
        output = ModelHandlerOutput(
            input_envelope_id=sample_envelope_id,
            correlation_id=sample_correlation_id,
            handler_id=sample_handler_id,
            node_kind=EnumNodeKind.COMPUTE,
            result=[1, 2, 3, "four"],
        )

        assert output.result == [1, 2, 3, "four"]


# ============================================================================
# JSON-Ledger-Safe Validation Tests (OMN-941)
# ============================================================================


@pytest.mark.unit
class TestJsonLedgerSafe:
    """
    Test JSON-ledger-safe validation for COMPUTE results.

    JSON-ledger-safe values can be:
    - JSON primitives: str, int, float, bool, None
    - JSON containers: list, tuple, dict (with str keys and JSON-safe values)
    - Pydantic BaseModel

    NOT ledger-safe (rejected):
    - bytes, bytearray
    - datetime, UUID, Decimal
    - Custom classes without Pydantic serialization
    """

    def test_string_is_ledger_safe(
        self, sample_envelope_id, sample_correlation_id, sample_handler_id
    ) -> None:
        """Test that string is JSON-ledger-safe."""
        output = ModelHandlerOutput(
            input_envelope_id=sample_envelope_id,
            correlation_id=sample_correlation_id,
            handler_id=sample_handler_id,
            node_kind=EnumNodeKind.COMPUTE,
            result="hello world",
        )
        assert output.result == "hello world"

    def test_int_is_ledger_safe(
        self, sample_envelope_id, sample_correlation_id, sample_handler_id
    ) -> None:
        """Test that int is JSON-ledger-safe."""
        output = ModelHandlerOutput(
            input_envelope_id=sample_envelope_id,
            correlation_id=sample_correlation_id,
            handler_id=sample_handler_id,
            node_kind=EnumNodeKind.COMPUTE,
            result=123,
        )
        assert output.result == 123

    def test_float_is_ledger_safe(
        self, sample_envelope_id, sample_correlation_id, sample_handler_id
    ) -> None:
        """Test that float is JSON-ledger-safe."""
        output = ModelHandlerOutput(
            input_envelope_id=sample_envelope_id,
            correlation_id=sample_correlation_id,
            handler_id=sample_handler_id,
            node_kind=EnumNodeKind.COMPUTE,
            result=3.14159,
        )
        assert output.result == 3.14159

    def test_bool_is_ledger_safe(
        self, sample_envelope_id, sample_correlation_id, sample_handler_id
    ) -> None:
        """Test that bool is JSON-ledger-safe."""
        output = ModelHandlerOutput(
            input_envelope_id=sample_envelope_id,
            correlation_id=sample_correlation_id,
            handler_id=sample_handler_id,
            node_kind=EnumNodeKind.COMPUTE,
            result=True,
        )
        assert output.result is True

    def test_none_is_ledger_safe_with_allow_void(
        self, sample_envelope_id, sample_correlation_id, sample_handler_id
    ) -> None:
        """Test that None is JSON-ledger-safe (with allow_void_compute=True)."""
        output = ModelHandlerOutput(
            input_envelope_id=sample_envelope_id,
            correlation_id=sample_correlation_id,
            handler_id=sample_handler_id,
            node_kind=EnumNodeKind.COMPUTE,
            result=None,
            allow_void_compute=True,
        )
        assert output.result is None

    def test_dict_with_str_keys_is_ledger_safe(
        self, sample_envelope_id, sample_correlation_id, sample_handler_id
    ) -> None:
        """Test that dict with str keys is JSON-ledger-safe."""
        output = ModelHandlerOutput(
            input_envelope_id=sample_envelope_id,
            correlation_id=sample_correlation_id,
            handler_id=sample_handler_id,
            node_kind=EnumNodeKind.COMPUTE,
            result={"key": "value", "count": 42, "active": True},
        )
        assert output.result == {"key": "value", "count": 42, "active": True}

    def test_list_is_ledger_safe(
        self, sample_envelope_id, sample_correlation_id, sample_handler_id
    ) -> None:
        """Test that list is JSON-ledger-safe."""
        output = ModelHandlerOutput(
            input_envelope_id=sample_envelope_id,
            correlation_id=sample_correlation_id,
            handler_id=sample_handler_id,
            node_kind=EnumNodeKind.COMPUTE,
            result=[1, "two", 3.0, True, None],
        )
        assert output.result == [1, "two", 3.0, True, None]

    def test_tuple_is_ledger_safe(
        self, sample_envelope_id, sample_correlation_id, sample_handler_id
    ) -> None:
        """Test that tuple is JSON-ledger-safe."""
        output = ModelHandlerOutput(
            input_envelope_id=sample_envelope_id,
            correlation_id=sample_correlation_id,
            handler_id=sample_handler_id,
            node_kind=EnumNodeKind.COMPUTE,
            result=(1, "two", 3.0),
        )
        assert output.result == (1, "two", 3.0)

    def test_nested_dict_is_ledger_safe(
        self, sample_envelope_id, sample_correlation_id, sample_handler_id
    ) -> None:
        """Test that nested dict/list structures are JSON-ledger-safe."""
        output = ModelHandlerOutput(
            input_envelope_id=sample_envelope_id,
            correlation_id=sample_correlation_id,
            handler_id=sample_handler_id,
            node_kind=EnumNodeKind.COMPUTE,
            result={
                "users": [
                    {"id": 1, "name": "Alice"},
                    {"id": 2, "name": "Bob"},
                ],
                "count": 2,
            },
        )
        assert output.result["count"] == 2
        assert len(output.result["users"]) == 2

    def test_basemodel_is_ledger_safe(
        self, sample_envelope_id, sample_correlation_id, sample_handler_id
    ) -> None:
        """Test that Pydantic BaseModel is JSON-ledger-safe."""

        class MyResult(BaseModel):
            value: int
            name: str

        result_model = MyResult(value=42, name="test")
        output = ModelHandlerOutput(
            input_envelope_id=sample_envelope_id,
            correlation_id=sample_correlation_id,
            handler_id=sample_handler_id,
            node_kind=EnumNodeKind.COMPUTE,
            result=result_model,
        )
        assert output.result == result_model
        assert output.result.value == 42

    def test_bytes_is_not_ledger_safe(
        self, sample_envelope_id, sample_correlation_id, sample_handler_id
    ) -> None:
        """Test that bytes is NOT JSON-ledger-safe (should raise ValueError)."""
        with pytest.raises(ValueError) as exc_info:
            ModelHandlerOutput(
                input_envelope_id=sample_envelope_id,
                correlation_id=sample_correlation_id,
                handler_id=sample_handler_id,
                node_kind=EnumNodeKind.COMPUTE,
                result=b"binary data",
            )

        error_msg = str(exc_info.value)
        assert "COMPUTE result must be JSON-ledger-safe" in error_msg

    def test_datetime_is_not_ledger_safe(
        self, sample_envelope_id, sample_correlation_id, sample_handler_id
    ) -> None:
        """Test that datetime is NOT JSON-ledger-safe (should raise ValueError)."""
        with pytest.raises(ValueError) as exc_info:
            ModelHandlerOutput(
                input_envelope_id=sample_envelope_id,
                correlation_id=sample_correlation_id,
                handler_id=sample_handler_id,
                node_kind=EnumNodeKind.COMPUTE,
                result=datetime.now(UTC),
            )

        error_msg = str(exc_info.value)
        assert "COMPUTE result must be JSON-ledger-safe" in error_msg

    def test_uuid_is_not_ledger_safe(
        self, sample_envelope_id, sample_correlation_id, sample_handler_id
    ) -> None:
        """Test that UUID is NOT JSON-ledger-safe (should raise ValueError)."""
        from uuid import uuid4

        with pytest.raises(ValueError) as exc_info:
            ModelHandlerOutput(
                input_envelope_id=sample_envelope_id,
                correlation_id=sample_correlation_id,
                handler_id=sample_handler_id,
                node_kind=EnumNodeKind.COMPUTE,
                result=uuid4(),
            )

        error_msg = str(exc_info.value)
        assert "COMPUTE result must be JSON-ledger-safe" in error_msg

    def test_custom_object_is_not_ledger_safe(
        self, sample_envelope_id, sample_correlation_id, sample_handler_id
    ) -> None:
        """Test that custom object is NOT JSON-ledger-safe (should raise ValueError)."""

        class CustomClass:
            def __init__(self, value: int) -> None:
                self.value = value

        custom_obj = CustomClass(42)

        with pytest.raises(ValueError) as exc_info:
            ModelHandlerOutput(
                input_envelope_id=sample_envelope_id,
                correlation_id=sample_correlation_id,
                handler_id=sample_handler_id,
                node_kind=EnumNodeKind.COMPUTE,
                result=custom_obj,
            )

        error_msg = str(exc_info.value)
        assert "COMPUTE result must be JSON-ledger-safe" in error_msg

    def test_bytearray_is_not_ledger_safe(
        self, sample_envelope_id, sample_correlation_id, sample_handler_id
    ) -> None:
        """Test that bytearray is NOT JSON-ledger-safe (should raise ValueError)."""
        with pytest.raises(ValueError) as exc_info:
            ModelHandlerOutput(
                input_envelope_id=sample_envelope_id,
                correlation_id=sample_correlation_id,
                handler_id=sample_handler_id,
                node_kind=EnumNodeKind.COMPUTE,
                result=bytearray(b"data"),
            )

        error_msg = str(exc_info.value)
        assert "COMPUTE result must be JSON-ledger-safe" in error_msg

    def test_dict_with_uuid_value_is_not_ledger_safe(
        self, sample_envelope_id, sample_correlation_id, sample_handler_id
    ) -> None:
        """Test that dict with non-ledger-safe values is rejected."""
        from uuid import uuid4

        with pytest.raises(ValueError) as exc_info:
            ModelHandlerOutput(
                input_envelope_id=sample_envelope_id,
                correlation_id=sample_correlation_id,
                handler_id=sample_handler_id,
                node_kind=EnumNodeKind.COMPUTE,
                result={"id": uuid4()},  # UUID in dict is not ledger-safe
            )

        error_msg = str(exc_info.value)
        assert "COMPUTE result must be JSON-ledger-safe" in error_msg

    def test_list_with_datetime_is_not_ledger_safe(
        self, sample_envelope_id, sample_correlation_id, sample_handler_id
    ) -> None:
        """Test that list with non-ledger-safe values is rejected."""
        with pytest.raises(ValueError) as exc_info:
            ModelHandlerOutput(
                input_envelope_id=sample_envelope_id,
                correlation_id=sample_correlation_id,
                handler_id=sample_handler_id,
                node_kind=EnumNodeKind.COMPUTE,
                result=[1, 2, datetime.now(UTC)],  # datetime in list is not ledger-safe
            )

        error_msg = str(exc_info.value)
        assert "COMPUTE result must be JSON-ledger-safe" in error_msg

    def test_dict_with_int_keys_is_not_ledger_safe(
        self, sample_envelope_id, sample_correlation_id, sample_handler_id
    ) -> None:
        """Test that dict with integer keys is NOT JSON-ledger-safe (only str keys allowed)."""
        with pytest.raises(ValueError) as exc_info:
            ModelHandlerOutput(
                input_envelope_id=sample_envelope_id,
                correlation_id=sample_correlation_id,
                handler_id=sample_handler_id,
                node_kind=EnumNodeKind.COMPUTE,
                result={1: "value", 2: "another"},  # int keys are not ledger-safe
            )

        error_msg = str(exc_info.value)
        assert "COMPUTE result must be JSON-ledger-safe" in error_msg


# ============================================================================
# COMPUTE Builder Methods Tests (OMN-941)
# ============================================================================


@pytest.mark.unit
class TestComputeBuilderMethods:
    """Test builder methods specific to COMPUTE nodes."""

    def test_for_compute_requires_result(
        self, sample_envelope_id, sample_correlation_id, sample_handler_id
    ) -> None:
        """Test that for_compute requires a result parameter."""
        # for_compute signature requires result - this should work
        output = ModelHandlerOutput.for_compute(
            input_envelope_id=sample_envelope_id,
            correlation_id=sample_correlation_id,
            handler_id=sample_handler_id,
            result={"data": "value"},
        )

        assert output.node_kind == EnumNodeKind.COMPUTE
        assert output.result == {"data": "value"}
        assert output.has_result() is True

    def test_for_compute_with_various_result_types(
        self, sample_envelope_id, sample_correlation_id, sample_handler_id
    ) -> None:
        """Test for_compute with various valid result types."""
        # String result
        str_output = ModelHandlerOutput.for_compute(
            input_envelope_id=sample_envelope_id,
            correlation_id=sample_correlation_id,
            handler_id=sample_handler_id,
            result="string result",
        )
        assert str_output.result == "string result"

        # Integer result
        int_output = ModelHandlerOutput.for_compute(
            input_envelope_id=sample_envelope_id,
            correlation_id=sample_correlation_id,
            handler_id=sample_handler_id,
            result=999,
        )
        assert int_output.result == 999

        # Dict result
        dict_output = ModelHandlerOutput.for_compute(
            input_envelope_id=sample_envelope_id,
            correlation_id=sample_correlation_id,
            handler_id=sample_handler_id,
            result={"key": "value"},
        )
        assert dict_output.result == {"key": "value"}

        # List result
        list_output = ModelHandlerOutput.for_compute(
            input_envelope_id=sample_envelope_id,
            correlation_id=sample_correlation_id,
            handler_id=sample_handler_id,
            result=[1, 2, 3],
        )
        assert list_output.result == [1, 2, 3]

    def test_for_compute_with_metrics_and_logs(
        self, sample_envelope_id, sample_correlation_id, sample_handler_id
    ) -> None:
        """Test for_compute with metrics and logs."""
        metrics = {"duration_ms": 50.5, "items_processed": 100.0}
        logs = ("Started processing", "Completed")

        output = ModelHandlerOutput.for_compute(
            input_envelope_id=sample_envelope_id,
            correlation_id=sample_correlation_id,
            handler_id=sample_handler_id,
            result="done",
            metrics=metrics,
            logs=logs,
        )

        assert output.metrics == metrics
        assert output.logs == logs
        assert output.result == "done"

    def test_for_void_compute_works_without_result(
        self, sample_envelope_id, sample_correlation_id, sample_handler_id
    ) -> None:
        """Test that for_void_compute works without a result."""
        output = ModelHandlerOutput.for_void_compute(
            input_envelope_id=sample_envelope_id,
            correlation_id=sample_correlation_id,
            handler_id=sample_handler_id,
        )

        assert output.node_kind == EnumNodeKind.COMPUTE
        assert output.result is None
        assert output.allow_void_compute is True
        assert output.has_result() is False

    def test_for_void_compute_with_processing_time(
        self, sample_envelope_id, sample_correlation_id, sample_handler_id
    ) -> None:
        """Test for_void_compute with processing time."""
        output = ModelHandlerOutput.for_void_compute(
            input_envelope_id=sample_envelope_id,
            correlation_id=sample_correlation_id,
            handler_id=sample_handler_id,
            processing_time_ms=10.5,
        )

        assert output.processing_time_ms == 10.5
        assert output.has_result() is False

    def test_for_void_compute_with_metrics(
        self, sample_envelope_id, sample_correlation_id, sample_handler_id
    ) -> None:
        """Test for_void_compute with metrics."""
        metrics = {"validation_checks": 15.0}

        output = ModelHandlerOutput.for_void_compute(
            input_envelope_id=sample_envelope_id,
            correlation_id=sample_correlation_id,
            handler_id=sample_handler_id,
            metrics=metrics,
        )

        assert output.metrics == metrics
        assert output.has_metrics() is True

    def test_empty_for_compute_allows_void(
        self, sample_envelope_id, sample_correlation_id, sample_handler_id
    ) -> None:
        """Test that empty() for COMPUTE automatically sets allow_void_compute=True."""
        output = ModelHandlerOutput.empty(
            input_envelope_id=sample_envelope_id,
            correlation_id=sample_correlation_id,
            handler_id=sample_handler_id,
            node_kind=EnumNodeKind.COMPUTE,
        )

        assert output.node_kind == EnumNodeKind.COMPUTE
        assert output.result is None
        assert output.allow_void_compute is True
        assert output.has_outputs() is False

    def test_for_compute_preserves_correlation_id(
        self, sample_envelope_id, sample_handler_id
    ) -> None:
        """Test that for_compute preserves the correlation_id."""
        from uuid import uuid4

        correlation_id = uuid4()

        output = ModelHandlerOutput.for_compute(
            input_envelope_id=sample_envelope_id,
            correlation_id=correlation_id,
            handler_id=sample_handler_id,
            result="test",
        )

        assert output.correlation_id == correlation_id

    def test_for_void_compute_preserves_correlation_id(
        self, sample_envelope_id, sample_handler_id
    ) -> None:
        """Test that for_void_compute preserves the correlation_id."""
        from uuid import uuid4

        correlation_id = uuid4()

        output = ModelHandlerOutput.for_void_compute(
            input_envelope_id=sample_envelope_id,
            correlation_id=correlation_id,
            handler_id=sample_handler_id,
        )

        assert output.correlation_id == correlation_id
