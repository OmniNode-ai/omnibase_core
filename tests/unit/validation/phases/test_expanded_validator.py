# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for ExpandedContractValidator (Phase 3 Contract Validation).

Tests all validation checks performed by ExpandedContractValidator including:
- Handler ID format validation
- Model reference validation
- Version format validation
- Execution graph cycle detection (self-reference)
- Event routing validation
- Capability input format validation
- Handler kind consistency
- Valid contract passes validation

Related:
    - OMN-1128: Contract Validation Pipeline
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_contract_validation_error_code import (
    EnumContractValidationErrorCode,
)
from omnibase_core.models.common.model_validation_result import ModelValidationResult
from omnibase_core.models.contracts.model_contract_capability_dependency import (
    ModelCapabilityDependency,
)
from omnibase_core.models.contracts.model_execution_constraints import (
    ModelExecutionConstraints,
)
from omnibase_core.models.contracts.model_handler_contract import ModelHandlerContract
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.models.runtime.model_handler_behavior import ModelHandlerBehavior
from omnibase_core.validation.phases import (
    ExpandedContractGraphValidator,
    ExpandedContractValidator,
)


@pytest.mark.unit
class TestExpandedContractValidatorFixtures:
    """Test fixtures for ExpandedContractValidator tests."""

    @pytest.fixture
    def validator(self) -> ExpandedContractValidator:
        """Create a validator fixture."""
        return ExpandedContractValidator()

    @pytest.fixture
    def graph_validator(self) -> ExpandedContractGraphValidator:
        """Create a graph validator fixture."""
        return ExpandedContractGraphValidator()

    @pytest.fixture
    def valid_descriptor(self) -> ModelHandlerBehavior:
        """Create a valid handler behavior descriptor."""
        return ModelHandlerBehavior(
            node_archetype="compute",
            purity="pure",
            idempotent=True,
        )

    @pytest.fixture
    def valid_contract(
        self, valid_descriptor: ModelHandlerBehavior
    ) -> ModelHandlerContract:
        """Create a valid contract fixture."""
        return ModelHandlerContract(
            handler_id="node.test.compute",
            name="Test Compute Node",
            contract_version=ModelSemVer(major=1, minor=0, patch=0),
            description="A test compute node",
            descriptor=valid_descriptor,
            input_model="omnibase_core.models.events.ModelTestEvent",
            output_model="omnibase_core.models.results.ModelTestResult",
        )


@pytest.mark.unit
class TestExpandedContractValidatorBasic(TestExpandedContractValidatorFixtures):
    """Basic tests for ExpandedContractValidator."""

    def test_valid_contract_passes(
        self,
        validator: ExpandedContractValidator,
        valid_contract: ModelHandlerContract,
    ) -> None:
        """Test that a valid contract passes validation."""
        result = validator.validate(valid_contract)
        assert result.is_valid is True
        assert result.error_level_count == 0

    def test_validator_returns_validation_result(
        self,
        validator: ExpandedContractValidator,
        valid_contract: ModelHandlerContract,
    ) -> None:
        """Test that validator returns ModelValidationResult."""
        result = validator.validate(valid_contract)
        assert isinstance(result, ModelValidationResult)

    def test_validator_is_stateless(
        self,
        validator: ExpandedContractValidator,
        valid_contract: ModelHandlerContract,
    ) -> None:
        """Test that validator is stateless and can be reused."""
        result1 = validator.validate(valid_contract)
        result2 = validator.validate(valid_contract)

        # Both should pass and be independent
        assert result1.is_valid is True
        assert result2.is_valid is True


