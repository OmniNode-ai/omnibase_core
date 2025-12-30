# SPDX-FileCopyrightText: 2025 OmniNode Team
# SPDX-License-Identifier: Apache-2.0
"""
Unit tests for ModelHandlerContract.

Tests handler contract specification including:
- Basic creation and validation
- Handler ID format validation
- Version format validation
- Descriptor consistency validation
- Capability dependency handling
- Helper methods
"""

import pytest
from pydantic import ValidationError

from omnibase_core.models.contracts.model_capability_dependency import (
    ModelCapabilityDependency,
)
from omnibase_core.models.contracts.model_execution_constraints import (
    ModelExecutionConstraints,
)
from omnibase_core.models.contracts.model_handler_contract import ModelHandlerContract
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.requirements.model_requirement_set import ModelRequirementSet
from omnibase_core.models.runtime.model_handler_behavior_descriptor import (
    ModelHandlerBehaviorDescriptor,
)


@pytest.mark.unit
class TestModelHandlerContractCreation:
    """Tests for ModelHandlerContract creation."""

    def test_minimal_creation(self) -> None:
        """Test creation with only required fields."""
        contract = ModelHandlerContract(
            handler_id="node.test.handler",
            name="Test Handler",
            version="1.0.0",
            descriptor=ModelHandlerBehaviorDescriptor(handler_kind="compute"),
            input_model="myapp.models.Input",
            output_model="myapp.models.Output",
        )
        assert contract.handler_id == "node.test.handler"
        assert contract.name == "Test Handler"
        assert contract.version == "1.0.0"
        assert contract.descriptor.handler_kind == "compute"

    def test_full_creation(self) -> None:
        """Test creation with all fields."""
        contract = ModelHandlerContract(
            handler_id="reducer.user.registration",
            name="User Registration Reducer",
            version="2.1.0-beta.1",
            description="Handles user registration lifecycle",
            descriptor=ModelHandlerBehaviorDescriptor(
                handler_kind="reducer",
                purity="side_effecting",
                idempotent=True,
                timeout_ms=30000,
            ),
            capability_inputs=[
                ModelCapabilityDependency(
                    alias="db",
                    capability="database.relational",
                    requirements=ModelRequirementSet(
                        must={"supports_transactions": True},
                    ),
                ),
            ],
            capability_outputs=["user.created", "user.registered"],
            input_model="myapp.models.RegistrationEvent",
            output_model="myapp.models.UserState",
            execution_constraints=ModelExecutionConstraints(
                requires_before=["capability:auth"],
                requires_after=["capability:logging"],
            ),
            supports_lifecycle=True,
            supports_health_check=True,
            supports_provisioning=False,
            tags=["registration", "user"],
            metadata={"owner": "user-team"},
        )
        assert contract.handler_id == "reducer.user.registration"
        assert contract.descriptor.handler_kind == "reducer"
        assert len(contract.capability_inputs) == 1
        assert contract.capability_inputs[0].alias == "db"
        assert contract.supports_lifecycle is True


@pytest.mark.unit
class TestHandlerIdValidation:
    """Tests for handler_id format validation."""

    def test_valid_two_segment_id(self) -> None:
        """Test valid two-segment handler ID."""
        contract = ModelHandlerContract(
            handler_id="node.handler",
            name="Test",
            version="1.0.0",
            descriptor=ModelHandlerBehaviorDescriptor(handler_kind="compute"),
            input_model="a.Input",
            output_model="a.Output",
        )
        assert contract.handler_id == "node.handler"

    def test_valid_multi_segment_id(self) -> None:
        """Test valid multi-segment handler ID."""
        contract = ModelHandlerContract(
            handler_id="effect.database.user.repository",
            name="Test",
            version="1.0.0",
            descriptor=ModelHandlerBehaviorDescriptor(handler_kind="effect"),
            input_model="a.Input",
            output_model="a.Output",
        )
        assert contract.handler_id == "effect.database.user.repository"

    def test_single_segment_id_rejected(self) -> None:
        """Test that single segment handler ID is rejected."""
        with pytest.raises(ValidationError, match="at least 2 segments"):
            ModelHandlerContract(
                handler_id="handler",
                name="Test",
                version="1.0.0",
                descriptor=ModelHandlerBehaviorDescriptor(handler_kind="compute"),
                input_model="a.Input",
                output_model="a.Output",
            )

    def test_empty_segment_id_rejected(self) -> None:
        """Test that handler ID with empty segment is rejected."""
        with pytest.raises(ValidationError, match="empty segment"):
            ModelHandlerContract(
                handler_id="node..handler",
                name="Test",
                version="1.0.0",
                descriptor=ModelHandlerBehaviorDescriptor(handler_kind="compute"),
                input_model="a.Input",
                output_model="a.Output",
            )

    def test_underscore_prefix_allowed(self) -> None:
        """Test that underscore prefix is allowed in segments."""
        contract = ModelHandlerContract(
            handler_id="node._internal.handler",
            name="Test",
            version="1.0.0",
            descriptor=ModelHandlerBehaviorDescriptor(handler_kind="compute"),
            input_model="a.Input",
            output_model="a.Output",
        )
        assert contract.handler_id == "node._internal.handler"


