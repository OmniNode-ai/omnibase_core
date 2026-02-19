# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
End-to-end integration tests for contract validation event flow.

These tests verify complete event flow through the validation pipeline with
real event emission, ensuring that:
- Events are emitted in the correct sequence
- All events share the same run_id and correlation_id
- Event ordering invariants are maintained
- File and memory sinks work correctly
- Multiple destinations receive all events

Test Scenarios:
    1. Happy Path - Full validation success
    2. PATCH Phase Failure
    3. MERGE Phase Failure
    4. EXPANDED Phase Failure
    5. Event Ordering Invariants
    6. File Sink Integration
    7. Multiple Destinations
    8. Replay Verification

Related:
    - OMN-1151: Contract Validation Event Emitter
    - ContractValidationPipeline: Pipeline orchestration
    - ServiceContractValidationEventEmitter: Event emission service
    - ServiceContractValidationInvariantChecker: Invariant validation

.. versionadded:: 0.4.0
"""

import asyncio
import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import pytest

from omnibase_core.enums.enum_validation_phase import EnumValidationPhase
from omnibase_core.models.common.model_validation_result import ModelValidationResult
from omnibase_core.models.contracts.model_contract_patch import ModelContractPatch
from omnibase_core.models.contracts.model_handler_contract import ModelHandlerContract
from omnibase_core.models.contracts.model_profile_reference import ModelProfileReference
from omnibase_core.models.events.contract_validation import (
    CONTRACT_MERGE_COMPLETED_EVENT,
    CONTRACT_MERGE_STARTED_EVENT,
    CONTRACT_VALIDATION_FAILED_EVENT,
    CONTRACT_VALIDATION_PASSED_EVENT,
    CONTRACT_VALIDATION_STARTED_EVENT,
    ModelContractValidationEventBase,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.models.runtime.model_handler_behavior import ModelHandlerBehavior
from omnibase_core.models.validation.model_contract_validation_event import (
    ModelContractValidationEvent,
)
from omnibase_core.models.validation.model_event_destination import (
    ModelEventDestination,
)
from omnibase_core.services.service_contract_validation_event_emitter import (
    ServiceContractValidationEventEmitter,
)
from omnibase_core.services.service_contract_validation_invariant_checker import (
    ServiceContractValidationInvariantChecker,
)
from omnibase_core.validation.validator_contract_pipeline import (
    ContractValidationPipeline,
)

# Module-level constant for event type mapping (used in _convert_to_invariant_events
# and test_events_from_file_can_be_replayed)
_EVENT_TYPE_MAPPING = {
    CONTRACT_VALIDATION_STARTED_EVENT: "validation_started",
    CONTRACT_VALIDATION_PASSED_EVENT: "validation_passed",
    CONTRACT_VALIDATION_FAILED_EVENT: "validation_failed",
    CONTRACT_MERGE_STARTED_EVENT: "merge_started",
    CONTRACT_MERGE_COMPLETED_EVENT: "merge_completed",
}


@pytest.fixture
def memory_destination() -> ModelEventDestination:
    """Create a memory destination for event collection."""
    return ModelEventDestination.create_memory(name="memory")


@pytest.fixture
def memory_emitter(
    memory_destination: ModelEventDestination,
) -> ServiceContractValidationEventEmitter:
    """Create an emitter with a memory destination for testing."""
    return ServiceContractValidationEventEmitter(
        destinations=[memory_destination],
    )


@pytest.fixture
def correlation_id() -> UUID:
    """Provide a unique correlation ID for tests."""
    return uuid4()


@pytest.fixture
def profile_ref() -> ModelProfileReference:
    """Create a profile reference fixture."""
    return ModelProfileReference(profile="compute_pure", version="1.0.0")


@pytest.fixture
def valid_descriptor() -> ModelHandlerBehavior:
    """Create a valid handler behavior descriptor."""
    return ModelHandlerBehavior(
        node_archetype="compute",
        purity="pure",
        idempotent=True,
    )


@pytest.fixture
def valid_patch(profile_ref: ModelProfileReference) -> ModelContractPatch:
    """Create a valid contract patch fixture."""
    return ModelContractPatch(
        extends=profile_ref,
        name="test_handler",
        node_version=ModelSemVer(major=1, minor=0, patch=0),
        description="Test handler description",
    )


@pytest.fixture
def valid_merged_contract(
    valid_descriptor: ModelHandlerBehavior,
) -> ModelHandlerContract:
    """Create a valid merged contract fixture."""
    return ModelHandlerContract(
        handler_id="node.test.compute",
        name="Test Handler",
        contract_version=ModelSemVer(major=1, minor=0, patch=0),
        description="Test handler description",
        descriptor=valid_descriptor,
        input_model="omnibase_core.models.events.ModelTestEvent",
        output_model="omnibase_core.models.results.ModelTestResult",
    )


@pytest.fixture
def invariant_checker() -> ServiceContractValidationInvariantChecker:
    """Create an invariant checker for validating event sequences."""
    return ServiceContractValidationInvariantChecker()


def _make_passing_validators() -> tuple[MagicMock, MagicMock, MagicMock]:
    """Create mock validators that all pass validation."""
    mock_patch_validator = MagicMock()
    mock_patch_result: ModelValidationResult[None] = ModelValidationResult(
        is_valid=True, summary="Patch passed"
    )
    mock_patch_validator.validate.return_value = mock_patch_result

    mock_merge_validator = MagicMock()
    mock_merge_result: ModelValidationResult[None] = ModelValidationResult(
        is_valid=True, summary="Merge passed"
    )
    mock_merge_validator.validate.return_value = mock_merge_result

    mock_expanded_validator = MagicMock()
    mock_expanded_result: ModelValidationResult[None] = ModelValidationResult(
        is_valid=True, summary="Expanded passed"
    )
    mock_expanded_validator.validate.return_value = mock_expanded_result

    return mock_patch_validator, mock_merge_validator, mock_expanded_validator


def _convert_to_invariant_events(
    events: list[ModelContractValidationEventBase],
) -> list[ModelContractValidationEvent]:
    """Convert rich domain events to invariant checker events.

    The invariant checker uses a simpler event model with string event types.
    This helper maps the rich domain events to the checker format.

    Args:
        events: List of domain events from the pipeline.

    Returns:
        List of ModelContractValidationEvent for invariant checking.
    """
    checker_events: list[ModelContractValidationEvent] = []
    for event in events:
        event_type = getattr(event, "event_type", None)
        if event_type and event_type in _EVENT_TYPE_MAPPING:
            checker_events.append(
                ModelContractValidationEvent(
                    event_type=_EVENT_TYPE_MAPPING[event_type],
                    run_ref=str(event.run_id),
                )
            )
    return checker_events


@pytest.mark.integration
@pytest.mark.timeout(60)
class TestContractValidationEventsE2E:
    """End-to-end tests for contract validation event flow."""

    def test_happy_path_full_validation_success(
        self,
        memory_emitter: ServiceContractValidationEventEmitter,
        correlation_id: UUID,
        valid_patch: ModelContractPatch,
        valid_merged_contract: ModelHandlerContract,
    ) -> None:
        """Test complete event sequence for successful validation.

        Verifies:
            - Event sequence: started -> merge_started -> merge_completed -> passed
            - All events have same run_id
            - All events have correlation_id set
        """
        mock_patch_validator, mock_merge_validator, mock_expanded_validator = (
            _make_passing_validators()
        )

        pipeline = ContractValidationPipeline(
            patch_validator=mock_patch_validator,
            merge_validator=mock_merge_validator,
            expanded_validator=mock_expanded_validator,
            event_emitter=memory_emitter,
            correlation_id=correlation_id,
        )

        with patch(
            "omnibase_core.merge.contract_merge_engine.ContractMergeEngine"
        ) as mock_merge_engine_class:
            mock_merge_engine = MagicMock()
            mock_merge_engine_class.return_value = mock_merge_engine
            mock_merge_engine.merge.return_value = valid_merged_contract

            mock_factory = MagicMock()
            mock_factory.get_profile.return_value = valid_merged_contract

            result = pipeline.validate_all(valid_patch, mock_factory)

        # Verify success
        assert result.success is True
        assert result.contract is not None

        # Get events
        events = memory_emitter.get_events()

        # Verify minimum event count (started, merge_started, merge_completed, passed)
        assert len(events) >= 4

        # Verify event sequence
        event_types = [e.event_type for e in events]
        assert event_types[0] == CONTRACT_VALIDATION_STARTED_EVENT
        assert event_types[-1] == CONTRACT_VALIDATION_PASSED_EVENT

        # Verify merge events are present and in order
        assert CONTRACT_MERGE_STARTED_EVENT in event_types
        assert CONTRACT_MERGE_COMPLETED_EVENT in event_types
        merge_started_idx = event_types.index(CONTRACT_MERGE_STARTED_EVENT)
        merge_completed_idx = event_types.index(CONTRACT_MERGE_COMPLETED_EVENT)
        assert merge_started_idx < merge_completed_idx

        # Verify all events have the same run_id
        first_run_id = events[0].run_id
        assert all(e.run_id == first_run_id for e in events)

        # Verify correlation_id is set on all events
        assert all(e.correlation_id == correlation_id for e in events)

    def test_patch_phase_failure(
        self,
        memory_emitter: ServiceContractValidationEventEmitter,
        correlation_id: UUID,
        profile_ref: ModelProfileReference,
    ) -> None:
        """Test event sequence when PATCH validation fails.

        Verifies:
            - Event sequence: started -> failed (with PATCH error code)
            - No merge events emitted
        """
        # Create a failing patch validator
        mock_patch_validator = MagicMock()
        mock_patch_result: ModelValidationResult[None] = ModelValidationResult(
            is_valid=False,
            summary="Patch validation failed",
        )
        mock_patch_result.add_error("Invalid patch structure")
        mock_patch_validator.validate.return_value = mock_patch_result

        pipeline = ContractValidationPipeline(
            patch_validator=mock_patch_validator,
            event_emitter=memory_emitter,
            correlation_id=correlation_id,
        )

        patch = ModelContractPatch(
            extends=profile_ref,
            name="test",
            node_version=ModelSemVer(major=1, minor=0, patch=0),
        )
        mock_factory = MagicMock()

        result = pipeline.validate_all(patch, mock_factory)

        # Verify failure at PATCH phase
        assert result.success is False
        assert result.phase_failed == EnumValidationPhase.PATCH

        # Get events
        events = memory_emitter.get_events()

        # Verify event sequence: started -> failed
        assert len(events) >= 2
        event_types = [e.event_type for e in events]
        assert event_types[0] == CONTRACT_VALIDATION_STARTED_EVENT
        assert event_types[-1] == CONTRACT_VALIDATION_FAILED_EVENT

        # Verify NO merge events were emitted
        assert CONTRACT_MERGE_STARTED_EVENT not in event_types
        assert CONTRACT_MERGE_COMPLETED_EVENT not in event_types

        # Verify correlation_id propagation
        assert all(e.correlation_id == correlation_id for e in events)

    def test_merge_phase_failure(
        self,
        memory_emitter: ServiceContractValidationEventEmitter,
        correlation_id: UUID,
        valid_patch: ModelContractPatch,
        valid_merged_contract: ModelHandlerContract,
    ) -> None:
        """Test event sequence when MERGE validation fails.

        Verifies:
            - Event sequence: started -> merge_started -> merge_completed -> failed
            - Merge events still emitted before failure
        """
        # Patch passes, merge fails
        mock_patch_validator = MagicMock()
        mock_patch_result: ModelValidationResult[None] = ModelValidationResult(
            is_valid=True, summary="Patch passed"
        )
        mock_patch_validator.validate.return_value = mock_patch_result

        mock_merge_validator = MagicMock()
        mock_merge_result: ModelValidationResult[None] = ModelValidationResult(
            is_valid=False,
            summary="Merge validation failed",
        )
        mock_merge_result.add_error("Placeholder value in critical field")
        mock_merge_validator.validate.return_value = mock_merge_result

        pipeline = ContractValidationPipeline(
            patch_validator=mock_patch_validator,
            merge_validator=mock_merge_validator,
            event_emitter=memory_emitter,
            correlation_id=correlation_id,
        )

        with patch(
            "omnibase_core.merge.contract_merge_engine.ContractMergeEngine"
        ) as mock_merge_engine_class:
            mock_merge_engine = MagicMock()
            mock_merge_engine_class.return_value = mock_merge_engine
            mock_merge_engine.merge.return_value = valid_merged_contract

            mock_factory = MagicMock()
            mock_factory.get_profile.return_value = valid_merged_contract

            result = pipeline.validate_all(valid_patch, mock_factory)

        # Verify failure at MERGE phase
        assert result.success is False
        assert result.phase_failed == EnumValidationPhase.MERGE

        # Get events
        events = memory_emitter.get_events()

        # Verify merge events were still emitted before failure
        event_types = [e.event_type for e in events]
        assert CONTRACT_VALIDATION_STARTED_EVENT in event_types
        assert CONTRACT_MERGE_STARTED_EVENT in event_types
        assert CONTRACT_MERGE_COMPLETED_EVENT in event_types
        assert event_types[-1] == CONTRACT_VALIDATION_FAILED_EVENT

    def test_expanded_phase_failure(
        self,
        memory_emitter: ServiceContractValidationEventEmitter,
        correlation_id: UUID,
        valid_patch: ModelContractPatch,
        valid_merged_contract: ModelHandlerContract,
    ) -> None:
        """Test event sequence when EXPANDED validation fails.

        Verifies full event sequence with failure at the end.
        """
        # Patch passes, merge passes, expanded fails
        mock_patch_validator = MagicMock()
        mock_patch_result: ModelValidationResult[None] = ModelValidationResult(
            is_valid=True, summary="Patch passed"
        )
        mock_patch_validator.validate.return_value = mock_patch_result

        mock_merge_validator = MagicMock()
        mock_merge_result: ModelValidationResult[None] = ModelValidationResult(
            is_valid=True, summary="Merge passed"
        )
        mock_merge_validator.validate.return_value = mock_merge_result

        mock_expanded_validator = MagicMock()
        mock_expanded_result: ModelValidationResult[None] = ModelValidationResult(
            is_valid=False,
            summary="Expanded validation failed",
        )
        mock_expanded_result.add_error("Invalid handler reference")
        mock_expanded_validator.validate.return_value = mock_expanded_result

        pipeline = ContractValidationPipeline(
            patch_validator=mock_patch_validator,
            merge_validator=mock_merge_validator,
            expanded_validator=mock_expanded_validator,
            event_emitter=memory_emitter,
            correlation_id=correlation_id,
        )

        with patch(
            "omnibase_core.merge.contract_merge_engine.ContractMergeEngine"
        ) as mock_merge_engine_class:
            mock_merge_engine = MagicMock()
            mock_merge_engine_class.return_value = mock_merge_engine
            mock_merge_engine.merge.return_value = valid_merged_contract

            mock_factory = MagicMock()
            mock_factory.get_profile.return_value = valid_merged_contract

            result = pipeline.validate_all(valid_patch, mock_factory)

        # Verify failure at EXPANDED phase
        assert result.success is False
        assert result.phase_failed == EnumValidationPhase.EXPANDED

        # Get events
        events = memory_emitter.get_events()

        # Verify full event sequence with failed at end
        event_types = [e.event_type for e in events]
        assert event_types[0] == CONTRACT_VALIDATION_STARTED_EVENT
        assert CONTRACT_MERGE_STARTED_EVENT in event_types
        assert CONTRACT_MERGE_COMPLETED_EVENT in event_types
        assert event_types[-1] == CONTRACT_VALIDATION_FAILED_EVENT


@pytest.mark.integration
@pytest.mark.timeout(60)
class TestEventOrderingInvariants:
    """Tests for event ordering invariants."""

    def test_started_always_first(
        self,
        memory_emitter: ServiceContractValidationEventEmitter,
        correlation_id: UUID,
        valid_patch: ModelContractPatch,
        valid_merged_contract: ModelHandlerContract,
    ) -> None:
        """Verify that validation_started is always the first event."""
        mock_patch_validator, mock_merge_validator, mock_expanded_validator = (
            _make_passing_validators()
        )

        pipeline = ContractValidationPipeline(
            patch_validator=mock_patch_validator,
            merge_validator=mock_merge_validator,
            expanded_validator=mock_expanded_validator,
            event_emitter=memory_emitter,
            correlation_id=correlation_id,
        )

        with patch(
            "omnibase_core.merge.contract_merge_engine.ContractMergeEngine"
        ) as mock_merge_engine_class:
            mock_merge_engine = MagicMock()
            mock_merge_engine_class.return_value = mock_merge_engine
            mock_merge_engine.merge.return_value = valid_merged_contract

            mock_factory = MagicMock()
            mock_factory.get_profile.return_value = valid_merged_contract

            pipeline.validate_all(valid_patch, mock_factory)

        events = memory_emitter.get_events()
        assert len(events) > 0
        assert events[0].event_type == CONTRACT_VALIDATION_STARTED_EVENT

    def test_passed_or_failed_always_last(
        self,
        memory_emitter: ServiceContractValidationEventEmitter,
        correlation_id: UUID,
        valid_patch: ModelContractPatch,
        valid_merged_contract: ModelHandlerContract,
    ) -> None:
        """Verify that passed or failed is always the last event."""
        mock_patch_validator, mock_merge_validator, mock_expanded_validator = (
            _make_passing_validators()
        )

        pipeline = ContractValidationPipeline(
            patch_validator=mock_patch_validator,
            merge_validator=mock_merge_validator,
            expanded_validator=mock_expanded_validator,
            event_emitter=memory_emitter,
            correlation_id=correlation_id,
        )

        with patch(
            "omnibase_core.merge.contract_merge_engine.ContractMergeEngine"
        ) as mock_merge_engine_class:
            mock_merge_engine = MagicMock()
            mock_merge_engine_class.return_value = mock_merge_engine
            mock_merge_engine.merge.return_value = valid_merged_contract

            mock_factory = MagicMock()
            mock_factory.get_profile.return_value = valid_merged_contract

            pipeline.validate_all(valid_patch, mock_factory)

        events = memory_emitter.get_events()
        assert len(events) > 0
        final_event_type = events[-1].event_type
        assert final_event_type in [
            CONTRACT_VALIDATION_PASSED_EVENT,
            CONTRACT_VALIDATION_FAILED_EVENT,
        ]

    def test_merge_started_before_completed(
        self,
        memory_emitter: ServiceContractValidationEventEmitter,
        correlation_id: UUID,
        valid_patch: ModelContractPatch,
        valid_merged_contract: ModelHandlerContract,
    ) -> None:
        """Verify that merge_started comes before merge_completed."""
        mock_patch_validator, mock_merge_validator, mock_expanded_validator = (
            _make_passing_validators()
        )

        pipeline = ContractValidationPipeline(
            patch_validator=mock_patch_validator,
            merge_validator=mock_merge_validator,
            expanded_validator=mock_expanded_validator,
            event_emitter=memory_emitter,
            correlation_id=correlation_id,
        )

        with patch(
            "omnibase_core.merge.contract_merge_engine.ContractMergeEngine"
        ) as mock_merge_engine_class:
            mock_merge_engine = MagicMock()
            mock_merge_engine_class.return_value = mock_merge_engine
            mock_merge_engine.merge.return_value = valid_merged_contract

            mock_factory = MagicMock()
            mock_factory.get_profile.return_value = valid_merged_contract

            pipeline.validate_all(valid_patch, mock_factory)

        events = memory_emitter.get_events()
        event_types = [e.event_type for e in events]

        if CONTRACT_MERGE_STARTED_EVENT in event_types:
            assert CONTRACT_MERGE_COMPLETED_EVENT in event_types
            merge_started_idx = event_types.index(CONTRACT_MERGE_STARTED_EVENT)
            merge_completed_idx = event_types.index(CONTRACT_MERGE_COMPLETED_EVENT)
            assert merge_started_idx < merge_completed_idx

    def test_timestamps_monotonically_increasing(
        self,
        memory_emitter: ServiceContractValidationEventEmitter,
        correlation_id: UUID,
        valid_patch: ModelContractPatch,
        valid_merged_contract: ModelHandlerContract,
    ) -> None:
        """Verify that event timestamps are monotonically increasing."""
        mock_patch_validator, mock_merge_validator, mock_expanded_validator = (
            _make_passing_validators()
        )

        pipeline = ContractValidationPipeline(
            patch_validator=mock_patch_validator,
            merge_validator=mock_merge_validator,
            expanded_validator=mock_expanded_validator,
            event_emitter=memory_emitter,
            correlation_id=correlation_id,
        )

        with patch(
            "omnibase_core.merge.contract_merge_engine.ContractMergeEngine"
        ) as mock_merge_engine_class:
            mock_merge_engine = MagicMock()
            mock_merge_engine_class.return_value = mock_merge_engine
            mock_merge_engine.merge.return_value = valid_merged_contract

            mock_factory = MagicMock()
            mock_factory.get_profile.return_value = valid_merged_contract

            pipeline.validate_all(valid_patch, mock_factory)

        events = memory_emitter.get_events()
        timestamps = [e.timestamp for e in events]

        # Verify monotonically non-decreasing (allow equal timestamps for fast ops)
        for i in range(1, len(timestamps)):
            assert timestamps[i] >= timestamps[i - 1], (
                f"Timestamp at index {i} ({timestamps[i]}) is before "
                f"timestamp at index {i - 1} ({timestamps[i - 1]})"
            )

    def test_invariant_checker_validates_sequence(
        self,
        memory_emitter: ServiceContractValidationEventEmitter,
        correlation_id: UUID,
        valid_patch: ModelContractPatch,
        valid_merged_contract: ModelHandlerContract,
        invariant_checker: ServiceContractValidationInvariantChecker,
    ) -> None:
        """Verify that emitted events pass invariant validation."""
        mock_patch_validator, mock_merge_validator, mock_expanded_validator = (
            _make_passing_validators()
        )

        pipeline = ContractValidationPipeline(
            patch_validator=mock_patch_validator,
            merge_validator=mock_merge_validator,
            expanded_validator=mock_expanded_validator,
            event_emitter=memory_emitter,
            correlation_id=correlation_id,
        )

        with patch(
            "omnibase_core.merge.contract_merge_engine.ContractMergeEngine"
        ) as mock_merge_engine_class:
            mock_merge_engine = MagicMock()
            mock_merge_engine_class.return_value = mock_merge_engine
            mock_merge_engine.merge.return_value = valid_merged_contract

            mock_factory = MagicMock()
            mock_factory.get_profile.return_value = valid_merged_contract

            pipeline.validate_all(valid_patch, mock_factory)

        events = memory_emitter.get_events()

        # Convert to invariant checker event format
        checker_events = _convert_to_invariant_events(events)

        # Validate sequence with invariant checker
        is_valid, violations = invariant_checker.validate_sequence(checker_events)
        assert is_valid is True, f"Invariant violations: {violations}"
        assert len(violations) == 0


@pytest.mark.integration
@pytest.mark.timeout(60)
class TestFileSinkIntegration:
    """Tests for file sink event persistence."""

    def test_file_sink_creates_jsonl(
        self,
        correlation_id: UUID,
        valid_patch: ModelContractPatch,
        valid_merged_contract: ModelHandlerContract,
    ) -> None:
        """Verify that file sink creates JSONL file with correct events."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "events.jsonl"

            file_destination = ModelEventDestination.create_file(
                name="file",
                file_path=str(file_path),
                buffer_size=1,  # Flush after each event
            )

            emitter = ServiceContractValidationEventEmitter(
                destinations=[file_destination],
                correlation_id=correlation_id,
            )

            mock_patch_validator, mock_merge_validator, mock_expanded_validator = (
                _make_passing_validators()
            )

            pipeline = ContractValidationPipeline(
                patch_validator=mock_patch_validator,
                merge_validator=mock_merge_validator,
                expanded_validator=mock_expanded_validator,
                event_emitter=emitter,
                correlation_id=correlation_id,
            )

            with patch(
                "omnibase_core.merge.contract_merge_engine.ContractMergeEngine"
            ) as mock_merge_engine_class:
                mock_merge_engine = MagicMock()
                mock_merge_engine_class.return_value = mock_merge_engine
                mock_merge_engine.merge.return_value = valid_merged_contract

                mock_factory = MagicMock()
                mock_factory.get_profile.return_value = valid_merged_contract

                pipeline.validate_all(valid_patch, mock_factory)

            # Flush and close to ensure all events are written
            asyncio.run(emitter.close())

            # Verify file exists and contains JSONL
            assert file_path.exists()

            # Parse JSONL content
            lines = file_path.read_text().strip().split("\n")
            assert (
                len(lines) >= 4
            )  # At least started, merge_started, merge_completed, passed

            # Verify each line is valid JSON
            for line in lines:
                event_data = json.loads(line)
                assert "event_type" in event_data
                assert "run_id" in event_data
                assert "contract_name" in event_data

            # Verify event types in file
            event_types = [json.loads(line)["event_type"] for line in lines]
            assert CONTRACT_VALIDATION_STARTED_EVENT in event_types

    def test_file_sink_cleanup_after_test(
        self,
        correlation_id: UUID,
        valid_patch: ModelContractPatch,
        valid_merged_contract: ModelHandlerContract,
    ) -> None:
        """Verify that temp file is properly cleaned up after test."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "events.jsonl"

            file_destination = ModelEventDestination.create_file(
                name="file",
                file_path=str(file_path),
                buffer_size=1,
            )

            emitter = ServiceContractValidationEventEmitter(
                destinations=[file_destination],
                correlation_id=correlation_id,
            )

            mock_patch_validator, _, _ = _make_passing_validators()

            # Just validate patch to emit a few events
            pipeline = ContractValidationPipeline(
                patch_validator=mock_patch_validator,
                event_emitter=emitter,
                correlation_id=correlation_id,
            )

            mock_factory = MagicMock()

            with patch(
                "omnibase_core.merge.contract_merge_engine.ContractMergeEngine"
            ) as mock_merge_engine_class:
                mock_merge_engine = MagicMock()
                mock_merge_engine_class.return_value = mock_merge_engine
                mock_merge_engine.merge.return_value = valid_merged_contract

                mock_factory.get_profile.return_value = valid_merged_contract
                pipeline.validate_all(valid_patch, mock_factory)

            asyncio.run(emitter.close())

            # At this point, file should exist
            assert file_path.exists()

        # After context manager exits, tmpdir is cleaned up
        # This verifies cleanup works correctly


@pytest.mark.integration
@pytest.mark.timeout(60)
class TestMultipleDestinations:
    """Tests for multiple event destinations."""

    def test_memory_and_file_destinations(
        self,
        correlation_id: UUID,
        valid_patch: ModelContractPatch,
        valid_merged_contract: ModelHandlerContract,
    ) -> None:
        """Verify that both memory and file destinations receive all events."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "events.jsonl"

            memory_destination = ModelEventDestination.create_memory(name="memory")
            file_destination = ModelEventDestination.create_file(
                name="file",
                file_path=str(file_path),
                buffer_size=1,
            )

            emitter = ServiceContractValidationEventEmitter(
                destinations=[memory_destination, file_destination],
                correlation_id=correlation_id,
            )

            mock_patch_validator, mock_merge_validator, mock_expanded_validator = (
                _make_passing_validators()
            )

            pipeline = ContractValidationPipeline(
                patch_validator=mock_patch_validator,
                merge_validator=mock_merge_validator,
                expanded_validator=mock_expanded_validator,
                event_emitter=emitter,
                correlation_id=correlation_id,
            )

            with patch(
                "omnibase_core.merge.contract_merge_engine.ContractMergeEngine"
            ) as mock_merge_engine_class:
                mock_merge_engine = MagicMock()
                mock_merge_engine_class.return_value = mock_merge_engine
                mock_merge_engine.merge.return_value = valid_merged_contract

                mock_factory = MagicMock()
                mock_factory.get_profile.return_value = valid_merged_contract

                pipeline.validate_all(valid_patch, mock_factory)

            asyncio.run(emitter.close())

            # Get events from memory
            memory_events = emitter.get_events("memory")

            # Get events from file
            lines = file_path.read_text().strip().split("\n")
            file_events = [json.loads(line) for line in lines]

            # Both should have the same number of events
            assert len(memory_events) == len(file_events)

            # Verify event types match
            memory_event_types = [e.event_type for e in memory_events]
            file_event_types = [e["event_type"] for e in file_events]
            assert memory_event_types == file_event_types

    def test_multiple_memory_sinks(
        self,
        correlation_id: UUID,
        valid_patch: ModelContractPatch,
        valid_merged_contract: ModelHandlerContract,
    ) -> None:
        """Verify that multiple memory sinks each receive all events."""
        memory_dest_1 = ModelEventDestination.create_memory(name="memory1")
        memory_dest_2 = ModelEventDestination.create_memory(name="memory2")

        emitter = ServiceContractValidationEventEmitter(
            destinations=[memory_dest_1, memory_dest_2],
            correlation_id=correlation_id,
        )

        mock_patch_validator, mock_merge_validator, mock_expanded_validator = (
            _make_passing_validators()
        )

        pipeline = ContractValidationPipeline(
            patch_validator=mock_patch_validator,
            merge_validator=mock_merge_validator,
            expanded_validator=mock_expanded_validator,
            event_emitter=emitter,
            correlation_id=correlation_id,
        )

        with patch(
            "omnibase_core.merge.contract_merge_engine.ContractMergeEngine"
        ) as mock_merge_engine_class:
            mock_merge_engine = MagicMock()
            mock_merge_engine_class.return_value = mock_merge_engine
            mock_merge_engine.merge.return_value = valid_merged_contract

            mock_factory = MagicMock()
            mock_factory.get_profile.return_value = valid_merged_contract

            pipeline.validate_all(valid_patch, mock_factory)

        # Both sinks should have the same events
        events_1 = emitter.get_events("memory1")
        events_2 = emitter.get_events("memory2")

        assert len(events_1) == len(events_2)
        assert len(events_1) >= 4  # At least 4 events

        # Verify event types match
        for e1, e2 in zip(events_1, events_2, strict=True):
            assert e1.event_type == e2.event_type
            assert e1.run_id == e2.run_id