@pytest.mark.unit
class TestExpandedContractValidatorHandlerIdFormat(
    TestExpandedContractValidatorFixtures
):
    """Tests for handler_id format validation."""

    def test_valid_handler_id_passes(
        self,
        validator: ExpandedContractValidator,
        valid_descriptor: ModelHandlerBehavior,
    ) -> None:
        """Test valid handler_id formats pass validation."""
        valid_ids = [
            "node.test.compute",
            "handler.email.sender",
            "_internal.service.worker",
            "node.user_registration.reducer",
        ]

        for handler_id in valid_ids:
            contract = ModelHandlerContract(
                handler_id=handler_id,
                name="Test Handler",
                contract_version=ModelSemVer(major=1, minor=0, patch=0),
                descriptor=valid_descriptor,
                input_model="omnibase_core.models.test.Input",
                output_model="omnibase_core.models.test.Output",
            )
            result = validator.validate(contract)
            assert result.is_valid is True, f"Handler ID '{handler_id}' should be valid"

    def test_single_segment_handler_id_fails(
        self,
        validator: ExpandedContractValidator,
        valid_descriptor: ModelHandlerBehavior,
    ) -> None:
        """Test that single-segment handler_id fails validation at model level."""
        # ModelHandlerContract validates this, so we expect a Pydantic error
        with pytest.raises(ValueError):
            ModelHandlerContract(
                handler_id="single",  # Should have at least 2 segments
                name="Test Handler",
                contract_version=ModelSemVer(major=1, minor=0, patch=0),
                descriptor=valid_descriptor,
                input_model="omnibase_core.models.test.Input",
                output_model="omnibase_core.models.test.Output",
            )


@pytest.mark.unit
class TestExpandedContractValidatorModelReference(
    TestExpandedContractValidatorFixtures
):
    """Tests for model reference validation."""

    def test_valid_model_reference_passes(
        self,
        validator: ExpandedContractValidator,
        valid_contract: ModelHandlerContract,
    ) -> None:
        """Test that valid model references pass validation."""
        result = validator.validate(valid_contract)
        assert result.is_valid is True

    def test_empty_input_model_fails(
        self,
        validator: ExpandedContractValidator,
        valid_descriptor: ModelHandlerBehavior,
    ) -> None:
        """Test that empty input_model fails validation."""
        # Empty input_model will fail at Pydantic validation level (min_length=1)
        with pytest.raises(ValueError):
            ModelHandlerContract(
                handler_id="node.test.compute",
                name="Test Handler",
                contract_version=ModelSemVer(major=1, minor=0, patch=0),
                descriptor=valid_descriptor,
                input_model="",  # Empty
                output_model="omnibase_core.models.test.Output",
            )

    def test_invalid_model_reference_format_fails(
        self,
        validator: ExpandedContractValidator,
        valid_descriptor: ModelHandlerBehavior,
    ) -> None:
        """Test that invalid model reference format fails validation."""
        contract = ModelHandlerContract(
            handler_id="node.test.compute",
            name="Test Handler",
            contract_version=ModelSemVer(major=1, minor=0, patch=0),
            descriptor=valid_descriptor,
            input_model="InvalidSingleWord",  # Not dot-separated module path
            output_model="omnibase_core.models.test.Output",
        )
        result = validator.validate(contract)
        assert result.is_valid is False
        assert any(
            EnumContractValidationErrorCode.CONTRACT_VALIDATION_EXPANDED_MODEL_REFERENCE_INVALID.value
            in str(issue.code)
            for issue in result.issues
        )


@pytest.mark.unit
class TestExpandedContractValidatorVersionFormat(TestExpandedContractValidatorFixtures):
    """Tests for contract_version validation (ModelSemVer).

    Note: As of OMN-1436, handler contracts use contract_version: ModelSemVer
    instead of version: str. These tests validate the new structured version format.
    """

    def test_valid_semver_passes(
        self,
        validator: ExpandedContractValidator,
        valid_descriptor: ModelHandlerBehavior,
    ) -> None:
        """Test that valid ModelSemVer versions pass validation."""
        valid_versions = [
            ModelSemVer(major=1, minor=0, patch=0),
            ModelSemVer(major=2, minor=1, patch=3),
            ModelSemVer(major=0, minor=0, patch=1),
            ModelSemVer(major=1, minor=0, patch=0, prerelease=("beta", 1)),
            ModelSemVer(major=1, minor=0, patch=0, build=("build", "123")),
            ModelSemVer(
                major=1,
                minor=0,
                patch=0,
                prerelease=("alpha", 1),
                build=("build", "456"),
            ),
        ]

        for version in valid_versions:
            contract = ModelHandlerContract(
                handler_id="node.test.compute",
                name="Test Handler",
                contract_version=version,
                descriptor=valid_descriptor,
                input_model="omnibase_core.models.test.Input",
                output_model="omnibase_core.models.test.Output",
            )
            result = validator.validate(contract)
            assert result.is_valid is True, f"Version '{version}' should be valid"

    def test_deprecated_version_field_rejected(
        self,
        validator: ExpandedContractValidator,
        valid_descriptor: ModelHandlerBehavior,
    ) -> None:
        """Test that deprecated 'version' field is rejected.

        As of OMN-1436, handler contracts must use 'contract_version' (ModelSemVer),
        not the deprecated 'version' (str) field.
        """
        with pytest.raises(ModelOnexError, match="contract_version"):
            ModelHandlerContract(
                handler_id="node.test.compute",
                name="Test Handler",
                version="1.0.0",  # type: ignore[call-arg]  # Deprecated field - should be rejected
                descriptor=valid_descriptor,
                input_model="omnibase_core.models.test.Input",
                output_model="omnibase_core.models.test.Output",
            )