@pytest.mark.unit
class TestVersionValidation:
    """Tests for semantic version format validation."""

    @pytest.mark.parametrize(
        "version",
        [
            "1.0.0",
            "0.0.1",
            "10.20.30",
            "1.0.0-alpha",
            "1.0.0-beta.1",
            "1.0.0-rc.1",
            "1.0.0+build.123",
            "1.0.0-beta.1+build.456",
        ],
    )
    def test_valid_versions(self, version: str) -> None:
        """Test various valid semantic version formats."""
        contract = ModelHandlerContract(
            handler_id="node.test",
            name="Test",
            version=version,
            descriptor=ModelHandlerBehaviorDescriptor(handler_kind="compute"),
            input_model="a.Input",
            output_model="a.Output",
        )
        assert contract.version == version

    @pytest.mark.parametrize(
        "version",
        [
            "1.0",
            "1",
            "v1.0.0",
            "1.0.0.0",
            "latest",
            "1.0.0-",
        ],
    )
    def test_invalid_versions_rejected(self, version: str) -> None:
        """Test various invalid version formats are rejected."""
        with pytest.raises(ValidationError):
            ModelHandlerContract(
                handler_id="node.test",
                name="Test",
                version=version,
                descriptor=ModelHandlerBehaviorDescriptor(handler_kind="compute"),
                input_model="a.Input",
                output_model="a.Output",
            )


@pytest.mark.unit
class TestDescriptorConsistencyValidation:
    """Tests for handler_id prefix vs descriptor.handler_kind consistency."""

    def test_compute_prefix_matches_compute_kind(self) -> None:
        """Test compute prefix accepts compute handler_kind."""
        contract = ModelHandlerContract(
            handler_id="compute.data.transformer",
            name="Test",
            version="1.0.0",
            descriptor=ModelHandlerBehaviorDescriptor(handler_kind="compute"),
            input_model="a.Input",
            output_model="a.Output",
        )
        assert contract.descriptor.handler_kind == "compute"

    def test_effect_prefix_matches_effect_kind(self) -> None:
        """Test effect prefix accepts effect handler_kind."""
        contract = ModelHandlerContract(
            handler_id="effect.database.writer",
            name="Test",
            version="1.0.0",
            descriptor=ModelHandlerBehaviorDescriptor(handler_kind="effect"),
            input_model="a.Input",
            output_model="a.Output",
        )
        assert contract.descriptor.handler_kind == "effect"

    def test_reducer_prefix_matches_reducer_kind(self) -> None:
        """Test reducer prefix accepts reducer handler_kind."""
        contract = ModelHandlerContract(
            handler_id="reducer.user.state",
            name="Test",
            version="1.0.0",
            descriptor=ModelHandlerBehaviorDescriptor(handler_kind="reducer"),
            input_model="a.Input",
            output_model="a.Output",
        )
        assert contract.descriptor.handler_kind == "reducer"

    def test_generic_node_prefix_accepts_any_kind(self) -> None:
        """Test 'node' prefix accepts any handler_kind."""
        for kind in ["compute", "effect", "reducer", "orchestrator"]:
            contract = ModelHandlerContract(
                handler_id="node.test.handler",
                name="Test",
                version="1.0.0",
                descriptor=ModelHandlerBehaviorDescriptor(handler_kind=kind),  # type: ignore[arg-type]
                input_model="a.Input",
                output_model="a.Output",
            )
            assert contract.descriptor.handler_kind == kind

    def test_generic_handler_prefix_accepts_any_kind(self) -> None:
        """Test 'handler' prefix accepts any handler_kind."""
        for kind in ["compute", "effect", "reducer", "orchestrator"]:
            contract = ModelHandlerContract(
                handler_id="handler.test.impl",
                name="Test",
                version="1.0.0",
                descriptor=ModelHandlerBehaviorDescriptor(handler_kind=kind),  # type: ignore[arg-type]
                input_model="a.Input",
                output_model="a.Output",
            )
            assert contract.descriptor.handler_kind == kind

    def test_compute_prefix_rejects_effect_kind(self) -> None:
        """Test compute prefix rejects effect handler_kind."""
        with pytest.raises(ModelOnexError, match="implies handler_kind='compute'"):
            ModelHandlerContract(
                handler_id="compute.data.transformer",
                name="Test",
                version="1.0.0",
                descriptor=ModelHandlerBehaviorDescriptor(handler_kind="effect"),
                input_model="a.Input",
                output_model="a.Output",
            )


