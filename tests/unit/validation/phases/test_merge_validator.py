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
- Property-based tests for placeholder detection edge cases

Related:
    - OMN-1128: Contract Validation Pipeline
"""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

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
from omnibase_core.validation.phases.merge_validator import (
    MergeValidator,
    _is_placeholder_value,
)


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
        """Test that validator returns ModelValidationResult with expected structure."""
        result = validator.validate(valid_base, valid_patch, valid_merged)
        assert isinstance(result, ModelValidationResult)
        # Verify result has expected structure and valid content
        assert hasattr(result, "is_valid")
        assert hasattr(result, "issues")
        assert result.is_valid is True
        assert isinstance(result.issues, list)
        assert result.error_count == 0

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
        # Verify the specific warning message contains expected content
        # result.warnings is a list of strings (legacy field)
        assert any(
            "description" in msg.lower() and "placeholder" in msg.lower()
            for msg in result.warnings
        ), f"Expected warning about placeholder in description, got: {result.warnings}"
        # Get detailed warning issues for code verification
        from omnibase_core.enums.enum_validation_severity import EnumValidationSeverity

        warning_issues = result.get_issues_by_severity(EnumValidationSeverity.WARNING)
        warning_codes = [issue.code for issue in warning_issues if issue.code]
        assert any(
            EnumContractValidationErrorCode.CONTRACT_VALIDATION_MERGE_PLACEHOLDER_VALUE_REJECTED.value
            in code
            for code in warning_codes
        ), f"Expected PLACEHOLDER_VALUE_REJECTED code, got: {warning_codes}"


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
        # Pydantic wraps the ValueError from field_validator into ValidationError
        with pytest.raises(ValidationError) as exc_info:
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

        # ValidationError contains the original message from the field validator
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
        assert result.is_valid is True
        assert result.warning_count > 0
        # Verify warning message mentions the conflicting name
        assert any("shared_name" in msg.lower() for msg in result.warnings), (
            f"Expected warning about 'shared_name' conflict, got: {result.warnings}"
        )


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
        # Validation should pass (warnings don't fail validation)
        assert result.is_valid is True
        assert result.error_count == 0
        # Verify the warning was produced for the unresolved dependency
        has_dependency_warning = result.warning_count > 0 or any(
            "handler.nonexistent" in str(issue.message) for issue in result.issues
        )
        assert has_dependency_warning, (
            f"Expected warning about unresolved handler dependency 'handler.nonexistent', "
            f"got warnings: {result.warnings}, issues: {[str(i.message) for i in result.issues]}"
        )

    def test_multi_segment_handler_reference_no_false_positive(
        self,
        validator: MergeValidator,
        valid_merged: ModelHandlerContract,
        profile_ref: ModelProfileReference,
        valid_descriptor: ModelHandlerBehavior,
    ) -> None:
        """Test that multi-segment handler references don't produce false positives.

        When a dependency name like "node.user.compute" is checked against known
        handlers, it should extract "user.compute" (not just "compute") to avoid
        incorrectly matching unrelated handlers.

        This test verifies the fix for PR #321 feedback about false positives
        in handler reference extraction.
        """
        # Base with a handler named "compute" (not "user.compute")
        base = ModelHandlerContract(
            handler_id="node.test.compute",
            name="Test Handler",
            version="1.0.0",
            descriptor=valid_descriptor,
            input_model="omnibase_core.models.test.Input",
            output_model="omnibase_core.models.test.Output",
            capability_inputs=[
                ModelCapabilityDependency(
                    alias="compute",  # Handler named just "compute"
                    capability="compute.generic",
                ),
            ],
        )

        # Dependency referencing "node.user.compute" (different from "compute")
        patch = ModelContractPatch(
            extends=profile_ref,
            name="test_handler",
            node_version=ModelSemVer(major=1, minor=0, patch=0),
            dependencies__add=[
                ModelDependency(
                    name="node.user.compute"
                ),  # Should extract "user.compute"
            ],
        )

        result = validator.validate(base, patch, valid_merged)

        # Should produce warning because "user.compute" != "compute"
        # (Previously, extracting only "compute" would incorrectly match)
        assert result.is_valid is True
        assert result.warning_count > 0, (
            "Expected warning about unresolved 'node.user.compute' reference. "
            "The handler 'compute' exists but 'user.compute' does not. "
            "If this test fails, handler reference extraction may be using only "
            "the last segment instead of the full reference after the prefix."
        )

    def test_handler_prefix_multi_segment_extraction(
        self,
        validator: MergeValidator,
        valid_merged: ModelHandlerContract,
        profile_ref: ModelProfileReference,
        valid_descriptor: ModelHandlerBehavior,
    ) -> None:
        """Test that 'handler.' prefix extracts full reference after prefix.

        A dependency like "handler.module.submodule.my_handler" should extract
        "module.submodule.my_handler" (not just "my_handler").
        """
        # Base with handler named "my_handler" (not "module.submodule.my_handler")
        base = ModelHandlerContract(
            handler_id="node.test.compute",
            name="Test Handler",
            version="1.0.0",
            descriptor=valid_descriptor,
            input_model="omnibase_core.models.test.Input",
            output_model="omnibase_core.models.test.Output",
            capability_inputs=[
                ModelCapabilityDependency(
                    alias="my_handler",  # Simple name
                    capability="handler.generic",
                ),
            ],
        )

        # Dependency with multi-segment reference
        patch = ModelContractPatch(
            extends=profile_ref,
            name="test_handler",
            node_version=ModelSemVer(major=1, minor=0, patch=0),
            dependencies__add=[
                ModelDependency(name="handler.module.submodule.my_handler"),
            ],
        )

        result = validator.validate(base, patch, valid_merged)

        # Should produce warning: "module.submodule.my_handler" != "my_handler"
        assert result.is_valid is True
        assert result.warning_count > 0, (
            "Expected warning about unresolved 'handler.module.submodule.my_handler'. "
            "The reference extracts 'module.submodule.my_handler', not just 'my_handler'."
        )


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


@pytest.mark.unit
class TestPlaceholderDetectionHypothesis:
    """Property-based tests for _is_placeholder_value using hypothesis.

    These tests verify edge cases and invariants of placeholder detection
    that would be difficult to cover with example-based tests alone.
    """

    @given(st.text(min_size=0, alphabet=st.characters(blacklist_categories=["Cs"])))
    @settings(max_examples=100)
    def test_placeholder_detection_no_crash(self, text: str) -> None:
        """Property test: _is_placeholder_value never crashes on any input.

        Tests that the function handles arbitrary Unicode strings without
        raising exceptions. Uses blacklist_categories=['Cs'] to exclude
        surrogate characters which are invalid in Python strings.
        """
        result = _is_placeholder_value(text)
        assert isinstance(result, bool)

    @given(st.just(""))
    def test_empty_string_is_placeholder(self, text: str) -> None:
        """Property test: empty strings are always placeholders."""
        assert _is_placeholder_value(text) is True

    @given(st.text(alphabet=" \t\n\r\f\v", min_size=1, max_size=20))
    @settings(max_examples=50)
    def test_whitespace_only_is_placeholder(self, text: str) -> None:
        """Property test: whitespace-only strings are always placeholders."""
        assert _is_placeholder_value(text) is True

    @given(
        st.sampled_from(
            [
                "todo",
                "TODO",
                "Todo",
                "tbd",
                "TBD",
                "fixme",
                "FIXME",
                "placeholder",
                "PLACEHOLDER",
                "replace_me",
                "REPLACE_ME",
                "change_me",
                "CHANGE_ME",
                "undefined",
                "UNDEFINED",
                "default",
                "DEFAULT",
                "example",
                "EXAMPLE",
                "sample",
                "SAMPLE",
                "test",
                "TEST",
                "xxx",
                "XXX",
                "???",
                "...",
            ]
        )
    )
    def test_exact_patterns_are_placeholders(self, text: str) -> None:
        """Property test: exact pattern matches are always placeholders.

        Verifies that all known placeholder patterns are detected regardless
        of case (for case-insensitive patterns).
        """
        assert _is_placeholder_value(text) is True

    @given(
        st.sampled_from(
            [
                "  todo  ",
                "\tTODO\n",
                " placeholder ",
                "\n\ntest\n\n",
                "  ???  ",
            ]
        )
    )
    def test_exact_patterns_with_whitespace_padding(self, text: str) -> None:
        """Property test: exact patterns with whitespace padding are placeholders.

        Verifies that the function correctly strips whitespace before matching.
        """
        assert _is_placeholder_value(text) is True

    @given(
        st.text(
            alphabet=st.characters(
                whitelist_categories=["Ll", "Lu", "Nd"], whitelist_characters="_"
            ),
            min_size=5,
            max_size=50,
        )
    )
    @settings(max_examples=100)
    def test_normal_identifiers_not_placeholders(self, text: str) -> None:
        """Property test: normal alphanumeric identifiers are not placeholders.

        Generates valid identifier-like strings and verifies they're not
        falsely detected as placeholders. Uses a prefix/suffix to avoid
        accidentally generating exact matches like "test" or "default".
        """
        # Add a prefix to avoid matching exact patterns like "todo" or "test"
        identifier = f"handler_{text}_service"
        result = _is_placeholder_value(identifier)
        assert result is False, f"'{identifier}' incorrectly detected as placeholder"

    @given(
        st.text(
            alphabet=st.characters(
                whitelist_categories=["Ll", "Lu", "Nd"], whitelist_characters="_"
            ),
            min_size=1,
            max_size=30,
        )
    )
    @settings(max_examples=100)
    def test_valid_handler_names_not_placeholders(self, suffix: str) -> None:
        """Property test: realistic handler names are never placeholders.

        Uses common handler naming patterns to verify no false positives.
        """
        # Common handler naming patterns
        handler_names = [
            f"compute_{suffix}",
            f"effect_{suffix}_handler",
            f"NodeTest{suffix}Compute",
            f"process_{suffix}_event",
        ]
        for name in handler_names:
            result = _is_placeholder_value(name)
            assert result is False, f"'{name}' incorrectly detected as placeholder"

    @given(st.sampled_from(["${VAR}", "${SERVICE_NAME}", "${DB_HOST}"]))
    def test_template_var_placeholders_detected(self, text: str) -> None:
        """Property test: ${VAR} style templates are detected as placeholders."""
        assert _is_placeholder_value(text) is True

    @given(st.sampled_from(["{{name}}", "{{handler_name}}", "{{config.value}}"]))
    def test_jinja_style_placeholders_detected(self, text: str) -> None:
        """Property test: {{var}} Jinja-style templates are detected as placeholders."""
        assert _is_placeholder_value(text) is True

    @given(st.sampled_from(["<PLACEHOLDER>", "<NAME>", "<CONFIG_VALUE>"]))
    def test_angle_bracket_placeholders_detected(self, text: str) -> None:
        """Property test: <PLACEHOLDER> style markers are detected as placeholders."""
        assert _is_placeholder_value(text) is True

    @given(
        st.sampled_from(
            ["TODO: implement this", "TODO: add description", "TODO: fix later"]
        )
    )
    def test_todo_prefix_placeholders_detected(self, text: str) -> None:
        """Property test: 'TODO:' prefixed strings are detected as placeholders."""
        assert _is_placeholder_value(text) is True

    @given(
        st.text(
            alphabet=st.characters(
                whitelist_categories=["Lu", "Ll", "Lo", "Nd"],
                whitelist_characters="_-.",
            ),
            min_size=10,
            max_size=100,
        )
    )
    @settings(max_examples=100)
    def test_long_strings_not_mistakenly_placeholders(self, text: str) -> None:
        """Property test: long valid strings are not mistakenly detected.

        Verifies that longer strings containing placeholder-like substrings
        are not falsely detected when wrapped in valid identifiers.
        """
        # Wrap in a valid model path pattern
        model_path = f"omnibase_core.models.{text}.Model"
        result = _is_placeholder_value(model_path)
        # Should only be True if it contains actual template patterns
        if "${" not in model_path and "{{" not in model_path and "<" not in model_path:
            # Check it's not an exact match after normalization
            normalized = model_path.strip().lower()
            exact_patterns = frozenset(
                {
                    "todo",
                    "tbd",
                    "fixme",
                    "placeholder",
                    "replace_me",
                    "change_me",
                    "undefined",
                    "default",
                    "example",
                    "sample",
                    "test",
                    "xxx",
                    "???",
                    "...",
                }
            )
            if normalized not in exact_patterns and not normalized.startswith("todo:"):
                assert result is False, (
                    f"'{model_path}' incorrectly detected as placeholder"
                )

    @given(
        st.text(
            alphabet=st.characters(
                whitelist_categories=["L", "N", "P", "S"],
                blacklist_categories=["Cs"],
                blacklist_characters="${}|<>",
            ),
            min_size=20,
            max_size=100,
        )
    )
    @settings(max_examples=100)
    def test_unicode_strings_without_template_markers(self, text: str) -> None:
        """Property test: Unicode strings without template markers handled correctly.

        Tests that various Unicode characters (letters, numbers, punctuation,
        symbols) don't cause crashes and are correctly classified.
        """
        # Wrap to avoid exact matches
        wrapped = f"prefix_{text}_suffix"
        result = _is_placeholder_value(wrapped)
        # Result should be bool (we're mostly testing no crash)
        assert isinstance(result, bool)

    @given(st.sampled_from(["testHandler", "test_handler", "mytest", "testing123"]))
    def test_strings_containing_test_not_placeholders(self, text: str) -> None:
        """Property test: strings containing 'test' as substring are not placeholders.

        Verifies that only exact match of 'test' triggers placeholder detection,
        not substrings like 'testing' or 'test_handler'.
        """
        result = _is_placeholder_value(text)
        assert result is False, f"'{text}' incorrectly detected as placeholder"

    @given(st.sampled_from(["default_value", "my_default", "defaultHandler"]))
    def test_strings_containing_default_not_placeholders(self, text: str) -> None:
        """Property test: strings containing 'default' as substring are not placeholders.

        Verifies that only exact match of 'default' triggers placeholder detection.
        """
        result = _is_placeholder_value(text)
        assert result is False, f"'{text}' incorrectly detected as placeholder"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
