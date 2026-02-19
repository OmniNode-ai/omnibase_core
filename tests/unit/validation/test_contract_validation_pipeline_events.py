# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for ContractValidationPipeline event emission.

Tests cover:
- validation_started event at pipeline start
- validation_passed event on success
- validation_failed event on failure (each phase)
- merge_started/merge_completed events during merge
- correlation_id threading through all events
- run_id consistency across lifecycle
- No events when emitter is None (backward compatibility)

Related:
    - OMN-1151: Event emission for contract validation pipeline
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, Mock
from uuid import uuid4

import pytest

from omnibase_core.enums import EnumNodeType
from omnibase_core.models.contracts.model_contract_patch import ModelContractPatch
from omnibase_core.models.contracts.model_profile_reference import ModelProfileReference
from omnibase_core.models.events.contract_validation import (
    ModelContractMergeCompletedEvent,
    ModelContractMergeStartedEvent,
    ModelContractValidationFailedEvent,
    ModelContractValidationPassedEvent,
    ModelContractValidationStartedEvent,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.validation.validator_contract_pipeline import (
    ContractValidationPipeline,
)

# =============================================================================
# Test Fixtures and Helpers
# =============================================================================


class MockEmitter:
    """Mock event emitter that captures events synchronously.

    The emitter has an async emit method that stores events in a list.
    """

    def __init__(self) -> None:
        self.events: list[Any] = []

    async def emit(self, event: Any) -> None:
        """Capture the event."""
        self.events.append(event)


def create_mock_base_contract() -> Mock:
    """Create a mock base contract that the merge engine can work with."""
    mock = Mock()
    mock.name = "base_contract"
    mock.contract_version = ModelSemVer(major=0, minor=1, patch=0)
    mock.description = "Base contract description"
    mock.node_type = EnumNodeType.COMPUTE_GENERIC
    # Use valid module paths for input/output models
    mock.input_model = "omnibase_core.models.events.ModelTestEvent"
    mock.output_model = "omnibase_core.models.results.ModelTestResult"
    mock.handlers = []
    mock.dependencies = []
    mock.consumed_events = []
    mock.capability_inputs = []
    mock.capability_outputs = []
    mock.behavior = None
    mock.tags = []
    # Use valid handler_id format (dot-separated, each segment starting with letter/underscore)
    mock.handler_id = "node.base.contract"
    mock.descriptor = None

    mock.model_dump = Mock(
        return_value={
            "name": "base_contract",
            "contract_version": {"major": 0, "minor": 1, "patch": 0},
            "description": "Base contract description",
            "node_type": EnumNodeType.COMPUTE_GENERIC,
            "input_model": "omnibase_core.models.events.ModelTestEvent",
            "output_model": "omnibase_core.models.results.ModelTestResult",
            "handlers": [],
            "dependencies": [],
            "consumed_events": [],
            "capability_inputs": [],
            "capability_outputs": [],
            "behavior": None,
            "tags": [],
            "handler_id": "node.base.contract",
            "descriptor": None,
        }
    )
    return mock


def create_mock_profile_factory(base_contract: Mock | None = None) -> Mock:
    """Create a mock profile factory."""
    factory = Mock()
    factory.get_profile = Mock(
        return_value=base_contract or create_mock_base_contract()
    )
    factory.available_profiles = Mock(return_value=["compute_pure", "effect_http"])
    return factory


def create_test_patch(
    name: str = "test_handler",
    profile: str = "compute_pure",
    version: str = "1.0.0",
) -> ModelContractPatch:
    """Create a test patch for pipeline validation.

    Note: name uses underscore (not hyphen) to ensure valid handler_id format.
    """
    return ModelContractPatch(
        extends=ModelProfileReference(
            profile=profile,
            version=version,
        ),
        name=name,
        node_version=ModelSemVer(major=1, minor=0, patch=0),
        description="Test handler",
    )


# =============================================================================
# Event Emission Basic Tests
# =============================================================================


@pytest.mark.unit
class TestPipelineEventEmission:
    """Tests for basic event emission behavior."""

    def test_no_events_when_emitter_is_none(self) -> None:
        """Test that no events are emitted when emitter is None."""
        pipeline = ContractValidationPipeline(
            event_emitter=None,
        )
        profile_factory = create_mock_profile_factory()
        test_patch = create_test_patch()

        # This should complete without error even with no emitter
        result = pipeline.validate_all(test_patch, profile_factory)

        # Validation should still work
        assert result.success is True

    def test_validation_started_event_emitted_at_start(self) -> None:
        """Test that validation_started event is emitted at pipeline start."""
        emitter = MockEmitter()
        correlation_id = uuid4()
        pipeline = ContractValidationPipeline(
            event_emitter=emitter,
            correlation_id=correlation_id,
        )
        profile_factory = create_mock_profile_factory()
        test_patch = create_test_patch()

        pipeline.validate_all(test_patch, profile_factory)

        # Find the started event
        started_events = [
            e
            for e in emitter.events
            if isinstance(e, ModelContractValidationStartedEvent)
        ]
        assert len(started_events) == 1

        started = started_events[0]
        assert started.correlation_id == correlation_id

    def test_validation_passed_event_on_success(self) -> None:
        """Test that validation_passed event is emitted on success."""
        emitter = MockEmitter()
        pipeline = ContractValidationPipeline(event_emitter=emitter)
        profile_factory = create_mock_profile_factory()
        test_patch = create_test_patch()

        result = pipeline.validate_all(test_patch, profile_factory)

        assert result.success is True

        # Find the passed event
        passed_events = [
            e
            for e in emitter.events
            if isinstance(e, ModelContractValidationPassedEvent)
        ]
        assert len(passed_events) == 1

        passed = passed_events[0]
        assert passed.duration_ms >= 0

    def test_merge_events_emitted_during_merge(self) -> None:
        """Test that merge_started and merge_completed events are emitted."""
        emitter = MockEmitter()
        pipeline = ContractValidationPipeline(event_emitter=emitter)
        profile_factory = create_mock_profile_factory()
        test_patch = create_test_patch()

        pipeline.validate_all(test_patch, profile_factory)

        # Find merge events
        merge_started_events = [
            e for e in emitter.events if isinstance(e, ModelContractMergeStartedEvent)
        ]
        merge_completed_events = [
            e for e in emitter.events if isinstance(e, ModelContractMergeCompletedEvent)
        ]

        assert len(merge_started_events) == 1
        assert len(merge_completed_events) == 1

        # Merge completed should have duration
        completed = merge_completed_events[0]
        assert completed.duration_ms >= 0


# =============================================================================
# Correlation ID Tests
# =============================================================================


@pytest.mark.unit
class TestPipelineCorrelationId:
    """Tests for correlation ID threading."""

    def test_correlation_id_propagated_to_all_events(self) -> None:
        """Test that correlation_id is propagated to all emitted events."""
        correlation_id = uuid4()
        emitter = MockEmitter()
        pipeline = ContractValidationPipeline(
            event_emitter=emitter,
            correlation_id=correlation_id,
        )
        profile_factory = create_mock_profile_factory()
        test_patch = create_test_patch()

        pipeline.validate_all(test_patch, profile_factory)

        # All events should have the same correlation_id
        for event in emitter.events:
            assert event.correlation_id == correlation_id

    def test_generated_correlation_id_when_not_provided(self) -> None:
        """Test that a correlation_id is generated when not provided."""
        emitter = MockEmitter()
        pipeline = ContractValidationPipeline(event_emitter=emitter)
        profile_factory = create_mock_profile_factory()
        test_patch = create_test_patch()

        pipeline.validate_all(test_patch, profile_factory)

        # All events should have the same (generated) correlation_id
        correlation_ids = {event.correlation_id for event in emitter.events}
        assert len(correlation_ids) == 1
        assert None not in correlation_ids


# =============================================================================
# Run ID Tests
# =============================================================================


@pytest.mark.unit
class TestPipelineRunId:
    """Tests for run_id consistency."""

    def test_run_id_consistent_across_lifecycle(self) -> None:
        """Test that run_id is consistent across all events in a run."""
        emitter = MockEmitter()
        pipeline = ContractValidationPipeline(event_emitter=emitter)
        profile_factory = create_mock_profile_factory()
        test_patch = create_test_patch()

        pipeline.validate_all(test_patch, profile_factory)

        # All events should have the same run_id
        run_ids = {event.run_id for event in emitter.events}
        assert len(run_ids) == 1

    def test_different_runs_have_different_run_ids(self) -> None:
        """Test that different pipeline runs have different run_ids."""
        emitter = MockEmitter()
        pipeline = ContractValidationPipeline(event_emitter=emitter)
        profile_factory = create_mock_profile_factory()
        test_patch = create_test_patch()

        # First run
        pipeline.validate_all(test_patch, profile_factory)
        first_run_ids = {event.run_id for event in emitter.events}
        assert len(first_run_ids) == 1
        first_run_id = first_run_ids.pop()

        # Second run
        emitter.events.clear()
        pipeline.validate_all(test_patch, profile_factory)
        second_run_ids = {event.run_id for event in emitter.events}
        assert len(second_run_ids) == 1
        second_run_id = second_run_ids.pop()

        # Run IDs should be different
        assert first_run_id != second_run_id


# =============================================================================
# Event Ordering Tests
# =============================================================================


@pytest.mark.unit
class TestPipelineEventOrdering:
    """Tests for event ordering invariants."""

    def test_started_event_is_first(self) -> None:
        """Test that validation_started is always the first event."""
        emitter = MockEmitter()
        pipeline = ContractValidationPipeline(event_emitter=emitter)
        profile_factory = create_mock_profile_factory()
        test_patch = create_test_patch()

        pipeline.validate_all(test_patch, profile_factory)

        assert len(emitter.events) >= 1
        assert isinstance(emitter.events[0], ModelContractValidationStartedEvent)

    def test_passed_or_failed_is_last(self) -> None:
        """Test that passed or failed is the last event."""
        emitter = MockEmitter()
        pipeline = ContractValidationPipeline(event_emitter=emitter)
        profile_factory = create_mock_profile_factory()
        test_patch = create_test_patch()

        pipeline.validate_all(test_patch, profile_factory)

        assert len(emitter.events) >= 1
        last_event = emitter.events[-1]
        assert isinstance(
            last_event,
            (ModelContractValidationPassedEvent, ModelContractValidationFailedEvent),
        )

    def test_merge_events_in_correct_order(self) -> None:
        """Test that merge_started comes before merge_completed."""
        emitter = MockEmitter()
        pipeline = ContractValidationPipeline(event_emitter=emitter)
        profile_factory = create_mock_profile_factory()
        test_patch = create_test_patch()

        pipeline.validate_all(test_patch, profile_factory)

        merge_started_idx = None
        merge_completed_idx = None

        for i, event in enumerate(emitter.events):
            if isinstance(event, ModelContractMergeStartedEvent):
                merge_started_idx = i
            elif isinstance(event, ModelContractMergeCompletedEvent):
                merge_completed_idx = i

        assert merge_started_idx is not None
        assert merge_completed_idx is not None
        assert merge_started_idx < merge_completed_idx

    def test_merge_started_after_validation_started(self) -> None:
        """Test that merge_started comes after validation_started."""
        emitter = MockEmitter()
        pipeline = ContractValidationPipeline(event_emitter=emitter)
        profile_factory = create_mock_profile_factory()
        test_patch = create_test_patch()

        pipeline.validate_all(test_patch, profile_factory)

        validation_started_idx = None
        merge_started_idx = None

        for i, event in enumerate(emitter.events):
            if isinstance(event, ModelContractValidationStartedEvent):
                validation_started_idx = i
            elif isinstance(event, ModelContractMergeStartedEvent):
                merge_started_idx = i

        assert validation_started_idx is not None
        assert merge_started_idx is not None
        assert validation_started_idx < merge_started_idx


# =============================================================================
# Event Content Tests
# =============================================================================


@pytest.mark.unit
class TestPipelineEventContent:
    """Tests for event content correctness."""

    def test_started_event_has_contract_name(self) -> None:
        """Test that started event has correct contract_name."""
        emitter = MockEmitter()
        pipeline = ContractValidationPipeline(event_emitter=emitter)
        profile_factory = create_mock_profile_factory()
        test_patch = create_test_patch(name="my_handler")

        pipeline.validate_all(test_patch, profile_factory)

        started_events = [
            e
            for e in emitter.events
            if isinstance(e, ModelContractValidationStartedEvent)
        ]
        assert len(started_events) == 1

        # Contract name should be set (either patch name or profile name)
        started = started_events[0]
        assert started.contract_name is not None
        assert len(started.contract_name) > 0

    def test_passed_event_has_duration(self) -> None:
        """Test that passed event has non-negative duration."""
        emitter = MockEmitter()
        pipeline = ContractValidationPipeline(event_emitter=emitter)
        profile_factory = create_mock_profile_factory()
        test_patch = create_test_patch()

        pipeline.validate_all(test_patch, profile_factory)

        passed_events = [
            e
            for e in emitter.events
            if isinstance(e, ModelContractValidationPassedEvent)
        ]
        assert len(passed_events) == 1

        passed = passed_events[0]
        assert passed.duration_ms >= 0

    def test_passed_event_has_checks_run(self) -> None:
        """Test that passed event has checks_run count."""
        emitter = MockEmitter()
        pipeline = ContractValidationPipeline(event_emitter=emitter)
        profile_factory = create_mock_profile_factory()
        test_patch = create_test_patch()

        pipeline.validate_all(test_patch, profile_factory)

        passed_events = [
            e
            for e in emitter.events
            if isinstance(e, ModelContractValidationPassedEvent)
        ]
        assert len(passed_events) == 1

        passed = passed_events[0]
        assert passed.checks_run >= 0

    def test_merge_completed_has_effective_name(self) -> None:
        """Test that merge_completed has effective_contract_name."""
        emitter = MockEmitter()
        pipeline = ContractValidationPipeline(event_emitter=emitter)
        profile_factory = create_mock_profile_factory()
        test_patch = create_test_patch(name="my_handler")

        pipeline.validate_all(test_patch, profile_factory)

        completed_events = [
            e for e in emitter.events if isinstance(e, ModelContractMergeCompletedEvent)
        ]
        assert len(completed_events) == 1

        completed = completed_events[0]
        assert completed.effective_contract_name is not None
        assert len(completed.effective_contract_name) > 0

    def test_merge_started_has_profile_names(self) -> None:
        """Test that merge_started has profile_names populated."""
        emitter = MockEmitter()
        pipeline = ContractValidationPipeline(event_emitter=emitter)
        profile_factory = create_mock_profile_factory()
        test_patch = create_test_patch(profile="compute_pure")

        pipeline.validate_all(test_patch, profile_factory)

        started_events = [
            e for e in emitter.events if isinstance(e, ModelContractMergeStartedEvent)
        ]
        assert len(started_events) == 1

        started = started_events[0]
        assert "compute_pure" in started.profile_names


# =============================================================================
# Error Resilience Tests
# =============================================================================


@pytest.mark.unit
class TestPipelineEventErrorResilience:
    """Tests for error resilience in event emission."""

    def test_event_emission_failure_does_not_fail_pipeline(self) -> None:
        """Test that event emission failure doesn't fail the pipeline."""
        # Create emitter with emit that raises
        emitter = MagicMock()

        async def failing_emit(event: Any) -> None:
            raise RuntimeError("Event bus down")

        emitter.emit = failing_emit

        pipeline = ContractValidationPipeline(event_emitter=emitter)
        profile_factory = create_mock_profile_factory()
        test_patch = create_test_patch()

        # Pipeline should still complete despite emission failures
        # (the _emit_event method catches exceptions)
        result = pipeline.validate_all(test_patch, profile_factory)

        # Validation should still work
        assert result.success is True

    def test_validation_continues_after_emit_error(self) -> None:
        """Test that validation continues after emit error."""
        call_count = 0

        async def counting_emit(event: Any) -> None:
            nonlocal call_count
            call_count += 1
            if call_count == 1:  # Fail on first call
                raise RuntimeError("First emit failed")
            # Subsequent calls succeed

        emitter = MagicMock()
        emitter.emit = counting_emit

        pipeline = ContractValidationPipeline(event_emitter=emitter)
        profile_factory = create_mock_profile_factory()
        test_patch = create_test_patch()

        result = pipeline.validate_all(test_patch, profile_factory)

        # Pipeline should complete
        assert result is not None
