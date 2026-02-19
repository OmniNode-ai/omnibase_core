# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for ContractMergeEngine event emission.

Tests cover:
- merge_started event at merge begin
- merge_completed event with diff summary
- Duration tracking in events
- correlation_id propagation
- run_id generation and usage
- No events when emitter is None (backward compatibility)

Related:
    - OMN-1151: Event emission for contract merge engine
"""

from __future__ import annotations

from typing import Any
from unittest.mock import Mock
from uuid import UUID, uuid4

import pytest

from omnibase_core.enums import EnumNodeType
from omnibase_core.merge.contract_merge_engine import ContractMergeEngine
from omnibase_core.models.contracts.model_contract_patch import ModelContractPatch
from omnibase_core.models.contracts.model_profile_reference import ModelProfileReference
from omnibase_core.models.events.contract_validation import (
    ModelContractMergeCompletedEvent,
    ModelContractMergeStartedEvent,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer

# =============================================================================
# Test Fixtures and Helpers
# =============================================================================


class MockEmitter:
    """Mock event emitter that tracks emitted events.

    Uses the sync methods expected by ContractMergeEngine.
    """

    def __init__(self) -> None:
        self.events: list[Any] = []
        self.merge_started_events: list[ModelContractMergeStartedEvent] = []
        self.merge_completed_events: list[ModelContractMergeCompletedEvent] = []

    def emit_merge_started(self, event: ModelContractMergeStartedEvent) -> None:
        """Capture merge started event."""
        self.events.append(event)
        self.merge_started_events.append(event)

    def emit_merge_completed(self, event: ModelContractMergeCompletedEvent) -> None:
        """Capture merge completed event."""
        self.events.append(event)
        self.merge_completed_events.append(event)

    # Other methods for completeness (not used by merge engine)
    def emit_validation_started(self, event: Any) -> None:
        self.events.append(event)

    def emit_validation_passed(self, event: Any) -> None:
        self.events.append(event)

    def emit_validation_failed(self, event: Any) -> None:
        self.events.append(event)


def create_mock_base_contract() -> Mock:
    """Create a mock base contract that the merge engine can work with."""
    mock = Mock()
    mock.name = "base_contract"
    mock.contract_version = ModelSemVer(major=0, minor=1, patch=0)
    mock.description = "Base contract description"
    mock.node_type = EnumNodeType.COMPUTE_GENERIC
    mock.input_model = "BaseInput"
    mock.output_model = "BaseOutput"
    mock.handlers = []
    mock.dependencies = []
    mock.consumed_events = []
    mock.capability_inputs = []
    mock.capability_outputs = []
    mock.behavior = None
    mock.tags = []

    mock.model_dump = Mock(
        return_value={
            "name": "base_contract",
            "contract_version": {"major": 0, "minor": 1, "patch": 0},
            "description": "Base contract description",
            "node_type": EnumNodeType.COMPUTE_GENERIC,
            "input_model": "BaseInput",
            "output_model": "BaseOutput",
            "handlers": [],
            "dependencies": [],
            "consumed_events": [],
            "capability_inputs": [],
            "capability_outputs": [],
            "behavior": None,
            "tags": [],
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
    name: str = "test-handler",
    profile: str = "compute_pure",
    version: str = "1.0.0",
) -> ModelContractPatch:
    """Create a test patch for merge testing."""
    return ModelContractPatch(
        extends=ModelProfileReference(
            profile=profile,
            version=version,
        ),
        name=name,
        node_version=ModelSemVer(major=1, minor=0, patch=0),
        description="Test handler description",
    )


# =============================================================================
# Basic Event Emission Tests
# =============================================================================


@pytest.mark.unit
class TestMergeEngineEventEmission:
    """Tests for basic event emission behavior."""

    def test_no_events_when_emitter_is_none(self) -> None:
        """Test that no events are emitted when emitter is None."""
        profile_factory = create_mock_profile_factory()
        engine = ContractMergeEngine(
            profile_factory=profile_factory,
            event_emitter=None,
        )
        patch = create_test_patch()

        # Should complete without error
        result = engine.merge(patch)

        # Merge should still work
        assert result is not None
        assert result.name == "test-handler"

    def test_merge_started_event_emitted_at_start(self) -> None:
        """Test that merge_started event is emitted at merge begin."""
        emitter = MockEmitter()
        profile_factory = create_mock_profile_factory()
        engine = ContractMergeEngine(
            profile_factory=profile_factory,
            event_emitter=emitter,
        )
        patch = create_test_patch()

        engine.merge(patch)

        assert len(emitter.merge_started_events) == 1

    def test_merge_completed_event_emitted_at_end(self) -> None:
        """Test that merge_completed event is emitted at merge end."""
        emitter = MockEmitter()
        profile_factory = create_mock_profile_factory()
        engine = ContractMergeEngine(
            profile_factory=profile_factory,
            event_emitter=emitter,
        )
        patch = create_test_patch()

        engine.merge(patch)

        assert len(emitter.merge_completed_events) == 1

    def test_events_emitted_in_correct_order(self) -> None:
        """Test that started comes before completed."""
        emitter = MockEmitter()
        profile_factory = create_mock_profile_factory()
        engine = ContractMergeEngine(
            profile_factory=profile_factory,
            event_emitter=emitter,
        )
        patch = create_test_patch()

        engine.merge(patch)

        assert len(emitter.events) == 2
        assert isinstance(emitter.events[0], ModelContractMergeStartedEvent)
        assert isinstance(emitter.events[1], ModelContractMergeCompletedEvent)


# =============================================================================
# Merge Started Event Tests
# =============================================================================


@pytest.mark.unit
class TestMergeStartedEvent:
    """Tests for merge_started event content."""

    def test_started_has_contract_name(self) -> None:
        """Test that started event has correct contract_name."""
        emitter = MockEmitter()
        profile_factory = create_mock_profile_factory()
        engine = ContractMergeEngine(
            profile_factory=profile_factory,
            event_emitter=emitter,
        )
        patch = create_test_patch(name="my-handler")

        engine.merge(patch)

        started = emitter.merge_started_events[0]
        assert started.contract_name == "my-handler"

    def test_started_uses_profile_when_no_name(self) -> None:
        """Test that started uses profile name when patch has no name."""
        emitter = MockEmitter()
        profile_factory = create_mock_profile_factory()
        engine = ContractMergeEngine(
            profile_factory=profile_factory,
            event_emitter=emitter,
        )
        patch = ModelContractPatch(
            extends=ModelProfileReference(
                profile="compute_pure",
                version="1.0.0",
            ),
            # No name field - should use base name
        )

        engine.merge(patch)

        started = emitter.merge_started_events[0]
        # Should use the base contract name or profile name
        assert started.contract_name is not None

    def test_started_has_profile_names(self) -> None:
        """Test that started event has profile_names populated."""
        emitter = MockEmitter()
        profile_factory = create_mock_profile_factory()
        engine = ContractMergeEngine(
            profile_factory=profile_factory,
            event_emitter=emitter,
        )
        patch = create_test_patch(profile="effect_api")

        engine.merge(patch)

        started = emitter.merge_started_events[0]
        assert "effect_api" in started.profile_names

    def test_started_has_run_id(self) -> None:
        """Test that started event has run_id."""
        emitter = MockEmitter()
        profile_factory = create_mock_profile_factory()
        engine = ContractMergeEngine(
            profile_factory=profile_factory,
            event_emitter=emitter,
        )
        patch = create_test_patch()

        engine.merge(patch)

        started = emitter.merge_started_events[0]
        assert started.run_id is not None
        assert isinstance(started.run_id, UUID)


# =============================================================================
# Merge Completed Event Tests
# =============================================================================


@pytest.mark.unit
class TestMergeCompletedEvent:
    """Tests for merge_completed event content."""

    def test_completed_has_effective_contract_name(self) -> None:
        """Test that completed event has effective_contract_name."""
        emitter = MockEmitter()
        profile_factory = create_mock_profile_factory()
        engine = ContractMergeEngine(
            profile_factory=profile_factory,
            event_emitter=emitter,
        )
        patch = create_test_patch(name="my-handler")

        engine.merge(patch)

        completed = emitter.merge_completed_events[0]
        assert completed.effective_contract_name == "my-handler"

    def test_completed_has_duration(self) -> None:
        """Test that completed event has non-negative duration."""
        emitter = MockEmitter()
        profile_factory = create_mock_profile_factory()
        engine = ContractMergeEngine(
            profile_factory=profile_factory,
            event_emitter=emitter,
        )
        patch = create_test_patch()

        engine.merge(patch)

        completed = emitter.merge_completed_events[0]
        assert completed.duration_ms >= 0

    def test_completed_has_defaults_applied_true(self) -> None:
        """Test that completed event has defaults_applied=True."""
        emitter = MockEmitter()
        profile_factory = create_mock_profile_factory()
        engine = ContractMergeEngine(
            profile_factory=profile_factory,
            event_emitter=emitter,
        )
        patch = create_test_patch()

        engine.merge(patch)

        completed = emitter.merge_completed_events[0]
        assert completed.defaults_applied is True

    def test_completed_has_run_id(self) -> None:
        """Test that completed event has run_id."""
        emitter = MockEmitter()
        profile_factory = create_mock_profile_factory()
        engine = ContractMergeEngine(
            profile_factory=profile_factory,
            event_emitter=emitter,
        )
        patch = create_test_patch()

        engine.merge(patch)

        completed = emitter.merge_completed_events[0]
        assert completed.run_id is not None
        assert isinstance(completed.run_id, UUID)


# =============================================================================
# Run ID Consistency Tests
# =============================================================================


@pytest.mark.unit
class TestMergeEngineRunId:
    """Tests for run_id consistency."""

    def test_run_id_consistent_between_events(self) -> None:
        """Test that run_id is the same for started and completed events."""
        emitter = MockEmitter()
        profile_factory = create_mock_profile_factory()
        engine = ContractMergeEngine(
            profile_factory=profile_factory,
            event_emitter=emitter,
        )
        patch = create_test_patch()

        engine.merge(patch)

        started = emitter.merge_started_events[0]
        completed = emitter.merge_completed_events[0]
        assert started.run_id == completed.run_id

    def test_provided_run_id_used(self) -> None:
        """Test that provided run_id is used in events."""
        emitter = MockEmitter()
        profile_factory = create_mock_profile_factory()
        engine = ContractMergeEngine(
            profile_factory=profile_factory,
            event_emitter=emitter,
        )
        patch = create_test_patch()
        custom_run_id = uuid4()

        engine.merge(patch, run_id=custom_run_id)

        started = emitter.merge_started_events[0]
        completed = emitter.merge_completed_events[0]
        assert started.run_id == custom_run_id
        assert completed.run_id == custom_run_id

    def test_generated_run_id_when_not_provided(self) -> None:
        """Test that run_id is generated when not provided."""
        emitter = MockEmitter()
        profile_factory = create_mock_profile_factory()
        engine = ContractMergeEngine(
            profile_factory=profile_factory,
            event_emitter=emitter,
        )
        patch = create_test_patch()

        engine.merge(patch)  # No run_id provided

        started = emitter.merge_started_events[0]
        assert started.run_id is not None

    def test_different_merges_have_different_run_ids(self) -> None:
        """Test that different merge operations have different run_ids."""
        emitter = MockEmitter()
        profile_factory = create_mock_profile_factory()
        engine = ContractMergeEngine(
            profile_factory=profile_factory,
            event_emitter=emitter,
        )
        patch = create_test_patch()

        engine.merge(patch)
        first_run_id = emitter.merge_started_events[0].run_id

        engine.merge(patch)
        second_run_id = emitter.merge_started_events[1].run_id

        assert first_run_id != second_run_id


# =============================================================================
# Correlation ID Tests
# =============================================================================


@pytest.mark.unit
class TestMergeEngineCorrelationId:
    """Tests for correlation_id propagation."""

    def test_correlation_id_propagated_to_events(self) -> None:
        """Test that correlation_id is propagated to emitted events."""
        correlation_id = uuid4()
        emitter = MockEmitter()
        profile_factory = create_mock_profile_factory()
        engine = ContractMergeEngine(
            profile_factory=profile_factory,
            event_emitter=emitter,
            correlation_id=correlation_id,
        )
        patch = create_test_patch()

        engine.merge(patch)

        started = emitter.merge_started_events[0]
        completed = emitter.merge_completed_events[0]
        assert started.correlation_id == correlation_id
        assert completed.correlation_id == correlation_id

    def test_no_correlation_id_when_not_provided(self) -> None:
        """Test that events have None correlation_id when not provided."""
        emitter = MockEmitter()
        profile_factory = create_mock_profile_factory()
        engine = ContractMergeEngine(
            profile_factory=profile_factory,
            event_emitter=emitter,
            # No correlation_id provided
        )
        patch = create_test_patch()

        engine.merge(patch)

        started = emitter.merge_started_events[0]
        completed = emitter.merge_completed_events[0]
        assert started.correlation_id is None
        assert completed.correlation_id is None


# =============================================================================
# Duration Tracking Tests
# =============================================================================


@pytest.mark.unit
class TestMergeEngineDuration:
    """Tests for duration tracking in events."""

    def test_duration_is_non_negative(self) -> None:
        """Test that duration is always non-negative."""
        emitter = MockEmitter()
        profile_factory = create_mock_profile_factory()
        engine = ContractMergeEngine(
            profile_factory=profile_factory,
            event_emitter=emitter,
        )
        patch = create_test_patch()

        # Run multiple times
        for _ in range(5):
            engine.merge(patch)

        for completed in emitter.merge_completed_events:
            assert completed.duration_ms >= 0

    def test_duration_reflects_actual_time(self) -> None:
        """Test that duration reflects actual elapsed time."""
        emitter = MockEmitter()
        profile_factory = create_mock_profile_factory()
        engine = ContractMergeEngine(
            profile_factory=profile_factory,
            event_emitter=emitter,
        )
        patch = create_test_patch()

        # Perform merge
        engine.merge(patch)

        completed = emitter.merge_completed_events[0]
        # Duration should be recorded (could be 0 for very fast operations)
        assert completed.duration_ms >= 0
        # Should be reasonably small for simple merge
        assert completed.duration_ms < 10000  # Less than 10 seconds


# =============================================================================
# Contract Name Tests
# =============================================================================


@pytest.mark.unit
class TestMergeEngineContractNames:
    """Tests for contract name handling in events."""

    def test_contract_name_in_started_matches_completed(self) -> None:
        """Test that contract_name is consistent between started and completed."""
        emitter = MockEmitter()
        profile_factory = create_mock_profile_factory()
        engine = ContractMergeEngine(
            profile_factory=profile_factory,
            event_emitter=emitter,
        )
        patch = create_test_patch(name="consistent-handler")

        engine.merge(patch)

        started = emitter.merge_started_events[0]
        completed = emitter.merge_completed_events[0]
        assert started.contract_name == completed.contract_name

    def test_effective_name_reflects_merged_result(self) -> None:
        """Test that effective_contract_name reflects the actual merged name."""
        emitter = MockEmitter()
        profile_factory = create_mock_profile_factory()
        engine = ContractMergeEngine(
            profile_factory=profile_factory,
            event_emitter=emitter,
        )
        patch = create_test_patch(name="final-handler-name")

        result = engine.merge(patch)

        completed = emitter.merge_completed_events[0]
        assert completed.effective_contract_name == result.name