@pytest.mark.unit
class TestExpandedContractValidatorExecutionGraph(
    TestExpandedContractValidatorFixtures
):
    """Tests for execution graph validation."""

    def test_self_reference_cycle_detected(
        self,
        validator: ExpandedContractValidator,
        valid_descriptor: ModelHandlerBehavior,
    ) -> None:
        """Test that self-reference in execution constraints is detected."""
        contract = ModelHandlerContract(
            handler_id="node.test.compute",
            name="Test Handler",
            contract_version=ModelSemVer(major=1, minor=0, patch=0),
            descriptor=valid_descriptor,
            input_model="omnibase_core.models.test.Input",
            output_model="omnibase_core.models.test.Output",
            execution_constraints=ModelExecutionConstraints(
                requires_before=["handler:node.test.compute"],  # Self-reference
            ),
        )

        result = validator.validate(contract)
        assert result.is_valid is False
        assert any(
            EnumContractValidationErrorCode.CONTRACT_VALIDATION_EXPANDED_EXECUTION_GRAPH_CYCLE.value
            in str(issue.code)
            for issue in result.issues
        )

    def test_valid_execution_constraints_pass(
        self,
        validator: ExpandedContractValidator,
        valid_descriptor: ModelHandlerBehavior,
    ) -> None:
        """Test that valid execution constraints pass validation."""
        contract = ModelHandlerContract(
            handler_id="node.test.compute",
            name="Test Handler",
            contract_version=ModelSemVer(major=1, minor=0, patch=0),
            descriptor=valid_descriptor,
            input_model="omnibase_core.models.test.Input",
            output_model="omnibase_core.models.test.Output",
            execution_constraints=ModelExecutionConstraints(
                requires_before=["handler:node.other.compute"],
                requires_after=["capability:logging"],
            ),
        )

        result = validator.validate(contract)
        assert result.is_valid is True

    def test_empty_execution_constraints_pass(
        self,
        validator: ExpandedContractValidator,
        valid_contract: ModelHandlerContract,
    ) -> None:
        """Test that no execution constraints passes validation."""
        result = validator.validate(valid_contract)
        assert result.is_valid is True

    def test_invalid_dependency_reference_format(
        self,
        validator: ExpandedContractValidator,
        valid_descriptor: ModelHandlerBehavior,
    ) -> None:
        """Test that invalid dependency reference format is detected."""
        # ModelExecutionConstraints validates prefix format
        with pytest.raises(ValueError):
            ModelHandlerContract(
                handler_id="node.test.compute",
                name="Test Handler",
                contract_version=ModelSemVer(major=1, minor=0, patch=0),
                descriptor=valid_descriptor,
                input_model="omnibase_core.models.test.Input",
                output_model="omnibase_core.models.test.Output",
                execution_constraints=ModelExecutionConstraints(
                    requires_before=["invalid_no_prefix"],  # Missing prefix
                ),
            )


