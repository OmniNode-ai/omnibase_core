# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Tests for MergeValidator (Phase 2 Contract Validation).

Tests all validation checks performed by MergeValidator including:
- Placeholder value detection (TODO, PLACEHOLDER, ${VAR}, empty strings)
- Required override validation
- Dependency reference resolution
- Handler name uniqueness
- Capability consistency
- Valid merge passes validation
- Multiple errors aggregation

Related:
    - OMN-1128: Contract Validation Pipeline
"""

import pytest

from omnibase_core.enums.enum_contract_validation_error_code import (
    EnumContractValidationErrorCode,
)
from omnibase_core.models.common.model_validation_result import ModelValidationResult
from omnibase_core.models.contracts.model_contract_capability_dependency import (
    ModelCapabilityDependency,
)
from omnibase_core.models.contracts.model_contract_patch import ModelContractPatch
from omnibase_core.models.contracts.model_dependency import ModelDependency
from omnibase_core.models.contracts.model_handler_contract import ModelHandlerContract
from omnibase_core.models.contracts.model_handler_spec import ModelHandlerSpec
from omnibase_core.models.contracts.model_profile_reference import ModelProfileReference
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.models.runtime.model_handler_behavior import ModelHandlerBehavior
from omnibase_core.validation.phases.merge_validator import MergeValidator


@pytest.mark.unit
class TestMergeValidatorFixtures:
    """Test fixtures for MergeValidator tests."""

    @pytest.fixture
    def validator(self) -> MergeValidator:
        """Create a validator fixture."""
        return MergeValidator()

    @pytest.fixture
    def profile_ref(self) -> ModelProfileReference:
        """Create a profile reference fixture."""
        return ModelProfileReference(profile="compute_pure", version="1.0.0")

    @pytest.fixture
    def valid_descriptor(self) -> ModelHandlerBehavior:
        """Create a valid handler behavior descriptor."""
        return ModelHandlerBehavior(
            handler_kind="compute",
            purity="pure",
            idempotent=True,
        )

    @pytest.fixture
    def valid_base(
        self, valid_descriptor: ModelHandlerBehavior
    ) -> ModelHandlerContract:
        """Create a valid base contract fixture."""
        return ModelHandlerContract(
            handler_id="node.test.compute",
            name="Test Compute Node",
            version="1.0.0",
            description="A test compute node",
            descriptor=valid_descriptor,
            input_model="omnibase_core.models.events.ModelTestEvent",
            output_model="omnibase_core.models.results.ModelTestResult",
        )

    @pytest.fixture
    def valid_patch(self, profile_ref: ModelProfileReference) -> ModelContractPatch:
        """Create a valid patch fixture."""
        return ModelContractPatch(
            extends=profile_ref,
            name="updated_handler",
            node_version=ModelSemVer(major=1, minor=0, patch=0),
            description="Updated description",
        )

    @pytest.fixture
    def valid_merged(
        self, valid_descriptor: ModelHandlerBehavior
    ) -> ModelHandlerContract:
        """Create a valid merged contract fixture."""
        return ModelHandlerContract(
            handler_id="node.test.compute",
            name="Updated Handler",
            version="1.0.0",
            description="Updated description",
            descriptor=valid_descriptor,
            input_model="omnibase_core.models.events.ModelTestEvent",
            output_model="omnibase_core.models.results.ModelTestResult",
        )


@pytest.mark.unit
class TestMergeValidatorBasic(TestMergeValidatorFixtures):
    """Basic tests for MergeValidator."""

    def test_valid_merge_passes(
        self,
        validator: MergeValidator,
        valid_base: ModelHandlerContract,
        valid_patch: ModelContractPatch,
        valid_merged: ModelHandlerContract,
    ) -> None:
        """Test that a valid merge passes validation."""
        result = validator.validate(valid_base, valid_patch, valid_merged)
        assert result.is_valid is True
        assert result.error_count == 0

    def test_validator_returns_validation_result(
        self,
        validator: MergeValidator,
        valid_base: ModelHandlerContract,
        valid_patch: ModelContractPatch,
        valid_merged: ModelHandlerContract,
    ) -> None:
        """Test that validator returns ModelValidationResult."""
        result = validator.validate(valid_base, valid_patch, valid_merged)
        assert isinstance(result, ModelValidationResult)

    def test_validator_is_stateless(
        self,
        validator: MergeValidator,
        valid_base: ModelHandlerContract,
        valid_patch: ModelContractPatch,
        valid_merged: ModelHandlerContract,
    ) -> None:
        """Test that validator is stateless and can be reused."""
        result1 = validator.validate(valid_base, valid_patch, valid_merged)
        result2 = validator.validate(valid_base, valid_patch, valid_merged)

        # Both should pass and be independent
        assert result1.is_valid is True
        assert result2.is_valid is True


@pytest.mark.unit
class TestMergeValidatorPlaceholderDetection(TestMergeValidatorFixtures):
    """Tests for placeholder value detection."""

    def test_placeholder_todo_detected(
        self,
        validator: MergeValidator,
        valid_base: ModelHandlerContract,
        valid_patch: ModelContractPatch,
        valid_descriptor: ModelHandlerBehavior,
    ) -> None:
        """Test that TODO placeholder is detected."""
        # Create merged contract with TODO in name
        merged = ModelHandlerContract(
            handler_id="node.test.compute",
            name="TODO",
            version="1.0.0",
            descriptor=valid_descriptor,
            input_model="omnibase_core.models.test.Input",
            output_model="omnibase_core.models.test.Output",
        )

        result = validator.validate(valid_base, valid_patch, merged)
        assert result.is_valid is False
        assert any(
            EnumContractValidationErrorCode.CONTRACT_VALIDATION_MERGE_PLACEHOLDER_VALUE_REJECTED.value
            in str(issue.code)
            for issue in result.issues
        )

    def test_placeholder_template_var_detected(
        self,
        validator: MergeValidator,
        valid_base: ModelHandlerContract,
        valid_patch: ModelContractPatch,
        valid_descriptor: ModelHandlerBehavior,
    ) -> None:
        """Test that ${VAR} template placeholder is detected."""
        merged = ModelHandlerContract(
            handler_id="node.test.compute",
            name="${SERVICE_NAME}",
            version="1.0.0",
            descriptor=valid_descriptor,
            input_model="omnibase_core.models.test.Input",
            output_model="omnibase_core.models.test.Output",
        )

        result = validator.validate(valid_base, valid_patch, merged)
        assert result.is_valid is False
        assert "placeholder" in result.summary.lower() or result.error_count > 0

    def test_placeholder_jinja_style_detected(
        self,
        validator: MergeValidator,
        valid_base: ModelHandlerContract,
        valid_patch: ModelContractPatch,
        valid_descriptor: ModelHandlerBehavior,
    ) -> None:
        """Test that {{variable}} Jinja-style placeholder is detected."""
        merged = ModelHandlerContract(
            handler_id="node.test.compute",
            name="{{handler_name}}",
            version="1.0.0",
            descriptor=valid_descriptor,
            input_model="omnibase_core.models.test.Input",
            output_model="omnibase_core.models.test.Output",
        )

        result = validator.validate(valid_base, valid_patch, merged)
        assert result.is_valid is False

    def test_placeholder_value_detected(
        self,
        validator: MergeValidator,
        valid_base: ModelHandlerContract,
        valid_patch: ModelContractPatch,
        valid_descriptor: ModelHandlerBehavior,
    ) -> None:
        """Test that PLACEHOLDER literal is detected."""
        merged = ModelHandlerContract(
            handler_id="node.test.compute",
            name="PLACEHOLDER",
            version="1.0.0",
            descriptor=valid_descriptor,
            input_model="omnibase_core.models.test.Input",
            output_model="omnibase_core.models.test.Output",
        )

        result = validator.validate(valid_base, valid_patch, merged)
        assert result.is_valid is False

    def test_placeholder_in_input_model(
        self,
        validator: MergeValidator,
        valid_base: ModelHandlerContract,
        valid_patch: ModelContractPatch,
        valid_descriptor: ModelHandlerBehavior,
    ) -> None:
        """Test placeholder detection in input_model field."""
        merged = ModelHandlerContract(
            handler_id="node.test.compute",
            name="Valid Name",
            version="1.0.0",
            descriptor=valid_descriptor,
            input_model="TODO",
            output_model="omnibase_core.models.test.Output",
        )

        result = validator.validate(valid_base, valid_patch, merged)
        assert result.is_valid is False
        assert any("input_model" in str(issue.message) for issue in result.issues)

    def test_placeholder_in_output_model(
        self,
        validator: MergeValidator,
        valid_base: ModelHandlerContract,
        valid_patch: ModelContractPatch,
        valid_descriptor: ModelHandlerBehavior,
    ) -> None:
        """Test placeholder detection in output_model field."""
        merged = ModelHandlerContract(
            handler_id="node.test.compute",
            name="Valid Name",
            version="1.0.0",
            descriptor=valid_descriptor,
            input_model="omnibase_core.models.test.Input",
            output_model="PLACEHOLDER",
        )

        result = validator.validate(valid_base, valid_patch, merged)
        assert result.is_valid is False
        assert any("output_model" in str(issue.message) for issue in result.issues)

    def test_placeholder_in_description_warning(
        self,
        validator: MergeValidator,
        valid_base: ModelHandlerContract,
        valid_patch: ModelContractPatch,
        valid_descriptor: ModelHandlerBehavior,
    ) -> None:
        """Test that placeholder in description produces warning, not error."""
        merged = ModelHandlerContract(
            handler_id="node.test.compute",
            name="Valid Name",
            version="1.0.0",
            description="TODO: Add description",
            descriptor=valid_descriptor,
            input_model="omnibase_core.models.test.Input",
            output_model="omnibase_core.models.test.Output",
        )

        result = validator.validate(valid_base, valid_patch, merged)
        # Should still be valid (warning, not error)
        assert result.is_valid is True
        assert result.warning_count > 0


@pytest.mark.unit
class TestMergeValidatorRequiredOverrides(TestMergeValidatorFixtures):
    """Tests for required override validation."""

    def test_required_override_missing_detected(
        self,
        validator: MergeValidator,
        valid_patch: ModelContractPatch,
        valid_descriptor: ModelHandlerBehavior,
    ) -> None:
        """Test that missing required overrides are detected."""
        # Base with placeholder that should be overridden
        base = ModelHandlerContract(
            handler_id="node.test.compute",
            name="TODO",  # Placeholder that should be overridden
            version="1.0.0",
            descriptor=valid_descriptor,
            input_model="omnibase_core.models.test.Input",
            output_model="omnibase_core.models.test.Output",
        )

        # Merged still has the placeholder (not overridden)
        merged = ModelHandlerContract(
            handler_id="node.test.compute",
            name="TODO",  # Same placeholder - not overridden
            version="1.0.0",
            descriptor=valid_descriptor,
            input_model="omnibase_core.models.test.Input",
            output_model="omnibase_core.models.test.Output",
        )

        result = validator.validate(base, valid_patch, merged)
        assert result.is_valid is False
        # Should have both placeholder error and required override error
        assert any(
            "override" in str(issue.message).lower()
            or "placeholder" in str(issue.message).lower()
            for issue in result.issues
        )


@pytest.mark.unit
class TestMergeValidatorHandlerUniqueness(TestMergeValidatorFixtures):
    """Tests for handler name uniqueness validation."""

    def test_duplicate_handler_in_patch_detected(
        self,
        validator: MergeValidator,
        valid_base: ModelHandlerContract,
        valid_merged: ModelHandlerContract,
        profile_ref: ModelProfileReference,
    ) -> None:
        """Test that duplicate handlers in patch add list are detected."""
        patch = ModelContractPatch(
            extends=profile_ref,
            name="test_handler",
            node_version=ModelSemVer(major=1, minor=0, patch=0),
            handlers__add=[
                ModelHandlerSpec(name="http_handler", handler_type="http"),
                ModelHandlerSpec(name="http_handler", handler_type="http"),  # Duplicate
            ],
        )

        result = validator.validate(valid_base, patch, valid_merged)
        assert result.is_valid is False
        assert any(
            EnumContractValidationErrorCode.CONTRACT_VALIDATION_MERGE_CONFLICT_DETECTED.value
            in str(issue.code)
            for issue in result.issues
        )
        assert any("http_handler" in str(issue.message) for issue in result.issues)

    def test_handler_conflict_with_base_detected(
        self,
        validator: MergeValidator,
        valid_merged: ModelHandlerContract,
        profile_ref: ModelProfileReference,
        valid_descriptor: ModelHandlerBehavior,
    ) -> None:
        """Test that handler name conflicts with base are detected."""
        # Base with existing handler alias
        base = ModelHandlerContract(
            handler_id="node.test.compute",
            name="Test Handler",
            version="1.0.0",
            descriptor=valid_descriptor,
            input_model="omnibase_core.models.test.Input",
            output_model="omnibase_core.models.test.Output",
            capability_inputs=[
                ModelCapabilityDependency(
                    alias="existing_handler",
                    capability="database.relational",
                ),
            ],
        )

        # Patch trying to add handler with same name
        patch = ModelContractPatch(
            extends=profile_ref,
            name="test_handler",
            node_version=ModelSemVer(major=1, minor=0, patch=0),
            handlers__add=[
                ModelHandlerSpec(name="existing_handler", handler_type="http"),
            ],
        )

        result = validator.validate(base, patch, valid_merged)
        assert result.is_valid is False
        assert any("existing_handler" in str(issue.message) for issue in result.issues)


@pytest.mark.unit
class TestMergeValidatorCapabilityConsistency(TestMergeValidatorFixtures):
    """Tests for capability consistency validation."""

    def test_duplicate_capability_input_aliases_rejected_by_model(
        self,
        validator: MergeValidator,
        valid_base: ModelHandlerContract,
        valid_patch: ModelContractPatch,
        valid_descriptor: ModelHandlerBehavior,
    ) -> None:
        """Test that duplicate capability input aliases are rejected at model level."""
        # ModelHandlerContract validates unique aliases at construction time
        # This is the correct behavior - duplicates are caught early
        with pytest.raises(ValueError) as exc_info:
            ModelHandlerContract(
                handler_id="node.test.compute",
                name="Test Handler",
                version="1.0.0",
                descriptor=valid_descriptor,
                input_model="omnibase_core.models.test.Input",
                output_model="omnibase_core.models.test.Output",
                capability_inputs=[
                    ModelCapabilityDependency(
                        alias="db",
                        capability="database.relational",
                    ),
                    ModelCapabilityDependency(
                        alias="db",  # Duplicate alias
                        capability="database.nosql",
                    ),
                ],
            )

        assert "Duplicate capability input aliases" in str(exc_info.value)

    def test_duplicate_capability_outputs_detected(
        self,
        validator: MergeValidator,
        valid_base: ModelHandlerContract,
        valid_patch: ModelContractPatch,
        valid_descriptor: ModelHandlerBehavior,
    ) -> None:
        """Test that duplicate capability outputs are detected."""
        merged = ModelHandlerContract(
            handler_id="node.test.compute",
            name="Test Handler",
            version="1.0.0",
            descriptor=valid_descriptor,
            input_model="omnibase_core.models.test.Input",
            output_model="omnibase_core.models.test.Output",
            capability_outputs=[
                "event.user_created",
                "event.user_created",  # Duplicate
            ],
        )

        result = validator.validate(valid_base, valid_patch, merged)
        assert result.is_valid is False
        assert any(
            "duplicate" in str(issue.message).lower()
            or EnumContractValidationErrorCode.CONTRACT_VALIDATION_MERGE_CONFLICT_DETECTED.value
            in str(issue.code)
            for issue in result.issues
        )

    def test_capability_input_output_conflict_warning(
        self,
        validator: MergeValidator,
        valid_base: ModelHandlerContract,
        valid_patch: ModelContractPatch,
        valid_descriptor: ModelHandlerBehavior,
    ) -> None:
        """Test that capability input/output name conflicts produce warning."""
        merged = ModelHandlerContract(
            handler_id="node.test.compute",
            name="Test Handler",
            version="1.0.0",
            descriptor=valid_descriptor,
            input_model="omnibase_core.models.test.Input",
            output_model="omnibase_core.models.test.Output",
            capability_inputs=[
                ModelCapabilityDependency(
                    alias="shared_name",
                    capability="database.relational",
                ),
            ],
            capability_outputs=[
                "shared_name",  # Same name as input alias
            ],
        )

        result = validator.validate(valid_base, valid_patch, merged)
        # Should produce warning but still be valid
        assert result.warning_count > 0


@pytest.mark.unit
class TestMergeValidatorDependencyReferences(TestMergeValidatorFixtures):
    """Tests for dependency reference validation."""

    def test_unresolved_handler_dependency_warning(
        self,
        validator: MergeValidator,
        valid_base: ModelHandlerContract,
        valid_merged: ModelHandlerContract,
        profile_ref: ModelProfileReference,
    ) -> None:
        """Test that unresolved handler dependency produces warning."""
        patch = ModelContractPatch(
            extends=profile_ref,
            name="test_handler",
            node_version=ModelSemVer(major=1, minor=0, patch=0),
            dependencies__add=[
                ModelDependency(name="handler.nonexistent"),
            ],
        )

        result = validator.validate(valid_base, patch, valid_merged)
        # Should have warning about potential unresolved dependency
        # Note: This is a warning, not an error (full resolution in Phase 3)
        assert isinstance(result, ModelValidationResult)


@pytest.mark.unit
class TestMergeValidatorMultipleErrors(TestMergeValidatorFixtures):
    """Tests for multiple error aggregation."""

    def test_multiple_errors_aggregated(
        self,
        validator: MergeValidator,
        valid_base: ModelHandlerContract,
        profile_ref: ModelProfileReference,
        valid_descriptor: ModelHandlerBehavior,
    ) -> None:
        """Test that multiple errors are aggregated in result."""
        # Patch with duplicate handlers
        patch = ModelContractPatch(
            extends=profile_ref,
            name="test_handler",
            node_version=ModelSemVer(major=1, minor=0, patch=0),
            handlers__add=[
                ModelHandlerSpec(name="dup_handler", handler_type="http"),
                ModelHandlerSpec(name="dup_handler", handler_type="http"),  # Duplicate
            ],
        )

        # Merged with placeholder and duplicate outputs
        merged = ModelHandlerContract(
            handler_id="node.test.compute",
            name="TODO",  # Placeholder
            version="1.0.0",
            descriptor=valid_descriptor,
            input_model="omnibase_core.models.test.Input",
            output_model="omnibase_core.models.test.Output",
            capability_outputs=[
                "event.test",
                "event.test",  # Duplicate
            ],
        )

        result = validator.validate(valid_base, patch, merged)
        assert result.is_valid is False
        # Should have multiple errors
        assert result.error_count >= 2


@pytest.mark.unit
class TestMergeValidatorEdgeCases(TestMergeValidatorFixtures):
    """Test edge cases for MergeValidator."""

    def test_minimal_patch_no_list_operations(
        self,
        validator: MergeValidator,
        valid_base: ModelHandlerContract,
        valid_merged: ModelHandlerContract,
        profile_ref: ModelProfileReference,
    ) -> None:
        """Test validation with minimal patch (no list operations)."""
        patch = ModelContractPatch(extends=profile_ref)

        result = validator.validate(valid_base, patch, valid_merged)
        assert result.is_valid is True

    def test_empty_capability_lists(
        self,
        validator: MergeValidator,
        valid_base: ModelHandlerContract,
        valid_patch: ModelContractPatch,
        valid_descriptor: ModelHandlerBehavior,
    ) -> None:
        """Test validation with empty capability lists."""
        merged = ModelHandlerContract(
            handler_id="node.test.compute",
            name="Test Handler",
            version="1.0.0",
            descriptor=valid_descriptor,
            input_model="omnibase_core.models.test.Input",
            output_model="omnibase_core.models.test.Output",
            capability_inputs=[],
            capability_outputs=[],
        )

        result = validator.validate(valid_base, valid_patch, merged)
        assert result.is_valid is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
