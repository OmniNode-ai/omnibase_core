"""
Tests for ModelAction with pure typed ModelActionMetadata.

Tests verify that ModelAction.metadata uses pure type safety:
1. ModelActionMetadata (typed, with IDE support)
2. NO dict fallback - backward compatibility removed for type safety

This ensures full type safety without hybrid approaches.
"""

from datetime import datetime
from typing import Literal
from uuid import UUID, uuid4

import pytest
from pydantic import BaseModel, ConfigDict, ValidationError

from omnibase_core.enums.enum_workflow_execution import EnumActionType
from omnibase_core.models.core.model_action_category import ModelActionCategory
from omnibase_core.models.core.model_action_metadata import ModelActionMetadata
from omnibase_core.models.core.model_node_action_type import ModelNodeActionType
from omnibase_core.models.orchestrator.model_action import ModelAction


# Minimal test payload implementing ProtocolActionPayload
class _TestActionPayload(BaseModel):
    """Minimal payload for unit tests."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)
    kind: Literal["test.action"] = "test.action"
    data: str = "test"


# Test helper for creating valid action type payload
def _create_test_payload() -> _TestActionPayload:
    """Create a minimal valid payload for test ModelAction instances."""
    return _TestActionPayload()


@pytest.mark.unit
class TestModelActionBasicCreation:
    """Test basic ModelAction creation and validation."""

    def test_action_minimal_creation(self) -> None:
        """Test creating ModelAction with minimal required fields."""
        action = ModelAction(
            action_type=EnumActionType.COMPUTE,
            target_node_type="compute",
            lease_id=uuid4(),
            epoch=1,
            payload=_create_test_payload(),
        )

        assert action.action_id is not None
        assert isinstance(action.action_id, UUID)
        assert action.action_type == EnumActionType.COMPUTE
        assert action.target_node_type == "compute"
        assert isinstance(action.lease_id, UUID)
        assert action.epoch == 1
        assert action.priority == 1  # Default
        assert action.timeout_ms == 30000  # Default
        assert action.retry_count == 0  # Default
        assert isinstance(action.metadata, ModelActionMetadata)  # Now typed
        assert action.metadata.parameters == {}  # Default empty parameters
        assert isinstance(action.created_at, datetime)

    def test_action_full_creation(self) -> None:
        """Test creating ModelAction with all fields specified."""
        action_id = uuid4()
        lease_id = uuid4()
        dep1 = uuid4()
        dep2 = uuid4()
        created = datetime.now()

        # Create typed metadata
        custom_metadata = ModelActionMetadata()
        custom_metadata.parameters = {"custom": "data"}

        action = ModelAction(
            action_id=action_id,
            action_type=EnumActionType.EFFECT,
            target_node_type="effect",
            payload=_create_test_payload(),
            dependencies=[dep1, dep2],
            priority=5,
            timeout_ms=60000,
            lease_id=lease_id,
            epoch=42,
            retry_count=3,
            metadata=custom_metadata,
            created_at=created,
        )

        assert action.action_id == action_id
        assert action.action_type == EnumActionType.EFFECT
        assert action.target_node_type == "effect"
        assert isinstance(action.payload, _TestActionPayload)
        assert action.dependencies == [dep1, dep2]
        assert action.priority == 5
        assert action.timeout_ms == 60000
        assert action.lease_id == lease_id
        assert action.epoch == 42
        assert action.retry_count == 3
        assert isinstance(action.metadata, ModelActionMetadata)
        assert action.metadata.parameters == {"custom": "data"}
        assert action.created_at == created

    def test_action_immutability(self) -> None:
        """Test that ModelAction is immutable (frozen=True)."""
        action = ModelAction(
            action_type=EnumActionType.COMPUTE,
            target_node_type="compute",
            lease_id=uuid4(),
            epoch=1,
            payload=_create_test_payload(),
        )

        with pytest.raises(ValidationError, match="frozen"):
            action.priority = 10  # type: ignore[misc]

    def test_action_model_copy(self) -> None:
        """Test creating modified copy with model_copy()."""
        original = ModelAction(
            action_type=EnumActionType.COMPUTE,
            target_node_type="compute",
            lease_id=uuid4(),
            epoch=1,
            priority=1,
            retry_count=0,
            payload=_create_test_payload(),
        )

        # Create modified copy
        modified = original.model_copy(update={"priority": 5, "retry_count": 1})

        assert original.priority == 1
        assert original.retry_count == 0
        assert modified.priority == 5
        assert modified.retry_count == 1
        assert modified.action_id == original.action_id
        assert modified.lease_id == original.lease_id


@pytest.mark.unit
class TestModelActionValidation:
    """Test ModelAction field validation."""

    def test_action_target_node_type_too_short(self) -> None:
        """Test that target_node_type must be at least 1 character."""
        with pytest.raises(ValidationError, match="at least 1 character"):
            ModelAction(
                action_type=EnumActionType.COMPUTE,
                target_node_type="",  # Too short
                lease_id=uuid4(),
                epoch=1,
                payload=_create_test_payload(),
            )

    def test_action_target_node_type_too_long(self) -> None:
        """Test that target_node_type cannot exceed 100 characters."""
        with pytest.raises(ValidationError, match="at most 100 characters"):
            ModelAction(
                action_type=EnumActionType.COMPUTE,
                target_node_type="x" * 101,  # Too long
                lease_id=uuid4(),
                epoch=1,
                payload=_create_test_payload(),
            )

    def test_action_priority_too_low(self) -> None:
        """Test that priority must be >= 1."""
        with pytest.raises(ValidationError, match="greater than or equal to 1"):
            ModelAction(
                action_type=EnumActionType.COMPUTE,
                target_node_type="compute",
                lease_id=uuid4(),
                epoch=1,
                priority=0,  # Too low
                payload=_create_test_payload(),
            )

    def test_action_priority_too_high(self) -> None:
        """Test that priority must be <= 10."""
        with pytest.raises(ValidationError, match="less than or equal to 10"):
            ModelAction(
                action_type=EnumActionType.COMPUTE,
                target_node_type="compute",
                lease_id=uuid4(),
                epoch=1,
                priority=11,  # Too high
                payload=_create_test_payload(),
            )

    def test_action_timeout_too_low(self) -> None:
        """Test that timeout_ms must be >= 100."""
        with pytest.raises(ValidationError, match="greater than or equal to 100"):
            ModelAction(
                action_type=EnumActionType.COMPUTE,
                target_node_type="compute",
                lease_id=uuid4(),
                epoch=1,
                timeout_ms=50,  # Too low
                payload=_create_test_payload(),
            )

    def test_action_timeout_too_high(self) -> None:
        """Test that timeout_ms must be <= 300000."""
        with pytest.raises(ValidationError, match="less than or equal to 300000"):
            ModelAction(
                action_type=EnumActionType.COMPUTE,
                target_node_type="compute",
                lease_id=uuid4(),
                epoch=1,
                timeout_ms=400000,  # Too high
                payload=_create_test_payload(),
            )

    def test_action_epoch_negative(self) -> None:
        """Test that epoch must be >= 0."""
        with pytest.raises(ValidationError, match="greater than or equal to 0"):
            ModelAction(
                action_type=EnumActionType.COMPUTE,
                target_node_type="compute",
                lease_id=uuid4(),
                epoch=-1,  # Negative
                payload=_create_test_payload(),
            )

    def test_action_retry_count_negative(self) -> None:
        """Test that retry_count must be >= 0."""
        with pytest.raises(ValidationError, match="greater than or equal to 0"):
            ModelAction(
                action_type=EnumActionType.COMPUTE,
                target_node_type="compute",
                lease_id=uuid4(),
                epoch=1,
                retry_count=-1,  # Negative
                payload=_create_test_payload(),
            )

    def test_action_retry_count_too_high(self) -> None:
        """Test that retry_count must be <= 10."""
        with pytest.raises(ValidationError, match="less than or equal to 10"):
            ModelAction(
                action_type=EnumActionType.COMPUTE,
                target_node_type="compute",
                lease_id=uuid4(),
                epoch=1,
                retry_count=11,  # Too high
                payload=_create_test_payload(),
            )

    def test_action_extra_fields_forbidden(self) -> None:
        """Test that extra fields are forbidden."""
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            ModelAction(
                action_type=EnumActionType.COMPUTE,
                target_node_type="compute",
                lease_id=uuid4(),
                epoch=1,
                payload=_create_test_payload(),
                unknown_field="value",  # type: ignore[call-arg]
            )


@pytest.mark.unit
class TestModelActionMetadataTyped:
    """Test ModelAction with typed ModelActionMetadata."""

    def test_action_with_typed_metadata(self) -> None:
        """Test ModelAction with typed ModelActionMetadata for type safety and IDE support."""
        # Create typed metadata with required fields
        category = ModelActionCategory(
            name="compute",
            display_name="Compute",
            description="Compute operations",
        )
        action_type_model = ModelNodeActionType(
            name="transform",
            category=category,
            display_name="Transform",
            description="Data transformation",
        )

        typed_metadata = ModelActionMetadata(
            action_type=action_type_model,
            action_name="TestTransform",
        )

        # Create action with typed metadata
        action = ModelAction(
            action_type=EnumActionType.COMPUTE,
            target_node_type="compute",
            lease_id=uuid4(),
            epoch=1,
            metadata=typed_metadata,
            payload=_create_test_payload(),
        )

        # Verify metadata is preserved as ModelActionMetadata
        assert isinstance(action.metadata, ModelActionMetadata)
        assert action.metadata.action_name == "TestTransform"
        assert action.metadata.action_type.name == "transform"
        assert action.metadata.action_type.category.name == "compute"

    def test_action_typed_metadata_with_correlation_ids(self) -> None:
        """Test typed metadata preserves correlation IDs."""
        category = ModelActionCategory(
            name="effect",
            display_name="Effect",
            description="External I/O",
        )
        action_type_model = ModelNodeActionType(
            name="api_call",
            category=category,
            display_name="API Call",
            description="External API call",
        )

        correlation_id = uuid4()
        parent_id = uuid4()

        typed_metadata = ModelActionMetadata(
            action_type=action_type_model,
            action_name="FetchUserData",
            correlation_id=correlation_id,
            parent_correlation_id=parent_id,
        )

        action = ModelAction(
            action_type=EnumActionType.COMPUTE,
            target_node_type="effect",
            lease_id=uuid4(),
            epoch=1,
            metadata=typed_metadata,
            payload=_create_test_payload(),
        )

        assert isinstance(action.metadata, ModelActionMetadata)
        assert action.metadata.correlation_id == correlation_id
        assert action.metadata.parent_correlation_id == parent_id

    def test_action_typed_metadata_with_trust_score(self) -> None:
        """Test typed metadata preserves trust score."""
        category = ModelActionCategory(
            name="reducer",
            display_name="Reducer",
            description="State reduction",
        )
        action_type_model = ModelNodeActionType(
            name="aggregate",
            category=category,
            display_name="Aggregate",
            description="Data aggregation",
        )

        typed_metadata = ModelActionMetadata(
            action_type=action_type_model,
            action_name="AggregateMetrics",
            trust_score=0.85,
        )

        action = ModelAction(
            action_type=EnumActionType.COMPUTE,
            target_node_type="reducer",
            lease_id=uuid4(),
            epoch=1,
            metadata=typed_metadata,
            payload=_create_test_payload(),
        )

        assert isinstance(action.metadata, ModelActionMetadata)
        assert action.metadata.trust_score == 0.85


@pytest.mark.unit
class TestModelActionMetadataDefault:
    """Test ModelAction with default/empty metadata."""

    def test_action_with_empty_metadata_default(self) -> None:
        """Test ModelAction with default empty metadata."""
        # Create action without metadata (should use default)
        action = ModelAction(
            action_type=EnumActionType.COMPUTE,
            target_node_type="reducer",
            lease_id=uuid4(),
            epoch=1,
            # No metadata provided
            payload=_create_test_payload(),
        )

        # Verify default is ModelActionMetadata instance
        assert action.metadata is not None
        assert isinstance(action.metadata, ModelActionMetadata)

    def test_action_metadata_default_factory(self) -> None:
        """Test that metadata uses default_factory for independent instances."""
        action1 = ModelAction(
            action_type=EnumActionType.COMPUTE,
            target_node_type="compute",
            lease_id=uuid4(),
            epoch=1,
            payload=_create_test_payload(),
        )

        action2 = ModelAction(
            action_type=EnumActionType.COMPUTE,
            target_node_type="compute",
            lease_id=uuid4(),
            epoch=1,
            payload=_create_test_payload(),
        )

        # Each should have independent metadata instances
        assert action1.metadata is not action2.metadata
        assert id(action1.metadata) != id(action2.metadata)
        assert isinstance(action1.metadata, ModelActionMetadata)
        assert isinstance(action2.metadata, ModelActionMetadata)


@pytest.mark.unit
class TestModelActionMetadataNoneHandling:
    """Test ModelAction metadata None handling."""

    def test_action_metadata_uses_default_factory(self) -> None:
        """Test that missing metadata uses default_factory=ModelActionMetadata.

        When metadata is not provided, Pydantic uses default_factory to create
        a new ModelActionMetadata instance.
        """
        # Create action without metadata
        action = ModelAction(
            action_type=EnumActionType.COMPUTE,
            target_node_type="orchestrator",
            lease_id=uuid4(),
            epoch=1,
            # metadata not provided - will use default_factory
            payload=_create_test_payload(),
        )

        # With default_factory=ModelActionMetadata, missing field becomes ModelActionMetadata instance
        assert action.metadata is not None
        assert isinstance(action.metadata, ModelActionMetadata)

    def test_action_metadata_explicit_none_not_allowed(self) -> None:
        """Test that explicitly passing None to metadata is rejected.

        Metadata field expects ModelActionMetadata, not None.
        """
        # Pydantic should reject None for ModelActionMetadata field
        with pytest.raises(ValidationError):
            ModelAction(
                action_type=EnumActionType.COMPUTE,
                target_node_type="compute",
                lease_id=uuid4(),
                epoch=1,
                metadata=None,  # type: ignore[arg-type]  # Explicit None
                payload=_create_test_payload(),
            )


@pytest.mark.unit
class TestModelActionSerialization:
    """Test ModelAction serialization and deserialization."""

    def test_action_to_dict(self) -> None:
        """Test serializing ModelAction to dict."""
        # Create typed metadata
        action_metadata = ModelActionMetadata()
        action_metadata.parameters = {"key": "value"}

        action = ModelAction(
            action_type=EnumActionType.COMPUTE,
            target_node_type="compute",
            lease_id=uuid4(),
            epoch=1,
            priority=5,
            metadata=action_metadata,
            payload=_create_test_payload(),
        )

        data = action.model_dump()

        assert data["action_type"] == EnumActionType.COMPUTE
        assert data["target_node_type"] == "compute"
        assert data["priority"] == 5
        # metadata is now a dict representation of ModelActionMetadata
        assert isinstance(data["metadata"], dict)
        assert data["metadata"]["parameters"] == {"key": "value"}

    def test_action_from_dict_with_typed_payload(self) -> None:
        """Test deserializing ModelAction from dict with typed metadata.

        Note: ModelAction uses Protocol-based payload typing, which requires
        providing a typed payload object rather than deserializing from dict.
        """
        lease_id = uuid4()
        # Create typed metadata structure
        metadata_dict = {
            "parameters": {"foo": "bar"},
            "status": "created",
        }
        # Use typed payload object (Protocol-based typing doesn't auto-deserialize)
        test_payload = _create_test_payload()
        data = {
            "action_type": EnumActionType.COMPUTE,
            "target_node_type": "effect",
            "lease_id": lease_id,
            "epoch": 2,
            "metadata": metadata_dict,
            "payload": test_payload,  # Use typed payload object
        }

        action = ModelAction.model_validate(data)

        assert action.action_type == EnumActionType.COMPUTE
        assert action.target_node_type == "effect"
        assert action.lease_id == lease_id
        assert action.epoch == 2
        assert isinstance(action.metadata, ModelActionMetadata)
        assert action.metadata.parameters == {"foo": "bar"}
        assert action.metadata.status == "created"

    def test_action_roundtrip_with_model_copy(self) -> None:
        """Test roundtrip using model_copy for immutable updates.

        Note: Protocol-based payload typing doesn't support automatic
        deserialization, so we use model_copy for roundtrip verification.
        """
        # Create typed metadata
        original_metadata = ModelActionMetadata()
        original_metadata.parameters = {"complex": {"nested": "data"}}

        original = ModelAction(
            action_type=EnumActionType.EFFECT,
            target_node_type="reducer",
            lease_id=uuid4(),
            epoch=42,
            priority=7,
            retry_count=3,
            metadata=original_metadata,
            payload=_create_test_payload(),
        )

        # Use model_copy for roundtrip (frozen model pattern)
        restored = original.model_copy()

        assert restored.action_id == original.action_id
        assert restored.action_type == original.action_type
        assert restored.target_node_type == original.target_node_type
        assert restored.lease_id == original.lease_id
        assert restored.epoch == original.epoch
        assert restored.priority == original.priority
        assert restored.retry_count == original.retry_count
        assert isinstance(restored.metadata, ModelActionMetadata)
        assert restored.metadata.parameters == original.metadata.parameters


@pytest.mark.unit
class TestModelActionLeaseSemantics:
    """Test ModelAction lease management semantics."""

    def test_action_lease_id_required(self) -> None:
        """Test that lease_id is required."""
        with pytest.raises(ValidationError, match="Field required"):
            ModelAction(
                action_type=EnumActionType.COMPUTE,
                target_node_type="compute",
                epoch=1,
                # Missing lease_id
                payload=_create_test_payload(),
            )

    def test_action_epoch_required(self) -> None:
        """Test that epoch is required."""
        with pytest.raises(ValidationError, match="Field required"):
            ModelAction(
                action_type=EnumActionType.COMPUTE,
                target_node_type="compute",
                lease_id=uuid4(),
                # Missing epoch
                payload=_create_test_payload(),
            )

    def test_action_epoch_monotonic_increment(self) -> None:
        """Test creating actions with monotonically increasing epochs."""
        lease_id = uuid4()

        action1 = ModelAction(
            action_type=EnumActionType.COMPUTE,
            target_node_type="compute",
            lease_id=lease_id,
            epoch=1,
            payload=_create_test_payload(),
        )

        action2 = ModelAction(
            action_type=EnumActionType.COMPUTE,
            target_node_type="compute",
            lease_id=lease_id,
            epoch=2,
            payload=_create_test_payload(),
        )

        action3 = ModelAction(
            action_type=EnumActionType.COMPUTE,
            target_node_type="compute",
            lease_id=lease_id,
            epoch=3,
            payload=_create_test_payload(),
        )

        assert action1.epoch < action2.epoch < action3.epoch
        assert action1.lease_id == action2.lease_id == action3.lease_id


@pytest.mark.unit
class TestModelActionDependencies:
    """Test ModelAction dependency management."""

    def test_action_no_dependencies(self) -> None:
        """Test action with no dependencies."""
        action = ModelAction(
            action_type=EnumActionType.COMPUTE,
            target_node_type="compute",
            lease_id=uuid4(),
            epoch=1,
            payload=_create_test_payload(),
        )

        assert action.dependencies == []
        assert len(action.dependencies) == 0

    def test_action_single_dependency(self) -> None:
        """Test action with single dependency."""
        dep_id = uuid4()

        action = ModelAction(
            action_type=EnumActionType.COMPUTE,
            target_node_type="compute",
            lease_id=uuid4(),
            epoch=1,
            dependencies=[dep_id],
            payload=_create_test_payload(),
        )

        assert len(action.dependencies) == 1
        assert action.dependencies[0] == dep_id

    def test_action_multiple_dependencies(self) -> None:
        """Test action with multiple dependencies."""
        dep1 = uuid4()
        dep2 = uuid4()
        dep3 = uuid4()

        action = ModelAction(
            action_type=EnumActionType.COMPUTE,
            target_node_type="compute",
            lease_id=uuid4(),
            epoch=1,
            dependencies=[dep1, dep2, dep3],
            payload=_create_test_payload(),
        )

        assert len(action.dependencies) == 3
        assert dep1 in action.dependencies
        assert dep2 in action.dependencies
        assert dep3 in action.dependencies


@pytest.mark.unit
class TestModelActionUTCDatetime:
    """Test ModelAction UTC datetime handling (OMN-1008).

    These tests verify that ModelAction.created_at uses UTC-aware datetime
    as part of the Core Payload Architecture improvements.
    """

    def test_action_created_at_is_utc_aware(self) -> None:
        """Test that created_at is timezone-aware with UTC timezone.

        This test verifies the fix from OMN-1008 where created_at was changed
        from datetime.now() (naive) to datetime.now(UTC) (timezone-aware).
        """
        from datetime import UTC

        action = ModelAction(
            action_type=EnumActionType.COMPUTE,
            target_node_type="compute",
            lease_id=uuid4(),
            epoch=1,
            payload=_create_test_payload(),
        )

        # Verify created_at is timezone-aware
        assert action.created_at.tzinfo is not None
        # Verify it's UTC
        assert action.created_at.tzinfo == UTC

    def test_action_created_at_default_factory_utc(self) -> None:
        """Test that default_factory produces UTC-aware datetime."""
        from datetime import UTC

        # Create multiple actions and verify all have UTC
        actions = [
            ModelAction(
                action_type=EnumActionType.COMPUTE,
                target_node_type="compute",
                lease_id=uuid4(),
                epoch=i,
                payload=_create_test_payload(),
            )
            for i in range(5)
        ]

        for action in actions:
            assert action.created_at.tzinfo == UTC

    def test_action_serialization_preserves_utc(self) -> None:
        """Test that serialization preserves UTC timezone info."""
        from datetime import UTC

        action = ModelAction(
            action_type=EnumActionType.COMPUTE,
            target_node_type="compute",
            lease_id=uuid4(),
            epoch=1,
            payload=_create_test_payload(),
        )

        # Serialize to dict
        data = action.model_dump()

        # The datetime in the dict should still be UTC-aware
        assert data["created_at"].tzinfo == UTC

    def test_action_explicit_utc_datetime_accepted(self) -> None:
        """Test that explicitly providing UTC datetime works correctly."""
        from datetime import UTC

        explicit_time = datetime.now(UTC)

        action = ModelAction(
            action_type=EnumActionType.COMPUTE,
            target_node_type="compute",
            lease_id=uuid4(),
            epoch=1,
            payload=_create_test_payload(),
            created_at=explicit_time,
        )

        assert action.created_at == explicit_time
        assert action.created_at.tzinfo == UTC