@pytest.mark.unit
class TestExpandedContractValidatorEventRouting(TestExpandedContractValidatorFixtures):
    """Tests for event routing validation."""

    def test_valid_capability_output_format(
        self,
        validator: ExpandedContractValidator,
        valid_descriptor: ModelHandlerBehavior,
    ) -> None:
        """Test that valid capability output formats pass validation."""
        contract = ModelHandlerContract(
            handler_id="node.test.compute",
            name="Test Handler",
            contract_version=ModelSemVer(major=1, minor=0, patch=0),
            descriptor=valid_descriptor,
            input_model="omnibase_core.models.test.Input",
            output_model="omnibase_core.models.test.Output",
            capability_outputs=[
                "event.user_created",
                "notification.email",
                "log.audit",
            ],
        )

        result = validator.validate(contract)
        assert result.is_valid is True

    def test_invalid_capability_output_format_fails(
        self,
        validator: ExpandedContractValidator,
        valid_descriptor: ModelHandlerBehavior,
    ) -> None:
        """Test that invalid capability output format fails validation."""
        contract = ModelHandlerContract(
            handler_id="node.test.compute",
            name="Test Handler",
            contract_version=ModelSemVer(major=1, minor=0, patch=0),
            descriptor=valid_descriptor,
            input_model="omnibase_core.models.test.Input",
            output_model="omnibase_core.models.test.Output",
            capability_outputs=[
                "123invalid",  # Starts with number
            ],
        )

        result = validator.validate(contract)
        assert result.is_valid is False
        assert any(
            EnumContractValidationErrorCode.CONTRACT_VALIDATION_EXPANDED_EVENT_ROUTING_INVALID.value
            in str(issue.code)
            for issue in result.issues
        )

    def test_event_output_info_message(
        self,
        validator: ExpandedContractValidator,
        valid_descriptor: ModelHandlerBehavior,
    ) -> None:
        """Test that event outputs produce info in suggestions about consumers."""
        contract = ModelHandlerContract(
            handler_id="node.test.compute",
            name="Test Handler",
            contract_version=ModelSemVer(major=1, minor=0, patch=0),
            descriptor=valid_descriptor,
            input_model="omnibase_core.models.test.Input",
            output_model="omnibase_core.models.test.Output",
            capability_outputs=[
                "event.user_created",
                "event.order_completed",
            ],
        )

        result = validator.validate(contract)
        assert result.is_valid is True
        # Should produce suggestions about verifying consumers for event outputs
        # Note: Event outputs without known consumers produce INFO-level suggestions
        assert result.suggestions or result.warning_count > 0, (
            "Expected suggestions or warnings about event consumers"
        )


@pytest.mark.unit
class TestExpandedContractValidatorCapabilityInputs(
    TestExpandedContractValidatorFixtures
):
    """Tests for capability input validation."""

    def test_valid_capability_input_format(
        self,
        validator: ExpandedContractValidator,
        valid_descriptor: ModelHandlerBehavior,
    ) -> None:
        """Test that valid capability input formats pass validation."""
        contract = ModelHandlerContract(
            handler_id="node.test.compute",
            name="Test Handler",
            contract_version=ModelSemVer(major=1, minor=0, patch=0),
            descriptor=valid_descriptor,
            input_model="omnibase_core.models.test.Input",
            output_model="omnibase_core.models.test.Output",
            capability_inputs=[
                ModelCapabilityDependency(
                    alias="db",
                    capability="database.relational",
                ),
                ModelCapabilityDependency(
                    alias="cache",
                    capability="cache.distributed",
                ),
            ],
        )

        result = validator.validate(contract)
        assert result.is_valid is True

    def test_invalid_capability_format_fails(
        self,
        validator: ExpandedContractValidator,
        valid_descriptor: ModelHandlerBehavior,
    ) -> None:
        """Test that invalid capability format fails validation."""
        # ModelCapabilityDependency validates capability format, so we test
        # invalid formats that might pass model validation but fail expanded validation
        with pytest.raises(ValueError):
            ModelHandlerContract(
                handler_id="node.test.compute",
                name="Test Handler",
                contract_version=ModelSemVer(major=1, minor=0, patch=0),
                descriptor=valid_descriptor,
                input_model="omnibase_core.models.test.Input",
                output_model="omnibase_core.models.test.Output",
                capability_inputs=[
                    ModelCapabilityDependency(
                        alias="db",
                        capability="123invalid",  # Invalid format
                    ),
                ],
            )