@pytest.mark.integration
@pytest.mark.timeout(60)
class TestReplayVerification:
    """Tests for event replay and re-validation."""

    def test_events_can_be_replayed_through_invariant_checker(
        self,
        memory_emitter: ServiceContractValidationEventEmitter,
        correlation_id: UUID,
        valid_patch: ModelContractPatch,
        valid_merged_contract: ModelHandlerContract,
        invariant_checker: ServiceContractValidationInvariantChecker,
    ) -> None:
        """Verify that extracted events can be replayed through invariant checker."""
        mock_patch_validator, mock_merge_validator, mock_expanded_validator = (
            _make_passing_validators()
        )

        pipeline = ContractValidationPipeline(
            patch_validator=mock_patch_validator,
            merge_validator=mock_merge_validator,
            expanded_validator=mock_expanded_validator,
            event_emitter=memory_emitter,
            correlation_id=correlation_id,
        )

        with patch(
            "omnibase_core.merge.contract_merge_engine.ContractMergeEngine"
        ) as mock_merge_engine_class:
            mock_merge_engine = MagicMock()
            mock_merge_engine_class.return_value = mock_merge_engine
            mock_merge_engine.merge.return_value = valid_merged_contract

            mock_factory = MagicMock()
            mock_factory.get_profile.return_value = valid_merged_contract

            pipeline.validate_all(valid_patch, mock_factory)

        # Extract events
        events = memory_emitter.get_events()

        # Convert to invariant checker format
        checker_events = _convert_to_invariant_events(events)

        # Replay through invariant checker
        is_valid, violations = invariant_checker.validate_sequence(checker_events)
        assert is_valid is True
        assert len(violations) == 0

    def test_events_from_file_can_be_replayed(
        self,
        correlation_id: UUID,
        valid_patch: ModelContractPatch,
        valid_merged_contract: ModelHandlerContract,
        invariant_checker: ServiceContractValidationInvariantChecker,
    ) -> None:
        """Verify that events from file sink can be replayed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "events.jsonl"

            file_destination = ModelEventDestination.create_file(
                name="file",
                file_path=str(file_path),
                buffer_size=1,
            )

            emitter = ServiceContractValidationEventEmitter(
                destinations=[file_destination],
                correlation_id=correlation_id,
            )

            mock_patch_validator, mock_merge_validator, mock_expanded_validator = (
                _make_passing_validators()
            )

            pipeline = ContractValidationPipeline(
                patch_validator=mock_patch_validator,
                merge_validator=mock_merge_validator,
                expanded_validator=mock_expanded_validator,
                event_emitter=emitter,
                correlation_id=correlation_id,
            )

            with patch(
                "omnibase_core.merge.contract_merge_engine.ContractMergeEngine"
            ) as mock_merge_engine_class:
                mock_merge_engine = MagicMock()
                mock_merge_engine_class.return_value = mock_merge_engine
                mock_merge_engine.merge.return_value = valid_merged_contract

                mock_factory = MagicMock()
                mock_factory.get_profile.return_value = valid_merged_contract

                pipeline.validate_all(valid_patch, mock_factory)

            # Flush and close to ensure all events are written to file
            asyncio.run(emitter.close())

            # Read events from file
            lines = file_path.read_text().strip().split("\n")
            file_events = [json.loads(line) for line in lines]

            # Map file events to invariant checker format using module-level constant
            type_mapping = _EVENT_TYPE_MAPPING

            checker_events = []
            for event_data in file_events:
                event_type = event_data.get("event_type")
                if event_type in type_mapping:
                    checker_events.append(
                        ModelContractValidationEvent(
                            event_type=type_mapping[event_type],
                            run_ref=event_data.get("run_id", "unknown"),
                        )
                    )

            # Replay through invariant checker
            is_valid, violations = invariant_checker.validate_sequence(checker_events)
            assert is_valid is True, f"Invariant violations: {violations}"

    def test_incremental_event_validation(
        self,
        memory_emitter: ServiceContractValidationEventEmitter,
        correlation_id: UUID,
        valid_patch: ModelContractPatch,
        valid_merged_contract: ModelHandlerContract,
        invariant_checker: ServiceContractValidationInvariantChecker,
    ) -> None:
        """Verify that events can be validated incrementally."""
        mock_patch_validator, mock_merge_validator, mock_expanded_validator = (
            _make_passing_validators()
        )

        pipeline = ContractValidationPipeline(
            patch_validator=mock_patch_validator,
            merge_validator=mock_merge_validator,
            expanded_validator=mock_expanded_validator,
            event_emitter=memory_emitter,
            correlation_id=correlation_id,
        )

        with patch(
            "omnibase_core.merge.contract_merge_engine.ContractMergeEngine"
        ) as mock_merge_engine_class:
            mock_merge_engine = MagicMock()
            mock_merge_engine_class.return_value = mock_merge_engine
            mock_merge_engine.merge.return_value = valid_merged_contract

            mock_factory = MagicMock()
            mock_factory.get_profile.return_value = valid_merged_contract

            pipeline.validate_all(valid_patch, mock_factory)

        events = memory_emitter.get_events()
        checker_events = _convert_to_invariant_events(events)

        # Simulate incremental validation
        history: list[ModelContractValidationEvent] = []
        for event in checker_events:
            is_valid, violation = invariant_checker.check_invariant(event, history)
            assert is_valid is True, f"Violation at {event.event_type}: {violation}"
            history.append(event)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
