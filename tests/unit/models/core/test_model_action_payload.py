# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

#
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for ModelActionPayload.

Tests all ModelActionPayload functionality including:
- Basic instantiation with required action field
- Default value verification for optional fields
- Field validation (trust_level bounds 0.0-1.0)
- Method tests (add_to_execution_chain, create_child_payload)
- Serialization/deserialization round-trip
- Edge cases and additional scenarios
"""

from dataclasses import dataclass, field
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.models.context.model_action_execution_context import (
    ModelActionExecutionContext,
)
from omnibase_core.models.context.model_action_parameters import ModelActionParameters
from omnibase_core.models.context.model_routing_metadata import ModelRoutingMetadata
from omnibase_core.models.context.model_service_discovery_metadata import (
    ModelServiceDiscoveryMetadata,
)
from omnibase_core.models.core.model_action_category import ModelActionCategory
from omnibase_core.models.core.model_action_payload import ModelActionPayload
from omnibase_core.models.core.model_node_action import ModelNodeAction
from omnibase_core.models.core.model_node_action_type import ModelNodeActionType
from omnibase_core.models.primitives.model_semver import ModelSemVer

# =============================================================================
# Helper Functions and Fixtures
# =============================================================================


def create_test_action(
    name: str = "test_action",
    display_name: str = "Test Action",
    description: str = "A test action for unit testing",
) -> ModelNodeAction:
    """Create a ModelNodeAction for testing."""
    category = ModelActionCategory(
        name="test_category",
        display_name="Test Category",
        description="Test category for unit tests",
    )
    action_type = ModelNodeActionType(
        name=name,
        category=category,
        display_name=display_name,
        description=description,
    )
    return ModelNodeAction(
        action_name=name,
        action_type=action_type,
        category=category,
        display_name=display_name,
        description=description,
        mcp_schema_version=ModelSemVer(major=1, minor=0, patch=0),
    )


def create_test_version() -> ModelSemVer:
    """Create a ModelSemVer for testing."""
    return ModelSemVer(major=1, minor=0, patch=0)


# =============================================================================
# Helper Classes for from_attributes Testing
# =============================================================================


@dataclass
class ActionPayloadAttrs:
    """Helper dataclass for testing from_attributes on ModelActionPayload.

    Note: Fields that have default_factory in ModelActionPayload must have
    non-None defaults here to work with from_attributes=True validation.
    """

    action: ModelNodeAction
    version: ModelSemVer
    parameters: ModelActionParameters = field(default_factory=ModelActionParameters)
    execution_context: ModelActionExecutionContext = field(
        default_factory=ModelActionExecutionContext
    )
    parent_correlation_id: UUID | None = None
    execution_chain: list[str] = field(default_factory=list)
    target_service: str | None = None
    routing_metadata: ModelRoutingMetadata = field(default_factory=ModelRoutingMetadata)
    trust_level: float = 1.0
    service_metadata: ModelServiceDiscoveryMetadata | None = None
    tool_discovery_tags: list[str] = field(default_factory=list)


# =============================================================================
# Basic Instantiation Tests
# =============================================================================


@pytest.mark.unit
class TestModelActionPayloadInstantiation:
    """Tests for ModelActionPayload instantiation."""

    def test_create_with_required_fields_only(self) -> None:
        """Test creating payload with only required fields."""
        action = create_test_action()
        version = create_test_version()

        payload = ModelActionPayload(action=action, version=version)

        assert payload.action == action
        assert payload.version == version

    def test_create_with_all_fields(self) -> None:
        """Test creating payload with all fields populated."""
        action = create_test_action()
        version = create_test_version()
        parent_id = uuid4()
        parameters = ModelActionParameters(action_name="test")
        execution_context = ModelActionExecutionContext(
            environment="production", timeout_ms=60000
        )
        routing_metadata = ModelRoutingMetadata(target_region="us-east-1")
        service_metadata = ModelServiceDiscoveryMetadata(
            service_name="test-service",
            service_version=ModelSemVer(major=2, minor=0, patch=0),
        )

        payload = ModelActionPayload(
            action=action,
            version=version,
            parameters=parameters,
            execution_context=execution_context,
            parent_correlation_id=parent_id,
            execution_chain=["action1", "action2"],
            target_service="target-service",
            routing_metadata=routing_metadata,
            trust_level=0.85,
            service_metadata=service_metadata,
            tool_discovery_tags=["tag1", "tag2", "tag3"],
        )

        assert payload.action == action
        assert payload.version == version
        assert payload.parameters == parameters
        assert payload.execution_context == execution_context
        assert payload.parent_correlation_id == parent_id
        assert payload.execution_chain == ["action1", "action2"]
        assert payload.target_service == "target-service"
        assert payload.routing_metadata == routing_metadata
        assert payload.trust_level == 0.85
        assert payload.service_metadata == service_metadata
        assert payload.tool_discovery_tags == ["tag1", "tag2", "tag3"]

    def test_create_with_partial_fields(self) -> None:
        """Test creating payload with some optional fields."""
        action = create_test_action()
        version = create_test_version()

        payload = ModelActionPayload(
            action=action,
            version=version,
            target_service="my-service",
            trust_level=0.5,
        )

        assert payload.action == action
        assert payload.target_service == "my-service"
        assert payload.trust_level == 0.5
        # Defaults should be applied
        assert payload.execution_chain == []
        assert payload.tool_discovery_tags == []


# =============================================================================
# Default Value Tests
# =============================================================================


@pytest.mark.unit
class TestModelActionPayloadDefaults:
    """Tests for ModelActionPayload default values."""

    def test_parameters_defaults_to_empty_model(self) -> None:
        """Test that parameters defaults to empty ModelActionParameters."""
        action = create_test_action()
        version = create_test_version()

        payload = ModelActionPayload(action=action, version=version)

        assert isinstance(payload.parameters, ModelActionParameters)
        assert payload.parameters.action_name is None

    def test_execution_context_defaults_to_empty_model(self) -> None:
        """Test that execution_context defaults to empty ModelActionExecutionContext."""
        action = create_test_action()
        version = create_test_version()

        payload = ModelActionPayload(action=action, version=version)

        assert isinstance(payload.execution_context, ModelActionExecutionContext)
        assert payload.execution_context.environment == "development"

    def test_parent_correlation_id_defaults_to_none(self) -> None:
        """Test that parent_correlation_id defaults to None."""
        action = create_test_action()
        version = create_test_version()

        payload = ModelActionPayload(action=action, version=version)

        assert payload.parent_correlation_id is None

    def test_execution_chain_defaults_to_empty_list(self) -> None:
        """Test that execution_chain defaults to empty list."""
        action = create_test_action()
        version = create_test_version()

        payload = ModelActionPayload(action=action, version=version)

        assert payload.execution_chain == []
        assert isinstance(payload.execution_chain, list)

    def test_target_service_defaults_to_none(self) -> None:
        """Test that target_service defaults to None."""
        action = create_test_action()
        version = create_test_version()

        payload = ModelActionPayload(action=action, version=version)

        assert payload.target_service is None

    def test_routing_metadata_defaults_to_empty_model(self) -> None:
        """Test that routing_metadata defaults to empty ModelRoutingMetadata."""
        action = create_test_action()
        version = create_test_version()

        payload = ModelActionPayload(action=action, version=version)

        assert isinstance(payload.routing_metadata, ModelRoutingMetadata)
        assert payload.routing_metadata.load_balance_strategy == "round_robin"

    def test_trust_level_defaults_to_one(self) -> None:
        """Test that trust_level defaults to 1.0."""
        action = create_test_action()
        version = create_test_version()

        payload = ModelActionPayload(action=action, version=version)

        assert payload.trust_level == 1.0

    def test_service_metadata_defaults_to_none(self) -> None:
        """Test that service_metadata defaults to None."""
        action = create_test_action()
        version = create_test_version()

        payload = ModelActionPayload(action=action, version=version)

        assert payload.service_metadata is None

    def test_tool_discovery_tags_defaults_to_empty_list(self) -> None:
        """Test that tool_discovery_tags defaults to empty list."""
        action = create_test_action()
        version = create_test_version()

        payload = ModelActionPayload(action=action, version=version)

        assert payload.tool_discovery_tags == []
        assert isinstance(payload.tool_discovery_tags, list)

    def test_default_factories_create_independent_instances(self) -> None:
        """Test that default factories create independent list instances."""
        action = create_test_action()
        version = create_test_version()

        payload1 = ModelActionPayload(action=action, version=version)
        payload2 = ModelActionPayload(action=action, version=version)

        # Verify different instances
        assert payload1.execution_chain is not payload2.execution_chain
        assert payload1.tool_discovery_tags is not payload2.tool_discovery_tags

        # Modifying one doesn't affect the other
        payload1.execution_chain.append("test")
        assert payload2.execution_chain == []


# =============================================================================
# Field Validation Tests
# =============================================================================


@pytest.mark.unit
class TestModelActionPayloadValidation:
    """Tests for ModelActionPayload field validation."""

    def test_trust_level_accepts_valid_range(self) -> None:
        """Test that trust_level accepts values between 0.0 and 1.0."""
        action = create_test_action()
        version = create_test_version()

        # Minimum value
        payload_min = ModelActionPayload(
            action=action, version=version, trust_level=0.0
        )
        assert payload_min.trust_level == 0.0

        # Maximum value
        payload_max = ModelActionPayload(
            action=action, version=version, trust_level=1.0
        )
        assert payload_max.trust_level == 1.0

        # Mid value
        payload_mid = ModelActionPayload(
            action=action, version=version, trust_level=0.5
        )
        assert payload_mid.trust_level == 0.5

    def test_trust_level_rejects_below_zero(self) -> None:
        """Test that trust_level rejects values below 0.0."""
        action = create_test_action()
        version = create_test_version()

        with pytest.raises(ValidationError) as exc_info:
            ModelActionPayload(action=action, version=version, trust_level=-0.1)

        assert "trust_level" in str(exc_info.value).lower()

    def test_trust_level_rejects_above_one(self) -> None:
        """Test that trust_level rejects values above 1.0."""
        action = create_test_action()
        version = create_test_version()

        with pytest.raises(ValidationError) as exc_info:
            ModelActionPayload(action=action, version=version, trust_level=1.1)

        assert "trust_level" in str(exc_info.value).lower()

    def test_trust_level_boundary_values(self) -> None:
        """Test trust_level boundary values precisely."""
        action = create_test_action()
        version = create_test_version()

        # Exactly at boundaries should work
        payload_zero = ModelActionPayload(
            action=action, version=version, trust_level=0.0
        )
        assert payload_zero.trust_level == 0.0

        payload_one = ModelActionPayload(
            action=action, version=version, trust_level=1.0
        )
        assert payload_one.trust_level == 1.0

        # Just outside boundaries should fail
        with pytest.raises(ValidationError):
            ModelActionPayload(action=action, version=version, trust_level=-0.001)

        with pytest.raises(ValidationError):
            ModelActionPayload(action=action, version=version, trust_level=1.001)

    def test_action_is_required(self) -> None:
        """Test that action field is required."""
        version = create_test_version()

        with pytest.raises(ValidationError) as exc_info:
            ModelActionPayload(version=version)  # type: ignore[call-arg]

        assert "action" in str(exc_info.value).lower()

    def test_version_is_required(self) -> None:
        """Test that version field is required (inherited from base)."""
        action = create_test_action()

        with pytest.raises(ValidationError) as exc_info:
            ModelActionPayload(action=action)  # type: ignore[call-arg]

        assert "version" in str(exc_info.value).lower()

    def test_version_accepts_string(self) -> None:
        """Test that version accepts string format."""
        action = create_test_action()

        payload = ModelActionPayload(action=action, version="2.1.3")  # type: ignore[arg-type]

        assert isinstance(payload.version, ModelSemVer)
        assert payload.version.major == 2
        assert payload.version.minor == 1
        assert payload.version.patch == 3

    def test_version_accepts_dict(self) -> None:
        """Test that version accepts dict format."""
        action = create_test_action()

        payload = ModelActionPayload(
            action=action,
            version={"major": 3, "minor": 2, "patch": 1},  # type: ignore[arg-type]
        )

        assert isinstance(payload.version, ModelSemVer)
        assert payload.version.major == 3
        assert payload.version.minor == 2
        assert payload.version.patch == 1


# =============================================================================
# Method Tests
# =============================================================================


@pytest.mark.unit
class TestModelActionPayloadMethods:
    """Tests for ModelActionPayload methods."""

    def test_add_to_execution_chain_appends_action(self) -> None:
        """Test that add_to_execution_chain appends action name."""
        action = create_test_action()
        version = create_test_version()

        payload = ModelActionPayload(action=action, version=version)

        payload.add_to_execution_chain("first_action")
        assert payload.execution_chain == ["first_action"]

        payload.add_to_execution_chain("second_action")
        assert payload.execution_chain == ["first_action", "second_action"]

    def test_add_to_execution_chain_with_existing_chain(self) -> None:
        """Test add_to_execution_chain with pre-existing chain."""
        action = create_test_action()
        version = create_test_version()

        payload = ModelActionPayload(
            action=action, version=version, execution_chain=["existing_action"]
        )

        payload.add_to_execution_chain("new_action")
        assert payload.execution_chain == ["existing_action", "new_action"]

    def test_create_child_payload_basic(self) -> None:
        """Test create_child_payload creates child with correct parent reference."""
        action = create_test_action()
        version = create_test_version()

        parent_payload = ModelActionPayload(
            action=action,
            version=version,
            correlation_id=uuid4(),
        )

        child_action = create_test_action(name="child_action")
        child_payload = parent_payload.create_child_payload(child_action)

        assert child_payload.action == child_action
        assert child_payload.parent_correlation_id == parent_payload.correlation_id
        assert child_payload.version == parent_payload.version

    def test_create_child_payload_inherits_execution_chain(self) -> None:
        """Test create_child_payload copies execution chain."""
        action = create_test_action()
        version = create_test_version()

        parent_payload = ModelActionPayload(
            action=action,
            version=version,
            execution_chain=["action1", "action2"],
        )

        child_action = create_test_action(name="child_action")
        child_payload = parent_payload.create_child_payload(child_action)

        assert child_payload.execution_chain == ["action1", "action2"]
        # Verify it's a copy, not same reference
        assert child_payload.execution_chain is not parent_payload.execution_chain

    def test_create_child_payload_inherits_trust_level(self) -> None:
        """Test create_child_payload inherits parent trust level when not overridden."""
        action = create_test_action()
        version = create_test_version()

        parent_payload = ModelActionPayload(
            action=action, version=version, trust_level=0.8
        )

        child_action = create_test_action(name="child_action")

        # When no trust_level provided, child inherits parent's trust level
        # (min of parent trust and default 1.0 = parent's trust)
        child = parent_payload.create_child_payload(child_action)
        assert child.trust_level == 0.8

    def test_create_child_payload_trust_level_with_higher_parent(self) -> None:
        """Test child trust level when parent has high trust level."""
        action = create_test_action()
        version = create_test_version()

        parent_payload = ModelActionPayload(
            action=action, version=version, trust_level=1.0
        )

        child_action = create_test_action(name="child_action")
        child = parent_payload.create_child_payload(child_action)

        # With parent at 1.0 and no override, child gets min(1.0, 1.0) = 1.0
        assert child.trust_level == 1.0

    def test_create_child_payload_trust_level_with_lower_parent(self) -> None:
        """Test child trust level when parent has low trust level."""
        action = create_test_action()
        version = create_test_version()

        parent_payload = ModelActionPayload(
            action=action, version=version, trust_level=0.3
        )

        child_action = create_test_action(name="child_action")
        child = parent_payload.create_child_payload(child_action)

        # With parent at 0.3 and no override, child gets min(0.3, 1.0) = 0.3
        assert child.trust_level == 0.3

    def test_create_child_payload_inherits_service_metadata(self) -> None:
        """Test create_child_payload inherits service metadata."""
        action = create_test_action()
        version = create_test_version()
        service_metadata = ModelServiceDiscoveryMetadata(
            service_name="parent-service",
            service_version=ModelSemVer(major=1, minor=0, patch=0),
        )

        parent_payload = ModelActionPayload(
            action=action, version=version, service_metadata=service_metadata
        )

        child_action = create_test_action(name="child_action")
        child_payload = parent_payload.create_child_payload(child_action)

        assert child_payload.service_metadata == service_metadata

    def test_create_child_payload_with_additional_kwargs(self) -> None:
        """Test create_child_payload accepts additional kwargs."""
        action = create_test_action()
        version = create_test_version()

        parent_payload = ModelActionPayload(action=action, version=version)

        child_action = create_test_action(name="child_action")
        child_payload = parent_payload.create_child_payload(
            child_action,
            target_service="custom-target",
            tool_discovery_tags=["tag1", "tag2"],
        )

        assert child_payload.target_service == "custom-target"
        assert child_payload.tool_discovery_tags == ["tag1", "tag2"]

    def test_create_child_payload_trust_level_via_kwargs_takes_minimum(self) -> None:
        """Test that trust_level passed in kwargs takes minimum with parent.

        This tests the fix for the duplicate keyword argument bug where passing
        trust_level in kwargs would conflict with the explicit trust_level parameter.
        """
        action = create_test_action()
        version = create_test_version()

        # Parent has trust_level 0.8
        parent_payload = ModelActionPayload(
            action=action, version=version, trust_level=0.8
        )

        child_action = create_test_action(name="child_action")

        # Child requests trust_level 0.5 via kwargs - should take min(0.8, 0.5) = 0.5
        child_payload = parent_payload.create_child_payload(
            child_action,
            trust_level=0.5,
        )
        assert child_payload.trust_level == 0.5

        # Child requests trust_level 0.9 via kwargs - should take min(0.8, 0.9) = 0.8
        child_payload_higher = parent_payload.create_child_payload(
            child_action,
            trust_level=0.9,
        )
        assert child_payload_higher.trust_level == 0.8

    def test_create_child_payload_trust_level_default_when_not_in_kwargs(self) -> None:
        """Test that trust_level uses default 1.0 when not passed in kwargs.

        When no trust_level is provided in kwargs, the default 1.0 is used,
        and the child inherits the parent's trust level via min(parent, 1.0).
        """
        action = create_test_action()
        version = create_test_version()

        # Parent with trust_level 0.7
        parent_payload = ModelActionPayload(
            action=action, version=version, trust_level=0.7
        )

        child_action = create_test_action(name="child_action")

        # No trust_level in kwargs - should use min(0.7, 1.0) = 0.7
        child_payload = parent_payload.create_child_payload(child_action)
        assert child_payload.trust_level == 0.7

        # With fully trusted parent - should use min(1.0, 1.0) = 1.0
        parent_full_trust = ModelActionPayload(
            action=action, version=version, trust_level=1.0
        )
        child_full_trust = parent_full_trust.create_child_payload(child_action)
        assert child_full_trust.trust_level == 1.0

    def test_create_child_payload_trust_level_in_kwargs_no_duplicate_error(
        self,
    ) -> None:
        """Test that passing trust_level in kwargs does not cause duplicate argument error.

        Regression test for bug where trust_level in kwargs would conflict with
        the explicit trust_level parameter in the ModelActionPayload constructor.
        """
        action = create_test_action()
        version = create_test_version()

        parent_payload = ModelActionPayload(
            action=action, version=version, trust_level=0.6
        )

        child_action = create_test_action(name="child_action")

        # This should NOT raise TypeError about duplicate keyword argument
        child_payload = parent_payload.create_child_payload(
            child_action,
            trust_level=0.4,
            target_service="test-service",
        )

        # Verify it works correctly
        assert child_payload.trust_level == 0.4  # min(0.6, 0.4) = 0.4
        assert child_payload.target_service == "test-service"
        assert child_payload.parent_correlation_id == parent_payload.correlation_id


# =============================================================================
# Serialization Tests
# =============================================================================


@pytest.mark.unit
class TestModelActionPayloadSerialization:
    """Tests for ModelActionPayload serialization."""

    def test_model_dump(self) -> None:
        """Test model_dump serialization."""
        action = create_test_action()
        version = create_test_version()

        payload = ModelActionPayload(
            action=action,
            version=version,
            trust_level=0.75,
            target_service="test-service",
        )

        data = payload.model_dump()

        assert data["trust_level"] == 0.75
        assert data["target_service"] == "test-service"
        assert "action" in data
        assert "version" in data

    def test_model_dump_json(self) -> None:
        """Test model_dump_json serialization."""
        action = create_test_action()
        version = create_test_version()

        payload = ModelActionPayload(
            action=action,
            version=version,
            trust_level=0.9,
        )

        json_str = payload.model_dump_json()

        assert isinstance(json_str, str)
        assert '"trust_level":0.9' in json_str or '"trust_level": 0.9' in json_str
        assert "test_action" in json_str

    def test_model_validate_from_dict(self) -> None:
        """Test model_validate from dictionary."""
        action = create_test_action()
        version = create_test_version()

        original = ModelActionPayload(
            action=action,
            version=version,
            trust_level=0.6,
            target_service="from-dict-service",
            execution_chain=["step1"],
        )

        data = original.model_dump()
        restored = ModelActionPayload.model_validate(data)

        assert restored.trust_level == 0.6
        assert restored.target_service == "from-dict-service"
        assert restored.execution_chain == ["step1"]

    def test_round_trip_serialization(self) -> None:
        """Test full round-trip JSON serialization."""
        action = create_test_action()
        version = create_test_version()
        parent_id = uuid4()
        correlation_id = uuid4()
        service_metadata = ModelServiceDiscoveryMetadata(
            service_name="roundtrip-service",
            service_version=ModelSemVer(major=2, minor=1, patch=0),
        )

        original = ModelActionPayload(
            action=action,
            version=version,
            parameters=ModelActionParameters(action_name="roundtrip"),
            execution_context=ModelActionExecutionContext(environment="staging"),
            parent_correlation_id=parent_id,
            correlation_id=correlation_id,
            execution_chain=["chain1", "chain2"],
            target_service="target-svc",
            routing_metadata=ModelRoutingMetadata(target_region="eu-west-1"),
            trust_level=0.77,
            service_metadata=service_metadata,
            tool_discovery_tags=["tagA", "tagB"],
        )

        json_str = original.model_dump_json()
        restored = ModelActionPayload.model_validate_json(json_str)

        assert restored.trust_level == original.trust_level
        assert restored.target_service == original.target_service
        assert restored.execution_chain == original.execution_chain
        assert restored.parent_correlation_id == original.parent_correlation_id
        assert restored.tool_discovery_tags == original.tool_discovery_tags
        assert restored.execution_context.environment == "staging"
        assert restored.routing_metadata.target_region == "eu-west-1"

    def test_model_dump_excludes_none(self) -> None:
        """Test model_dump with exclude_none option."""
        action = create_test_action()
        version = create_test_version()

        payload = ModelActionPayload(action=action, version=version)

        data = payload.model_dump(exclude_none=True)

        # Fields that were None should be excluded from the output
        expected_excluded = {
            "parent_correlation_id",
            "target_service",
            "service_metadata",
        }
        assert expected_excluded.isdisjoint(data.keys()), (
            f"None fields should be excluded; found: {expected_excluded & data.keys()}"
        )


# =============================================================================
# Edge Cases and Additional Tests
# =============================================================================


@pytest.mark.unit
class TestModelActionPayloadEdgeCases:
    """Tests for edge cases and additional scenarios."""

    def test_empty_execution_chain(self) -> None:
        """Test that empty execution chain is valid."""
        action = create_test_action()
        version = create_test_version()

        payload = ModelActionPayload(action=action, version=version, execution_chain=[])

        assert payload.execution_chain == []

    def test_empty_tool_discovery_tags(self) -> None:
        """Test that empty tool_discovery_tags is valid."""
        action = create_test_action()
        version = create_test_version()

        payload = ModelActionPayload(
            action=action, version=version, tool_discovery_tags=[]
        )

        assert payload.tool_discovery_tags == []

    def test_empty_string_target_service(self) -> None:
        """Test that empty string target_service is accepted."""
        action = create_test_action()
        version = create_test_version()

        payload = ModelActionPayload(action=action, version=version, target_service="")

        assert payload.target_service == ""

    def test_trust_level_precision(self) -> None:
        """Test trust_level handles float precision."""
        action = create_test_action()
        version = create_test_version()

        payload = ModelActionPayload(
            action=action, version=version, trust_level=0.123456789
        )

        assert abs(payload.trust_level - 0.123456789) < 1e-9

    def test_long_execution_chain(self) -> None:
        """Test handling of long execution chain."""
        action = create_test_action()
        version = create_test_version()

        long_chain = [f"action_{i}" for i in range(100)]
        payload = ModelActionPayload(
            action=action, version=version, execution_chain=long_chain
        )

        assert len(payload.execution_chain) == 100
        assert payload.execution_chain[99] == "action_99"

    def test_many_tool_discovery_tags(self) -> None:
        """Test handling of many tool discovery tags."""
        action = create_test_action()
        version = create_test_version()

        many_tags = [f"tag_{i}" for i in range(50)]
        payload = ModelActionPayload(
            action=action, version=version, tool_discovery_tags=many_tags
        )

        assert len(payload.tool_discovery_tags) == 50

    def test_inherited_fields_from_base(self) -> None:
        """Test that inherited fields from ModelOnexInputState are available."""
        action = create_test_action()
        version = create_test_version()
        event_id = uuid4()
        correlation_id = uuid4()

        payload = ModelActionPayload(
            action=action,
            version=version,
            event_id=event_id,
            correlation_id=correlation_id,
            node_name="test-node",
        )

        assert payload.event_id == event_id
        assert payload.correlation_id == correlation_id
        assert payload.node_name == "test-node"

    def test_equal_payloads_are_equal(self) -> None:
        """Test that payloads with same values are equal."""
        action = create_test_action()
        version = create_test_version()

        payload1 = ModelActionPayload(
            action=action,
            version=version,
            trust_level=0.5,
            target_service="same-service",
        )
        payload2 = ModelActionPayload(
            action=action,
            version=version,
            trust_level=0.5,
            target_service="same-service",
        )

        assert payload1 == payload2

    def test_different_payloads_are_not_equal(self) -> None:
        """Test that different payloads are not equal."""
        action = create_test_action()
        version = create_test_version()

        payload1 = ModelActionPayload(action=action, version=version, trust_level=0.5)
        payload2 = ModelActionPayload(action=action, version=version, trust_level=0.6)

        assert payload1 != payload2

    def test_model_copy_with_update(self) -> None:
        """Test model_copy with update for creating modified copies."""
        action = create_test_action()
        version = create_test_version()

        original = ModelActionPayload(
            action=action,
            version=version,
            trust_level=0.8,
            target_service="original",
        )

        modified = original.model_copy(
            update={"trust_level": 0.5, "target_service": "modified"}
        )

        assert modified.trust_level == 0.5
        assert modified.target_service == "modified"
        assert original.trust_level == 0.8  # Original unchanged
        assert original.target_service == "original"

    def test_uuid_fields_accept_string(self) -> None:
        """Test that UUID fields accept string format."""
        action = create_test_action()
        version = create_test_version()
        uuid_str = "550e8400-e29b-41d4-a716-446655440000"

        payload = ModelActionPayload(
            action=action,
            version=version,
            parent_correlation_id=UUID(uuid_str),
            correlation_id=UUID(uuid_str),
        )

        assert str(payload.parent_correlation_id) == uuid_str
        assert str(payload.correlation_id) == uuid_str


# =============================================================================
# Integration Tests
# =============================================================================


@pytest.mark.unit
class TestModelActionPayloadIntegration:
    """Integration tests for ModelActionPayload."""

    def test_complex_nested_structure(self) -> None:
        """Test payload with complex nested structures."""
        action = create_test_action()
        version = create_test_version()

        parameters = ModelActionParameters(
            action_name="complex",
            action_version=ModelSemVer(major=1, minor=2, patch=3),
            extensions={"nested": {"key": "value"}},
        )

        execution_context = ModelActionExecutionContext(
            environment="production",
            timeout_ms=120000,
            max_retries=5,
            debug_mode=True,
        )

        routing_metadata = ModelRoutingMetadata(
            target_region="ap-southeast-1",
            load_balance_strategy="weighted",
            weight=2.5,
            circuit_breaker_enabled=True,
        )

        service_metadata = ModelServiceDiscoveryMetadata(
            service_name="complex-service",
            service_version=ModelSemVer(major=3, minor=0, patch=1),
            capabilities=["read", "write", "delete"],
            dependencies=["dep1", "dep2"],
        )

        payload = ModelActionPayload(
            action=action,
            version=version,
            parameters=parameters,
            execution_context=execution_context,
            routing_metadata=routing_metadata,
            service_metadata=service_metadata,
            trust_level=0.95,
            execution_chain=["step1", "step2", "step3"],
            tool_discovery_tags=["production", "critical"],
        )

        # Verify all nested structures
        assert payload.parameters.action_name == "complex"
        assert payload.execution_context.max_retries == 5
        assert payload.routing_metadata.weight == 2.5
        assert payload.service_metadata.capabilities == ["read", "write", "delete"]

    def test_workflow_simulation(self) -> None:
        """Test simulating a workflow with parent-child payloads."""
        # Create root action
        root_action = create_test_action(name="workflow_root")
        version = create_test_version()

        root_payload = ModelActionPayload(
            action=root_action,
            version=version,
            correlation_id=uuid4(),
            trust_level=0.9,
        )
        root_payload.add_to_execution_chain("workflow_root")

        # Create child action - inherits parent's trust level
        child_action = create_test_action(name="workflow_step1")
        child_payload = root_payload.create_child_payload(child_action)
        child_payload.add_to_execution_chain("workflow_step1")

        # Verify child inherits parent's trust level
        assert child_payload.trust_level == 0.9

        # Create grandchild - inherits child's trust level
        grandchild_action = create_test_action(name="workflow_step2")
        grandchild_payload = child_payload.create_child_payload(grandchild_action)
        grandchild_payload.add_to_execution_chain("workflow_step2")

        # Verify chain
        assert grandchild_payload.execution_chain == [
            "workflow_root",
            "workflow_step1",
            "workflow_step2",
        ]
        # Trust level propagates through the chain
        assert grandchild_payload.trust_level == 0.9

    def test_serialization_preserves_all_nested_models(self) -> None:
        """Test that serialization preserves all nested model data."""
        action = create_test_action()
        version = create_test_version()

        original = ModelActionPayload(
            action=action,
            version=version,
            parameters=ModelActionParameters(timeout_override_ms=5000),
            execution_context=ModelActionExecutionContext(dry_run=True),
            routing_metadata=ModelRoutingMetadata(priority=10),
            service_metadata=ModelServiceDiscoveryMetadata(
                service_name="test",
                tags=["tag1"],
            ),
        )

        # Round-trip through JSON
        json_str = original.model_dump_json()
        restored = ModelActionPayload.model_validate_json(json_str)

        # Verify nested model data preserved
        assert restored.parameters.timeout_override_ms == 5000
        assert restored.execution_context.dry_run is True
        assert restored.routing_metadata.priority == 10
        assert restored.service_metadata is not None
        assert restored.service_metadata.tags == ["tag1"]


# =============================================================================
# From Attributes Tests
# =============================================================================


@pytest.mark.unit
class TestModelActionPayloadFromAttributes:
    """Tests for ModelActionPayload from_attributes=True."""

    def test_create_from_dataclass_with_attributes(self) -> None:
        """Test creating ModelActionPayload from an object with attributes."""
        action = create_test_action()
        version = create_test_version()
        attrs = ActionPayloadAttrs(
            action=action,
            version=version,
            target_service="from-attrs-service",
            trust_level=0.75,
        )
        payload = ModelActionPayload.model_validate(attrs)
        assert payload.action == action
        assert payload.version == version
        assert payload.target_service == "from-attrs-service"
        assert payload.trust_level == 0.75

    def test_create_from_object_with_all_attributes(self) -> None:
        """Test creating from object with all attributes populated."""
        action = create_test_action()
        version = create_test_version()
        parent_id = uuid4()
        parameters = ModelActionParameters(action_name="attrs_test")
        execution_context = ModelActionExecutionContext(
            environment="production", timeout_ms=60000
        )
        routing = ModelRoutingMetadata(target_region="eu-west-1")
        service_meta = ModelServiceDiscoveryMetadata(
            service_name="full-attrs-service",
            service_version=ModelSemVer(major=1, minor=0, patch=0),
        )

        attrs = ActionPayloadAttrs(
            action=action,
            version=version,
            parameters=parameters,
            execution_context=execution_context,
            parent_correlation_id=parent_id,
            execution_chain=["step1", "step2"],
            target_service="full-service",
            routing_metadata=routing,
            trust_level=0.9,
            service_metadata=service_meta,
            tool_discovery_tags=["tag1", "tag2"],
        )
        payload = ModelActionPayload.model_validate(attrs)

        assert payload.action == action
        assert payload.parameters == parameters
        assert payload.execution_context == execution_context
        assert payload.parent_correlation_id == parent_id
        assert payload.execution_chain == ["step1", "step2"]
        assert payload.routing_metadata == routing
        assert payload.service_metadata == service_meta


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
