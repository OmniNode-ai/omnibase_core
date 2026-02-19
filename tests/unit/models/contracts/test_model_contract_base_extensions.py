# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for ModelContractBase ONEX infrastructure extension fields.

Tests the OMN-1588 extension fields:
- handler_routing: ModelHandlerRoutingSubcontract for contract-driven routing
- yaml_consumed_events: list[ModelConsumedEventEntry] with string normalization
- yaml_published_events: list[ModelPublishedEventEntry] for event publishing

Test Categories:
1. Published Event Entry Tests
2. Consumed Event Entry Tests
3. Consumed Events Normalization Tests
4. Handler Routing Integration Tests
5. Full Contract Integration Tests
"""

import pytest
from pydantic import ValidationError

from omnibase_core.enums import EnumNodeType
from omnibase_core.models.contracts import (
    ModelAlgorithmConfig,
    ModelAlgorithmFactorConfig,
    ModelConsumedEventEntry,
    ModelContractCompute,
    ModelPerformanceRequirements,
    ModelPublishedEventEntry,
)
from omnibase_core.models.contracts.subcontracts import (
    ModelHandlerRoutingEntry,
    ModelHandlerRoutingSubcontract,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer


def _create_minimal_algorithm() -> ModelAlgorithmConfig:
    """Create a minimal valid algorithm config for testing."""
    return ModelAlgorithmConfig(
        algorithm_type="test_algorithm",
        factors={
            "factor1": ModelAlgorithmFactorConfig(
                weight=1.0,
                calculation_method="default",
            ),
        },
    )


def _create_minimal_performance() -> ModelPerformanceRequirements:
    """Create minimal performance requirements for testing."""
    return ModelPerformanceRequirements(single_operation_max_ms=1000)


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestModelPublishedEventEntry:
    """Tests for ModelPublishedEventEntry model."""

    def test_create_with_required_fields(self) -> None:
        """Test creating ModelPublishedEventEntry with required fields."""
        entry = ModelPublishedEventEntry(
            topic="jobs.events.created.v1",
            event_type="ModelEventJobCreated",
        )
        assert entry.topic == "jobs.events.created.v1"
        assert entry.event_type == "ModelEventJobCreated"

    def test_model_is_frozen(self) -> None:
        """Test that ModelPublishedEventEntry is immutable (frozen=True)."""
        entry = ModelPublishedEventEntry(
            topic="jobs.events.created.v1",
            event_type="ModelEventJobCreated",
        )
        with pytest.raises(ValidationError):
            entry.topic = "different.topic"  # type: ignore[misc]

    def test_extra_fields_forbidden(self) -> None:
        """Test that extra fields are rejected (extra='forbid')."""
        with pytest.raises(ValidationError):
            ModelPublishedEventEntry(
                topic="jobs.events.created.v1",
                event_type="ModelEventJobCreated",
                extra_field="not allowed",  # type: ignore[call-arg]
            )

    def test_missing_required_topic_raises_error(self) -> None:
        """Test that missing topic raises ValidationError."""
        with pytest.raises(ValidationError):
            ModelPublishedEventEntry(event_type="ModelEventJobCreated")  # type: ignore[call-arg]

    def test_missing_required_event_type_raises_error(self) -> None:
        """Test that missing event_type raises ValidationError."""
        with pytest.raises(ValidationError):
            ModelPublishedEventEntry(topic="jobs.events.created.v1")  # type: ignore[call-arg]

    def test_serialization_roundtrip(self) -> None:
        """Test model serialization and deserialization."""
        entry = ModelPublishedEventEntry(
            topic="jobs.events.created.v1",
            event_type="ModelEventJobCreated",
        )
        dumped = entry.model_dump()
        restored = ModelPublishedEventEntry.model_validate(dumped)
        assert restored == entry


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestModelConsumedEventEntry:
    """Tests for ModelConsumedEventEntry model."""

    def test_create_with_event_type_only(self) -> None:
        """Test creating ModelConsumedEventEntry with event_type only."""
        entry = ModelConsumedEventEntry(event_type="jobs.events.created.v1")
        assert entry.event_type == "jobs.events.created.v1"
        assert entry.handler_function is None

    def test_create_with_handler_function(self) -> None:
        """Test creating ModelConsumedEventEntry with handler_function."""
        entry = ModelConsumedEventEntry(
            event_type="jobs.events.created.v1",
            handler_function="handle_job_created",
        )
        assert entry.event_type == "jobs.events.created.v1"
        assert entry.handler_function == "handle_job_created"

    def test_model_is_frozen(self) -> None:
        """Test that ModelConsumedEventEntry is immutable (frozen=True)."""
        entry = ModelConsumedEventEntry(event_type="jobs.events.created.v1")
        with pytest.raises(ValidationError):
            entry.event_type = "different.event"  # type: ignore[misc]

    def test_extra_fields_forbidden(self) -> None:
        """Test that extra fields are rejected (extra='forbid')."""
        with pytest.raises(ValidationError):
            ModelConsumedEventEntry(
                event_type="jobs.events.created.v1",
                extra_field="not allowed",  # type: ignore[call-arg]
            )

    def test_missing_required_event_type_raises_error(self) -> None:
        """Test that missing event_type raises ValidationError."""
        with pytest.raises(ValidationError):
            ModelConsumedEventEntry()  # type: ignore[call-arg]

    def test_serialization_roundtrip(self) -> None:
        """Test model serialization and deserialization."""
        entry = ModelConsumedEventEntry(
            event_type="jobs.events.created.v1",
            handler_function="handle_job_created",
        )
        dumped = entry.model_dump()
        restored = ModelConsumedEventEntry.model_validate(dumped)
        assert restored == entry


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestYamlConsumedEventsNormalization:
    """Tests for yaml_consumed_events field normalization in ModelContractBase."""

    def _create_minimal_contract(
        self,
        yaml_consumed_events: object = None,
        yaml_published_events: object = None,
        handler_routing: object = None,
    ) -> ModelContractCompute:
        """Helper to create a minimal compute contract for testing."""
        kwargs: dict[str, object] = {
            "name": "TestContract",
            "contract_version": ModelSemVer(major=1, minor=0, patch=0),
            "description": "Test contract for extension fields",
            "node_type": EnumNodeType.COMPUTE_GENERIC,
            "input_model": "omnibase_core.models.ModelInput",
            "output_model": "omnibase_core.models.ModelOutput",
            "algorithm": _create_minimal_algorithm(),
            "performance": _create_minimal_performance(),
        }
        if yaml_consumed_events is not None:
            kwargs["yaml_consumed_events"] = yaml_consumed_events
        if yaml_published_events is not None:
            kwargs["yaml_published_events"] = yaml_published_events
        if handler_routing is not None:
            kwargs["handler_routing"] = handler_routing
        return ModelContractCompute(**kwargs)

    def test_yaml_consumed_events_empty_list_default(self) -> None:
        """Test that yaml_consumed_events defaults to empty list."""
        contract = self._create_minimal_contract()
        assert contract.yaml_consumed_events == []

    def test_yaml_consumed_events_string_list_normalized(self) -> None:
        """Test that string list is normalized to ModelConsumedEventEntry list."""
        contract = self._create_minimal_contract(
            yaml_consumed_events=["event.a.v1", "event.b.v1"]
        )
        assert len(contract.yaml_consumed_events) == 2
        assert all(
            isinstance(e, ModelConsumedEventEntry)
            for e in contract.yaml_consumed_events
        )
        assert contract.yaml_consumed_events[0].event_type == "event.a.v1"
        assert contract.yaml_consumed_events[0].handler_function is None
        assert contract.yaml_consumed_events[1].event_type == "event.b.v1"
        assert contract.yaml_consumed_events[1].handler_function is None

    def test_yaml_consumed_events_dict_list_accepted(self) -> None:
        """Test that dict list is accepted and converted to entries."""
        contract = self._create_minimal_contract(
            yaml_consumed_events=[
                {"event_type": "event.a.v1", "handler_function": "handle_a"},
                {"event_type": "event.b.v1"},
            ]
        )
        assert len(contract.yaml_consumed_events) == 2
        assert contract.yaml_consumed_events[0].event_type == "event.a.v1"
        assert contract.yaml_consumed_events[0].handler_function == "handle_a"
        assert contract.yaml_consumed_events[1].event_type == "event.b.v1"
        assert contract.yaml_consumed_events[1].handler_function is None

    def test_yaml_consumed_events_mixed_list_normalized(self) -> None:
        """Test that mixed string and dict list is normalized."""
        contract = self._create_minimal_contract(
            yaml_consumed_events=[
                "event.a.v1",
                {"event_type": "event.b.v1", "handler_function": "handle_b"},
            ]
        )
        assert len(contract.yaml_consumed_events) == 2
        assert contract.yaml_consumed_events[0].event_type == "event.a.v1"
        assert contract.yaml_consumed_events[0].handler_function is None
        assert contract.yaml_consumed_events[1].event_type == "event.b.v1"
        assert contract.yaml_consumed_events[1].handler_function == "handle_b"

    def test_yaml_consumed_events_model_instance_accepted(self) -> None:
        """Test that ModelConsumedEventEntry instances are accepted."""
        entry = ModelConsumedEventEntry(
            event_type="event.a.v1",
            handler_function="handle_a",
        )
        contract = self._create_minimal_contract(yaml_consumed_events=[entry])
        assert len(contract.yaml_consumed_events) == 1
        # Note: due to normalization, the instance is recreated from model_dump
        assert contract.yaml_consumed_events[0].event_type == "event.a.v1"
        assert contract.yaml_consumed_events[0].handler_function == "handle_a"

    def test_yaml_consumed_events_invalid_item_type_raises_error(self) -> None:
        """Test that invalid item types raise ValueError."""
        with pytest.raises(ValidationError) as exc_info:
            self._create_minimal_contract(yaml_consumed_events=[123, "valid.event"])
        assert "Invalid yaml_consumed_events item type" in str(exc_info.value)

    def test_yaml_consumed_events_non_list_raises_error(self) -> None:
        """Test that non-list yaml_consumed_events raises ValueError."""
        with pytest.raises(ValidationError) as exc_info:
            self._create_minimal_contract(yaml_consumed_events="not a list")
        assert "yaml_consumed_events must be a list" in str(exc_info.value)


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestYamlPublishedEventsField:
    """Tests for yaml_published_events field in ModelContractBase."""

    def _create_minimal_contract(
        self,
        yaml_published_events: object = None,
    ) -> ModelContractCompute:
        """Helper to create a minimal compute contract for testing."""
        kwargs: dict[str, object] = {
            "name": "TestContract",
            "contract_version": ModelSemVer(major=1, minor=0, patch=0),
            "description": "Test contract for extension fields",
            "node_type": EnumNodeType.COMPUTE_GENERIC,
            "input_model": "omnibase_core.models.ModelInput",
            "output_model": "omnibase_core.models.ModelOutput",
            "algorithm": _create_minimal_algorithm(),
            "performance": _create_minimal_performance(),
        }
        if yaml_published_events is not None:
            kwargs["yaml_published_events"] = yaml_published_events
        return ModelContractCompute(**kwargs)

    def test_yaml_published_events_empty_list_default(self) -> None:
        """Test that yaml_published_events defaults to empty list."""
        contract = self._create_minimal_contract()
        assert contract.yaml_published_events == []

    def test_yaml_published_events_dict_list_accepted(self) -> None:
        """Test that dict list is accepted for yaml_published_events."""
        contract = self._create_minimal_contract(
            yaml_published_events=[
                {"topic": "jobs.events.created.v1", "event_type": "ModelEventCreated"},
                {
                    "topic": "jobs.events.completed.v1",
                    "event_type": "ModelEventCompleted",
                },
            ]
        )
        assert len(contract.yaml_published_events) == 2
        assert contract.yaml_published_events[0].topic == "jobs.events.created.v1"
        assert contract.yaml_published_events[0].event_type == "ModelEventCreated"
        assert contract.yaml_published_events[1].topic == "jobs.events.completed.v1"
        assert contract.yaml_published_events[1].event_type == "ModelEventCompleted"

    def test_yaml_published_events_model_instance_accepted(self) -> None:
        """Test that ModelPublishedEventEntry instances are accepted."""
        entry = ModelPublishedEventEntry(
            topic="jobs.events.created.v1",
            event_type="ModelEventCreated",
        )
        contract = self._create_minimal_contract(yaml_published_events=[entry])
        assert len(contract.yaml_published_events) == 1
        assert contract.yaml_published_events[0].topic == "jobs.events.created.v1"
        assert contract.yaml_published_events[0].event_type == "ModelEventCreated"


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestYamlPublishedEventsNormalization:
    """Tests for yaml_published_events field normalization in ModelContractBase."""

    def _create_minimal_contract(
        self,
        yaml_published_events: object = None,
    ) -> ModelContractCompute:
        """Helper to create a minimal compute contract for testing."""
        kwargs: dict[str, object] = {
            "name": "TestContract",
            "contract_version": ModelSemVer(major=1, minor=0, patch=0),
            "description": "Test contract for extension fields",
            "node_type": EnumNodeType.COMPUTE_GENERIC,
            "input_model": "omnibase_core.models.ModelInput",
            "output_model": "omnibase_core.models.ModelOutput",
            "algorithm": _create_minimal_algorithm(),
            "performance": _create_minimal_performance(),
        }
        if yaml_published_events is not None:
            kwargs["yaml_published_events"] = yaml_published_events
        return ModelContractCompute(**kwargs)

    def test_yaml_published_events_string_list_normalized(self) -> None:
        """Test that string list is normalized to ModelPublishedEventEntry list.

        String values are used as both topic and event_type.
        """
        contract = self._create_minimal_contract(
            yaml_published_events=[
                "jobs.events.created.v1",
                "jobs.events.completed.v1",
            ]
        )
        assert len(contract.yaml_published_events) == 2
        assert all(
            isinstance(e, ModelPublishedEventEntry)
            for e in contract.yaml_published_events
        )
        # First entry: string used as both topic and event_type
        assert contract.yaml_published_events[0].topic == "jobs.events.created.v1"
        assert contract.yaml_published_events[0].event_type == "jobs.events.created.v1"
        # Second entry
        assert contract.yaml_published_events[1].topic == "jobs.events.completed.v1"
        assert (
            contract.yaml_published_events[1].event_type == "jobs.events.completed.v1"
        )

    def test_yaml_published_events_dict_list_passthrough(self) -> None:
        """Test that dict list is passed through unchanged."""
        contract = self._create_minimal_contract(
            yaml_published_events=[
                {"topic": "jobs.events.created.v1", "event_type": "ModelEventCreated"},
                {
                    "topic": "jobs.events.completed.v1",
                    "event_type": "ModelEventCompleted",
                },
            ]
        )
        assert len(contract.yaml_published_events) == 2
        # Dict values preserved exactly
        assert contract.yaml_published_events[0].topic == "jobs.events.created.v1"
        assert contract.yaml_published_events[0].event_type == "ModelEventCreated"
        assert contract.yaml_published_events[1].topic == "jobs.events.completed.v1"
        assert contract.yaml_published_events[1].event_type == "ModelEventCompleted"

    def test_yaml_published_events_mixed_list_normalized(self) -> None:
        """Test that mixed string and dict list is normalized correctly."""
        contract = self._create_minimal_contract(
            yaml_published_events=[
                "jobs.events.created.v1",
                {
                    "topic": "jobs.events.completed.v1",
                    "event_type": "ModelEventCompleted",
                },
            ]
        )
        assert len(contract.yaml_published_events) == 2
        # First entry: string normalized to same topic/event_type
        assert contract.yaml_published_events[0].topic == "jobs.events.created.v1"
        assert contract.yaml_published_events[0].event_type == "jobs.events.created.v1"
        # Second entry: dict preserved
        assert contract.yaml_published_events[1].topic == "jobs.events.completed.v1"
        assert contract.yaml_published_events[1].event_type == "ModelEventCompleted"

    def test_yaml_published_events_model_instance_handling(self) -> None:
        """Test that ModelPublishedEventEntry instances are converted via model_dump."""
        entry = ModelPublishedEventEntry(
            topic="jobs.events.created.v1",
            event_type="ModelEventCreated",
        )
        contract = self._create_minimal_contract(yaml_published_events=[entry])
        assert len(contract.yaml_published_events) == 1
        # Instance is recreated from model_dump
        assert contract.yaml_published_events[0].topic == "jobs.events.created.v1"
        assert contract.yaml_published_events[0].event_type == "ModelEventCreated"

    def test_yaml_published_events_invalid_item_type_raises_error(self) -> None:
        """Test that invalid item types raise ValueError."""
        with pytest.raises(ValidationError) as exc_info:
            self._create_minimal_contract(yaml_published_events=[123, "valid.event.v1"])
        assert "Invalid yaml_published_events item type" in str(exc_info.value)

    def test_yaml_published_events_non_list_raises_error(self) -> None:
        """Test that non-list yaml_published_events raises ValueError."""
        with pytest.raises(ValidationError) as exc_info:
            self._create_minimal_contract(yaml_published_events="not a list")
        assert "yaml_published_events must be a list" in str(exc_info.value)

    def test_yaml_published_events_empty_list_returns_empty(self) -> None:
        """Test that empty list input returns empty list."""
        contract = self._create_minimal_contract(yaml_published_events=[])
        assert contract.yaml_published_events == []

    def test_yaml_published_events_none_returns_empty_list(self) -> None:
        """Test that None/falsy input returns empty list via default_factory."""
        contract = self._create_minimal_contract()
        assert contract.yaml_published_events == []


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestHandlerRoutingField:
    """Tests for handler_routing field in ModelContractBase."""

    def _create_minimal_contract(
        self,
        handler_routing: object = None,
    ) -> ModelContractCompute:
        """Helper to create a minimal compute contract for testing."""
        kwargs: dict[str, object] = {
            "name": "TestContract",
            "contract_version": ModelSemVer(major=1, minor=0, patch=0),
            "description": "Test contract for extension fields",
            "node_type": EnumNodeType.COMPUTE_GENERIC,
            "input_model": "omnibase_core.models.ModelInput",
            "output_model": "omnibase_core.models.ModelOutput",
            "algorithm": _create_minimal_algorithm(),
            "performance": _create_minimal_performance(),
        }
        if handler_routing is not None:
            kwargs["handler_routing"] = handler_routing
        return ModelContractCompute(**kwargs)

    def test_handler_routing_none_default(self) -> None:
        """Test that handler_routing defaults to None."""
        contract = self._create_minimal_contract()
        assert contract.handler_routing is None

    def test_handler_routing_subcontract_accepted(self) -> None:
        """Test that ModelHandlerRoutingSubcontract is accepted."""
        routing = ModelHandlerRoutingSubcontract(
            version=ModelSemVer(major=1, minor=0, patch=0),
            handlers=[
                ModelHandlerRoutingEntry(
                    routing_key="ModelEventJobCreated",
                    handler_key="handle_job_created",
                ),
            ],
        )
        contract = self._create_minimal_contract(handler_routing=routing)
        assert contract.handler_routing is not None
        assert len(contract.handler_routing.handlers) == 1
        assert (
            contract.handler_routing.handlers[0].routing_key == "ModelEventJobCreated"
        )

    def test_handler_routing_dict_accepted(self) -> None:
        """Test that dict is accepted and converted to ModelHandlerRoutingSubcontract."""
        contract = self._create_minimal_contract(
            handler_routing={
                "version": {"major": 1, "minor": 0, "patch": 0},
                "handlers": [
                    {
                        "routing_key": "ModelEventJobCreated",
                        "handler_key": "handle_job_created",
                    },
                ],
                "default_handler": "handle_unknown",
            }
        )
        assert contract.handler_routing is not None
        assert len(contract.handler_routing.handlers) == 1
        assert contract.handler_routing.default_handler == "handle_unknown"


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestFullContractIntegration:
    """Integration tests for all extension fields together."""

    def test_contract_with_all_extension_fields(self) -> None:
        """Test creating a contract with all extension fields populated."""
        contract = ModelContractCompute(
            name="FullExtensionContract",
            contract_version=ModelSemVer(major=1, minor=0, patch=0),
            description="Contract with all extension fields",
            node_type=EnumNodeType.COMPUTE_GENERIC,
            input_model="omnibase_core.models.ModelInput",
            output_model="omnibase_core.models.ModelOutput",
            algorithm=_create_minimal_algorithm(),
            performance=_create_minimal_performance(),
            handler_routing=ModelHandlerRoutingSubcontract(
                version=ModelSemVer(major=1, minor=0, patch=0),
                handlers=[
                    ModelHandlerRoutingEntry(
                        routing_key="ModelEventA",
                        handler_key="handle_a",
                    ),
                ],
            ),
            yaml_consumed_events=[
                "event.a.v1",
                {"event_type": "event.b.v1", "handler_function": "handle_b"},
            ],
            yaml_published_events=[
                {"topic": "out.events.v1", "event_type": "ModelEventOut"},
            ],
        )

        # Verify handler_routing
        assert contract.handler_routing is not None
        assert len(contract.handler_routing.handlers) == 1

        # Verify yaml_consumed_events normalized
        assert len(contract.yaml_consumed_events) == 2
        assert contract.yaml_consumed_events[0].event_type == "event.a.v1"
        assert contract.yaml_consumed_events[1].handler_function == "handle_b"

        # Verify yaml_published_events
        assert len(contract.yaml_published_events) == 1
        assert contract.yaml_published_events[0].topic == "out.events.v1"

    def test_contract_serialization_with_extension_fields(self) -> None:
        """Test that contracts with extension fields serialize and deserialize correctly."""
        contract = ModelContractCompute(
            name="SerializationTest",
            contract_version=ModelSemVer(major=1, minor=0, patch=0),
            description="Test serialization",
            node_type=EnumNodeType.COMPUTE_GENERIC,
            input_model="omnibase_core.models.ModelInput",
            output_model="omnibase_core.models.ModelOutput",
            algorithm=_create_minimal_algorithm(),
            performance=_create_minimal_performance(),
            yaml_consumed_events=["event.a.v1"],
            yaml_published_events=[{"topic": "out.v1", "event_type": "ModelOut"}],
        )

        dumped = contract.model_dump()

        # Verify serialization includes extension fields
        assert "yaml_consumed_events" in dumped
        assert "yaml_published_events" in dumped
        assert "handler_routing" in dumped

        assert len(dumped["yaml_consumed_events"]) == 1
        assert dumped["yaml_consumed_events"][0]["event_type"] == "event.a.v1"

        assert len(dumped["yaml_published_events"]) == 1
        assert dumped["yaml_published_events"][0]["topic"] == "out.v1"

        # Verify deserialization works
        restored = ModelContractCompute.model_validate(dumped)
        assert len(restored.yaml_consumed_events) == 1
        assert len(restored.yaml_published_events) == 1