@pytest.mark.unit
class TestExpandedContractValidatorHandlerKindConsistency(
    TestExpandedContractValidatorFixtures
):
    """Tests for handler kind consistency validation."""

    def test_compute_prefix_compute_kind_passes(
        self,
        validator: ExpandedContractValidator,
    ) -> None:
        """Test that compute prefix with compute kind passes."""
        descriptor = ModelHandlerBehavior(
            node_archetype="compute",
            purity="pure",
            idempotent=True,
        )
        contract = ModelHandlerContract(
            handler_id="compute.test.handler",
            name="Test Handler",
            contract_version=ModelSemVer(major=1, minor=0, patch=0),
            descriptor=descriptor,
            input_model="omnibase_core.models.test.Input",
            output_model="omnibase_core.models.test.Output",
        )

        result = validator.validate(contract)
        assert result.is_valid is True

    def test_effect_prefix_effect_kind_passes(
        self,
        validator: ExpandedContractValidator,
    ) -> None:
        """Test that effect prefix with effect kind passes."""
        descriptor = ModelHandlerBehavior(
            node_archetype="effect",
            purity="side_effecting",
            idempotent=False,
        )
        contract = ModelHandlerContract(
            handler_id="effect.email.sender",
            name="Email Sender",
            contract_version=ModelSemVer(major=1, minor=0, patch=0),
            descriptor=descriptor,
            input_model="omnibase_core.models.test.Input",
            output_model="omnibase_core.models.test.Output",
        )

        result = validator.validate(contract)
        assert result.is_valid is True

    def test_generic_prefix_any_kind_passes(
        self,
        validator: ExpandedContractValidator,
        valid_descriptor: ModelHandlerBehavior,
    ) -> None:
        """Test that generic prefixes allow any handler kind."""
        generic_prefixes = ["node", "handler"]

        for prefix in generic_prefixes:
            contract = ModelHandlerContract(
                handler_id=f"{prefix}.test.handler",
                name="Test Handler",
                contract_version=ModelSemVer(major=1, minor=0, patch=0),
                descriptor=valid_descriptor,
                input_model="omnibase_core.models.test.Input",
                output_model="omnibase_core.models.test.Output",
            )
            result = validator.validate(contract)
            assert result.is_valid is True, f"Prefix '{prefix}' should allow any kind"

    def test_compute_prefix_effect_kind_fails(
        self,
        validator: ExpandedContractValidator,
    ) -> None:
        """Test that compute prefix with effect kind fails at model level."""
        # ModelHandlerContract validates this consistency
        descriptor = ModelHandlerBehavior(
            node_archetype="effect",
            purity="side_effecting",
        )
        with pytest.raises((ModelOnexError, ValidationError, ValueError)):
            ModelHandlerContract(
                handler_id="compute.test.handler",  # compute prefix
                name="Test Handler",
                contract_version=ModelSemVer(major=1, minor=0, patch=0),
                descriptor=descriptor,  # but effect kind
                input_model="omnibase_core.models.test.Input",
                output_model="omnibase_core.models.test.Output",
            )