@pytest.mark.unit
class TestCapabilityDependencyHandling:
    """Tests for capability dependency handling."""

    def test_unique_aliases_required(self) -> None:
        """Test that capability input aliases must be unique."""
        with pytest.raises(ValidationError, match="Duplicate capability input aliases"):
            ModelHandlerContract(
                handler_id="node.test",
                name="Test",
                version="1.0.0",
                descriptor=ModelHandlerBehaviorDescriptor(handler_kind="effect"),
                capability_inputs=[
                    ModelCapabilityDependency(alias="db", capability="database"),
                    ModelCapabilityDependency(alias="db", capability="cache"),
                ],
                input_model="a.Input",
                output_model="a.Output",
            )

    def test_get_capability_aliases(self) -> None:
        """Test get_capability_aliases helper method."""
        contract = ModelHandlerContract(
            handler_id="node.test",
            name="Test",
            version="1.0.0",
            descriptor=ModelHandlerBehaviorDescriptor(handler_kind="effect"),
            capability_inputs=[
                ModelCapabilityDependency(alias="db", capability="database"),
                ModelCapabilityDependency(alias="cache", capability="cache"),
            ],
            input_model="a.Input",
            output_model="a.Output",
        )
        aliases = contract.get_capability_aliases()
        assert aliases == ["db", "cache"]

    def test_get_required_capabilities(self) -> None:
        """Test get_required_capabilities helper method."""
        contract = ModelHandlerContract(
            handler_id="node.test",
            name="Test",
            version="1.0.0",
            descriptor=ModelHandlerBehaviorDescriptor(handler_kind="effect"),
            capability_inputs=[
                ModelCapabilityDependency(
                    alias="db", capability="database", strict=True
                ),
                ModelCapabilityDependency(
                    alias="cache", capability="cache", strict=False
                ),
            ],
            input_model="a.Input",
            output_model="a.Output",
        )
        required = contract.get_required_capabilities()
        assert required == ["database"]

    def test_get_optional_capabilities(self) -> None:
        """Test get_optional_capabilities helper method."""
        contract = ModelHandlerContract(
            handler_id="node.test",
            name="Test",
            version="1.0.0",
            descriptor=ModelHandlerBehaviorDescriptor(handler_kind="effect"),
            capability_inputs=[
                ModelCapabilityDependency(
                    alias="db", capability="database", strict=True
                ),
                ModelCapabilityDependency(
                    alias="cache", capability="cache", strict=False
                ),
            ],
            input_model="a.Input",
            output_model="a.Output",
        )
        optional = contract.get_optional_capabilities()
        assert optional == ["cache"]


@pytest.mark.unit
class TestExecutionConstraintsHelpers:
    """Tests for execution constraints helper methods."""

    def test_has_execution_constraints_none(self) -> None:
        """Test has_execution_constraints with no constraints."""
        contract = ModelHandlerContract(
            handler_id="node.test",
            name="Test",
            version="1.0.0",
            descriptor=ModelHandlerBehaviorDescriptor(handler_kind="compute"),
            input_model="a.Input",
            output_model="a.Output",
        )
        assert contract.has_execution_constraints() is False

    def test_has_execution_constraints_empty(self) -> None:
        """Test has_execution_constraints with empty constraints."""
        contract = ModelHandlerContract(
            handler_id="node.test",
            name="Test",
            version="1.0.0",
            descriptor=ModelHandlerBehaviorDescriptor(handler_kind="compute"),
            execution_constraints=ModelExecutionConstraints(),
            input_model="a.Input",
            output_model="a.Output",
        )
        assert contract.has_execution_constraints() is False

    def test_has_execution_constraints_with_ordering(self) -> None:
        """Test has_execution_constraints with ordering constraints."""
        contract = ModelHandlerContract(
            handler_id="node.test",
            name="Test",
            version="1.0.0",
            descriptor=ModelHandlerBehaviorDescriptor(handler_kind="compute"),
            execution_constraints=ModelExecutionConstraints(
                requires_before=["capability:auth"],
            ),
            input_model="a.Input",
            output_model="a.Output",
        )
        assert contract.has_execution_constraints() is True


@pytest.mark.unit
class TestImmutability:
    """Tests for model immutability."""

    def test_model_is_frozen(self) -> None:
        """Test that model instances are immutable."""
        contract = ModelHandlerContract(
            handler_id="node.test",
            name="Test",
            version="1.0.0",
            descriptor=ModelHandlerBehaviorDescriptor(handler_kind="compute"),
            input_model="a.Input",
            output_model="a.Output",
        )
        with pytest.raises(ValidationError):
            contract.name = "New Name"  # type: ignore[misc]

    def test_extra_fields_forbidden(self) -> None:
        """Test that extra fields are not allowed."""
        with pytest.raises(ValidationError):
            ModelHandlerContract(
                handler_id="node.test",
                name="Test",
                version="1.0.0",
                descriptor=ModelHandlerBehaviorDescriptor(handler_kind="compute"),
                input_model="a.Input",
                output_model="a.Output",
                unknown_field="value",  # type: ignore[call-arg]
            )