@pytest.mark.unit
class TestExpandedContractGraphValidator(TestExpandedContractValidatorFixtures):
    """Tests for multi-contract graph validation."""

    def test_empty_contract_list(
        self,
        graph_validator: ExpandedContractGraphValidator,
    ) -> None:
        """Test validation with empty contract list."""
        result = graph_validator.validate_graph([])
        assert result.is_valid is True
        assert "No contracts" in result.summary

    def test_single_contract_graph(
        self,
        graph_validator: ExpandedContractGraphValidator,
        valid_contract: ModelHandlerContract,
    ) -> None:
        """Test validation with single contract."""
        result = graph_validator.validate_graph([valid_contract])
        assert result.is_valid is True

    def test_orphan_handler_reference_detected(
        self,
        graph_validator: ExpandedContractGraphValidator,
        valid_descriptor: ModelHandlerBehavior,
    ) -> None:
        """Test that orphan handler references are detected."""
        contract = ModelHandlerContract(
            handler_id="node.test.compute",
            name="Test Handler",
            contract_version=ModelSemVer(major=1, minor=0, patch=0),
            descriptor=valid_descriptor,
            input_model="omnibase_core.models.test.Input",
            output_model="omnibase_core.models.test.Output",
            execution_constraints=ModelExecutionConstraints(
                requires_before=["handler:nonexistent.handler"],  # Orphan reference
            ),
        )

        result = graph_validator.validate_graph([contract])
        assert result.is_valid is False
        assert any(
            EnumContractValidationErrorCode.CONTRACT_VALIDATION_EXPANDED_EXECUTION_GRAPH_ORPHAN.value
            in str(issue.code)
            for issue in result.issues
        )

    def test_circular_dependency_detected(
        self,
        graph_validator: ExpandedContractGraphValidator,
        valid_descriptor: ModelHandlerBehavior,
    ) -> None:
        """Test that circular dependencies are detected."""
        # Contract A requires B before
        contract_a = ModelHandlerContract(
            handler_id="node.a.compute",
            name="Handler A",
            contract_version=ModelSemVer(major=1, minor=0, patch=0),
            descriptor=valid_descriptor,
            input_model="omnibase_core.models.test.Input",
            output_model="omnibase_core.models.test.Output",
            execution_constraints=ModelExecutionConstraints(
                requires_before=["handler:node.b.compute"],
            ),
        )

        # Contract B requires A before (creates cycle)
        contract_b = ModelHandlerContract(
            handler_id="node.b.compute",
            name="Handler B",
            contract_version=ModelSemVer(major=1, minor=0, patch=0),
            descriptor=valid_descriptor,
            input_model="omnibase_core.models.test.Input",
            output_model="omnibase_core.models.test.Output",
            execution_constraints=ModelExecutionConstraints(
                requires_before=["handler:node.a.compute"],
            ),
        )

        result = graph_validator.validate_graph([contract_a, contract_b])
        assert result.is_valid is False
        assert any(
            EnumContractValidationErrorCode.CONTRACT_VALIDATION_EXPANDED_EXECUTION_GRAPH_CYCLE.value
            in str(issue.code)
            for issue in result.issues
        )

    def test_valid_dependency_chain(
        self,
        graph_validator: ExpandedContractGraphValidator,
        valid_descriptor: ModelHandlerBehavior,
    ) -> None:
        """Test that valid dependency chain passes."""
        # A -> B -> C (no cycle)
        contract_a = ModelHandlerContract(
            handler_id="node.a.compute",
            name="Handler A",
            contract_version=ModelSemVer(major=1, minor=0, patch=0),
            descriptor=valid_descriptor,
            input_model="omnibase_core.models.test.Input",
            output_model="omnibase_core.models.test.Output",
        )

        contract_b = ModelHandlerContract(
            handler_id="node.b.compute",
            name="Handler B",
            contract_version=ModelSemVer(major=1, minor=0, patch=0),
            descriptor=valid_descriptor,
            input_model="omnibase_core.models.test.Input",
            output_model="omnibase_core.models.test.Output",
            execution_constraints=ModelExecutionConstraints(
                requires_before=["handler:node.a.compute"],
            ),
        )

        contract_c = ModelHandlerContract(
            handler_id="node.c.compute",
            name="Handler C",
            contract_version=ModelSemVer(major=1, minor=0, patch=0),
            descriptor=valid_descriptor,
            input_model="omnibase_core.models.test.Input",
            output_model="omnibase_core.models.test.Output",
            execution_constraints=ModelExecutionConstraints(
                requires_before=["handler:node.b.compute"],
            ),
        )

        result = graph_validator.validate_graph([contract_a, contract_b, contract_c])
        assert result.is_valid is True

    def test_unmatched_event_warning(
        self,
        graph_validator: ExpandedContractGraphValidator,
        valid_descriptor: ModelHandlerBehavior,
    ) -> None:
        """Test that unmatched events produce warning."""
        # Producer produces event but no consumer
        producer = ModelHandlerContract(
            handler_id="node.producer.compute",
            name="Event Producer",
            contract_version=ModelSemVer(major=1, minor=0, patch=0),
            descriptor=valid_descriptor,
            input_model="omnibase_core.models.test.Input",
            output_model="omnibase_core.models.test.Output",
            capability_outputs=["event.orphan_event"],
        )

        result = graph_validator.validate_graph([producer])
        # Should have warning about no consumer
        assert result.warning_count > 0
        assert any(
            "event.orphan_event" in str(issue.message) for issue in result.issues
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
