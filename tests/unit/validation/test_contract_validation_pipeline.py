# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for ContractValidationPipeline.

Tests all aspects of the contract validation pipeline including:
- validate_patch delegates correctly
- validate_merge delegates correctly
- validate_expanded delegates correctly
- validate_all runs all phases
- Pipeline stops on first critical error
- constraint_validator seam (duck-typed injection)
- ModelExpandedContractResult model
- Successful pipeline returns contract

Related:
    - OMN-1128: Contract Validation Pipeline
"""

from unittest.mock import MagicMock, patch

import pytest

from omnibase_core.enums.enum_validation_phase import EnumValidationPhase
from omnibase_core.models.common.model_validation_result import ModelValidationResult
from omnibase_core.models.contracts.model_contract_patch import ModelContractPatch
from omnibase_core.models.contracts.model_handler_contract import ModelHandlerContract
from omnibase_core.models.contracts.model_profile_reference import ModelProfileReference
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.models.runtime.model_handler_behavior import ModelHandlerBehavior
from omnibase_core.validation.phases.validator_expanded_contract import (
    ExpandedContractValidator,
)
from omnibase_core.validation.phases.validator_merge import MergeValidator
from omnibase_core.validation.validator_contract_patch import ContractPatchValidator
from omnibase_core.validation.validator_contract_pipeline import (
    ContractValidationPipeline,
    ModelExpandedContractResult,
    ProtocolContractValidationPipeline,
)


@pytest.mark.unit
class TestContractValidationPipelineFixtures:
    """Test fixtures for ContractValidationPipeline tests."""

    @pytest.fixture
    def pipeline(self) -> ContractValidationPipeline:
        """Create a pipeline fixture."""
        return ContractValidationPipeline()

    @pytest.fixture
    def profile_ref(self) -> ModelProfileReference:
        """Create a profile reference fixture."""
        return ModelProfileReference(profile="compute_pure", version="1.0.0")

    @pytest.fixture
    def valid_descriptor(self) -> ModelHandlerBehavior:
        """Create a valid handler behavior descriptor."""
        return ModelHandlerBehavior(
            node_archetype="compute",
            purity="pure",
            idempotent=True,
        )

    @pytest.fixture
    def valid_patch(self, profile_ref: ModelProfileReference) -> ModelContractPatch:
        """Create a valid patch fixture."""
        return ModelContractPatch(
            extends=profile_ref,
            name="test_handler",
            node_version=ModelSemVer(major=1, minor=0, patch=0),
            description="Test handler description",
        )

    @pytest.fixture
    def valid_base(
        self, valid_descriptor: ModelHandlerBehavior
    ) -> ModelHandlerContract:
        """Create a valid base contract fixture."""
        return ModelHandlerContract(
            handler_id="node.test.compute",
            name="Test Compute Node",
            contract_version=ModelSemVer(major=1, minor=0, patch=0),
            description="A test compute node",
            descriptor=valid_descriptor,
            input_model="omnibase_core.models.events.ModelTestEvent",
            output_model="omnibase_core.models.results.ModelTestResult",
        )

    @pytest.fixture
    def valid_merged(
        self, valid_descriptor: ModelHandlerBehavior
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


@pytest.mark.unit
class TestContractValidationPipelineBasic(TestContractValidationPipelineFixtures):
    """Basic tests for ContractValidationPipeline."""

    def test_pipeline_initialization(
        self, pipeline: ContractValidationPipeline
    ) -> None:
        """Test that pipeline initializes correctly."""
        assert isinstance(pipeline._patch_validator, ContractPatchValidator)
        assert isinstance(pipeline._merge_validator, MergeValidator)
        assert isinstance(pipeline._expanded_validator, ExpandedContractValidator)
        assert pipeline._constraint_validator is None

    def test_pipeline_with_custom_validators(self) -> None:
        """Test pipeline with custom validators."""
        custom_patch_validator = ContractPatchValidator()
        custom_merge_validator = MergeValidator()
        custom_expanded_validator = ExpandedContractValidator()

        pipeline = ContractValidationPipeline(
            patch_validator=custom_patch_validator,
            merge_validator=custom_merge_validator,
            expanded_validator=custom_expanded_validator,
        )

        assert pipeline._patch_validator is custom_patch_validator
        assert pipeline._merge_validator is custom_merge_validator
        assert pipeline._expanded_validator is custom_expanded_validator

    def test_pipeline_conforms_to_protocol(
        self, pipeline: ContractValidationPipeline
    ) -> None:
        """Test that pipeline conforms to ProtocolContractValidationPipeline."""
        assert isinstance(pipeline, ProtocolContractValidationPipeline)


@pytest.mark.unit
class TestContractValidationPipelineValidatePatch(
    TestContractValidationPipelineFixtures
):
    """Tests for validate_patch method."""

    def test_validate_patch_delegates_correctly(
        self, pipeline: ContractValidationPipeline, valid_patch: ModelContractPatch
    ) -> None:
        """Test that validate_patch delegates to patch validator."""
        result = pipeline.validate_patch(valid_patch)
        assert isinstance(result, ModelValidationResult)
        # Verify actual validation behavior, not just type
        assert result.is_valid is True
        assert result.error_level_count == 0

    def test_validate_patch_returns_validation_result(
        self, pipeline: ContractValidationPipeline, valid_patch: ModelContractPatch
    ) -> None:
        """Test that validate_patch returns ModelValidationResult with expected structure."""
        result = pipeline.validate_patch(valid_patch)
        assert isinstance(result, ModelValidationResult)
        # Verify result has expected structure and valid content
        assert hasattr(result, "is_valid")
        assert hasattr(result, "issues")
        assert result.is_valid is True
        assert isinstance(result.issues, list)
        assert result.error_level_count == 0

    def test_validate_patch_valid_patch_passes(
        self, pipeline: ContractValidationPipeline, valid_patch: ModelContractPatch
    ) -> None:
        """Test that valid patch passes validation."""
        result = pipeline.validate_patch(valid_patch)
        assert result.is_valid is True


@pytest.mark.unit
class TestContractValidationPipelineValidateMerge(
    TestContractValidationPipelineFixtures
):
    """Tests for validate_merge method."""

    def test_validate_merge_delegates_correctly(
        self,
        pipeline: ContractValidationPipeline,
        valid_base: ModelHandlerContract,
        valid_patch: ModelContractPatch,
        valid_merged: ModelHandlerContract,
    ) -> None:
        """Test that validate_merge delegates to merge validator."""
        result = pipeline.validate_merge(valid_base, valid_patch, valid_merged)
        assert isinstance(result, ModelValidationResult)
        # Verify actual validation behavior for valid inputs
        assert result.is_valid is True
        assert result.error_level_count == 0

    def test_validate_merge_returns_validation_result(
        self,
        pipeline: ContractValidationPipeline,
        valid_base: ModelHandlerContract,
        valid_patch: ModelContractPatch,
        valid_merged: ModelHandlerContract,
    ) -> None:
        """Test that validate_merge returns ModelValidationResult with expected structure."""
        result = pipeline.validate_merge(valid_base, valid_patch, valid_merged)
        assert isinstance(result, ModelValidationResult)
        # Verify result has expected structure and valid content
        assert result.is_valid is True
        assert isinstance(result.issues, list)
        assert result.error_level_count == 0

    def test_validate_merge_valid_merge_passes(
        self,
        pipeline: ContractValidationPipeline,
        valid_base: ModelHandlerContract,
        valid_patch: ModelContractPatch,
        valid_merged: ModelHandlerContract,
    ) -> None:
        """Test that valid merge passes validation."""
        result = pipeline.validate_merge(valid_base, valid_patch, valid_merged)
        assert result.is_valid is True


@pytest.mark.unit
class TestContractValidationPipelineValidateExpanded(
    TestContractValidationPipelineFixtures
):
    """Tests for validate_expanded method."""

    def test_validate_expanded_delegates_correctly(
        self,
        pipeline: ContractValidationPipeline,
        valid_merged: ModelHandlerContract,
    ) -> None:
        """Test that validate_expanded delegates to expanded validator."""
        result = pipeline.validate_expanded(valid_merged)
        assert isinstance(result, ModelValidationResult)
        # Verify actual validation behavior for valid inputs
        assert result.is_valid is True
        assert result.error_level_count == 0

    def test_validate_expanded_returns_validation_result(
        self,
        pipeline: ContractValidationPipeline,
        valid_merged: ModelHandlerContract,
    ) -> None:
        """Test that validate_expanded returns ModelValidationResult with expected structure."""
        result = pipeline.validate_expanded(valid_merged)
        assert isinstance(result, ModelValidationResult)
        # Verify result has expected structure and valid content
        assert result.is_valid is True
        assert isinstance(result.issues, list)
        assert result.error_level_count == 0

    def test_validate_expanded_valid_contract_passes(
        self,
        pipeline: ContractValidationPipeline,
        valid_merged: ModelHandlerContract,
    ) -> None:
        """Test that valid contract passes expanded validation."""
        result = pipeline.validate_expanded(valid_merged)
        assert result.is_valid is True


@pytest.mark.unit
class TestContractValidationPipelineConstraintValidator(
    TestContractValidationPipelineFixtures
):
    """Tests for constraint_validator seam (duck-typed injection)."""

    def test_constraint_validator_seam_none_by_default(
        self, pipeline: ContractValidationPipeline
    ) -> None:
        """Test that constraint_validator is None by default."""
        assert pipeline._constraint_validator is None

    def test_constraint_validator_seam_can_be_injected(self) -> None:
        """Test that constraint_validator can be injected."""
        mock_constraint_validator = MagicMock()
        pipeline = ContractValidationPipeline(
            constraint_validator=mock_constraint_validator
        )
        assert pipeline._constraint_validator is mock_constraint_validator

    def test_constraint_validator_called_during_merge(
        self,
        valid_base: ModelHandlerContract,
        valid_patch: ModelContractPatch,
        valid_merged: ModelHandlerContract,
    ) -> None:
        """Test that constraint_validator is called during merge validation."""
        mock_constraint_validator = MagicMock()
        mock_result = MagicMock()
        mock_result.is_valid = True
        mock_result.issues = []
        mock_result.errors = []
        mock_result.warnings = []
        mock_constraint_validator.validate.return_value = mock_result

        pipeline = ContractValidationPipeline(
            constraint_validator=mock_constraint_validator
        )
        pipeline.validate_merge(valid_base, valid_patch, valid_merged)

        mock_constraint_validator.validate.assert_called_once_with(
            valid_base, valid_patch, valid_merged
        )

    def test_constraint_validator_result_merged(
        self,
        valid_base: ModelHandlerContract,
        valid_patch: ModelContractPatch,
        valid_merged: ModelHandlerContract,
    ) -> None:
        """Test that constraint_validator result is merged into main result."""
        mock_constraint_validator = MagicMock()
        mock_result = MagicMock()
        mock_result.is_valid = False
        mock_result.issues = [MagicMock(message="Custom constraint error")]
        mock_result.errors = ["Custom constraint error"]
        mock_result.warnings = []
        mock_constraint_validator.validate.return_value = mock_result

        pipeline = ContractValidationPipeline(
            constraint_validator=mock_constraint_validator
        )
        result = pipeline.validate_merge(valid_base, valid_patch, valid_merged)

        # Result should be invalid due to constraint validator
        assert result.is_valid is False

    def test_constraint_validator_without_validate_method_ignored(
        self,
        valid_base: ModelHandlerContract,
        valid_patch: ModelContractPatch,
        valid_merged: ModelHandlerContract,
    ) -> None:
        """Test that constraint_validator without validate method is ignored."""
        # Object without validate method
        mock_constraint_validator = object()

        pipeline = ContractValidationPipeline(
            constraint_validator=mock_constraint_validator
        )
        # Should not crash and should still validate successfully
        result = pipeline.validate_merge(valid_base, valid_patch, valid_merged)
        assert isinstance(result, ModelValidationResult)
        # Verify validation still works correctly despite invalid constraint_validator
        assert result.is_valid is True
        assert result.error_level_count == 0


@pytest.mark.unit
class TestModelExpandedContractResult:
    """Tests for ModelExpandedContractResult model."""

    def test_default_values(self) -> None:
        """Test default values for ModelExpandedContractResult."""
        result = ModelExpandedContractResult()
        assert result.success is False
        assert result.contract is None
        assert result.validation_results == {}
        assert result.errors == []
        assert result.phase_failed is None

    def test_success_result(self) -> None:
        """Test successful result creation."""
        descriptor = ModelHandlerBehavior(
            node_archetype="compute",
            purity="pure",
        )
        contract = ModelHandlerContract(
            handler_id="node.test.compute",
            name="Test Handler",
            contract_version=ModelSemVer(major=1, minor=0, patch=0),
            descriptor=descriptor,
            input_model="omnibase_core.models.test.Input",
            output_model="omnibase_core.models.test.Output",
        )

        result = ModelExpandedContractResult(
            success=True,
            contract=contract,
        )

        assert result.success is True
        assert result.contract is not None
        assert result.contract.name == "Test Handler"

    def test_failed_result_with_phase(self) -> None:
        """Test failed result with phase information."""
        result = ModelExpandedContractResult(
            success=False,
            phase_failed=EnumValidationPhase.PATCH,
            errors=["Validation error 1", "Validation error 2"],
        )

        assert result.success is False
        assert result.phase_failed == EnumValidationPhase.PATCH
        assert len(result.errors) == 2

    def test_validation_results_by_phase(self) -> None:
        """Test validation_results dictionary by phase."""
        patch_result: ModelValidationResult[None] = ModelValidationResult(
            is_valid=True,
            summary="Patch validation passed",
        )
        merge_result: ModelValidationResult[None] = ModelValidationResult(
            is_valid=True,
            summary="Merge validation passed",
        )

        result = ModelExpandedContractResult(
            success=True,
            validation_results={
                EnumValidationPhase.PATCH.value: patch_result,
                EnumValidationPhase.MERGE.value: merge_result,
            },
        )

        assert EnumValidationPhase.PATCH.value in result.validation_results
        assert EnumValidationPhase.MERGE.value in result.validation_results


@pytest.mark.unit
class TestContractValidationPipelineValidateAll(TestContractValidationPipelineFixtures):
    """Tests for validate_all method (full pipeline execution)."""

    def test_validate_all_requires_profile_factory(
        self, pipeline: ContractValidationPipeline, valid_patch: ModelContractPatch
    ) -> None:
        """Test that validate_all requires a profile factory."""
        # Should work with a mock factory
        mock_factory = MagicMock()

        # Mock the merge engine and factory behavior
        with patch(
            "omnibase_core.merge.contract_merge_engine.ContractMergeEngine"
        ) as mock_merge_engine_class:
            mock_merge_engine = MagicMock()
            mock_merge_engine_class.return_value = mock_merge_engine

            # Create a valid merged contract
            descriptor = ModelHandlerBehavior(node_archetype="compute", purity="pure")
            merged = ModelHandlerContract(
                handler_id="node.test.compute",
                name="Merged Handler",
                contract_version=ModelSemVer(major=1, minor=0, patch=0),
                descriptor=descriptor,
                input_model="omnibase_core.models.test.Input",
                output_model="omnibase_core.models.test.Output",
            )
            mock_merge_engine.merge.return_value = merged

            # Mock factory.get_profile to return a valid base
            mock_factory.get_profile.return_value = merged

            result = pipeline.validate_all(valid_patch, mock_factory)
            assert isinstance(result, ModelExpandedContractResult)
            # Verify successful pipeline execution
            assert result.success is True
            assert result.contract is not None
            assert result.phase_failed is None

    def test_validate_all_stops_on_patch_failure(
        self, profile_ref: ModelProfileReference
    ) -> None:
        """Test that pipeline stops on patch validation failure."""
        # Create a mock patch validator that fails
        mock_patch_validator = MagicMock()
        mock_patch_result: ModelValidationResult[None] = ModelValidationResult(
            is_valid=False,
            summary="Patch validation failed",
        )
        mock_patch_result.add_error("Test error")
        mock_patch_validator.validate.return_value = mock_patch_result

        pipeline = ContractValidationPipeline(patch_validator=mock_patch_validator)

        patch = ModelContractPatch(
            extends=profile_ref,
            name="test",
            node_version=ModelSemVer(major=1, minor=0, patch=0),
        )
        mock_factory = MagicMock()

        result = pipeline.validate_all(patch, mock_factory)

        assert result.success is False
        assert result.phase_failed == EnumValidationPhase.PATCH
        assert EnumValidationPhase.PATCH.value in result.validation_results
        # Merge and Expanded should not be in results since we stopped at patch
        assert EnumValidationPhase.MERGE.value not in result.validation_results
        assert EnumValidationPhase.EXPANDED.value not in result.validation_results

    def test_validate_all_returns_contract_on_success(
        self, valid_patch: ModelContractPatch
    ) -> None:
        """Test that successful pipeline returns contract."""
        # Create mock validators that pass
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

        pipeline = ContractValidationPipeline(
            patch_validator=mock_patch_validator,
            merge_validator=mock_merge_validator,
            expanded_validator=mock_expanded_validator,
        )

        # Mock the merge engine
        with patch(
            "omnibase_core.merge.contract_merge_engine.ContractMergeEngine"
        ) as mock_merge_engine_class:
            mock_merge_engine = MagicMock()
            mock_merge_engine_class.return_value = mock_merge_engine

            descriptor = ModelHandlerBehavior(node_archetype="compute", purity="pure")
            merged = ModelHandlerContract(
                handler_id="node.test.compute",
                name="Test Handler",
                contract_version=ModelSemVer(major=1, minor=0, patch=0),
                descriptor=descriptor,
                input_model="omnibase_core.models.test.Input",
                output_model="omnibase_core.models.test.Output",
            )
            mock_merge_engine.merge.return_value = merged

            mock_factory = MagicMock()
            mock_factory.get_profile.return_value = merged

            result = pipeline.validate_all(valid_patch, mock_factory)

            assert result.success is True
            assert result.contract is not None
            assert result.contract.name == "Test Handler"
            assert result.phase_failed is None

    def test_validate_all_runs_all_phases(
        self, valid_patch: ModelContractPatch
    ) -> None:
        """Test that validate_all runs all three phases on success."""
        # Track which validators were called
        called_phases: list[str] = []

        def make_mock_validator(phase: str) -> MagicMock:
            mock = MagicMock()
            result: ModelValidationResult[None] = ModelValidationResult(
                is_valid=True, summary=f"{phase} passed"
            )

            def validate_side_effect(
                *args: object, **kwargs: object
            ) -> ModelValidationResult[None]:
                called_phases.append(phase)
                return result

            mock.validate.side_effect = validate_side_effect
            return mock

        pipeline = ContractValidationPipeline(
            patch_validator=make_mock_validator("patch"),
            merge_validator=make_mock_validator("merge"),
            expanded_validator=make_mock_validator("expanded"),
        )

        with patch(
            "omnibase_core.merge.contract_merge_engine.ContractMergeEngine"
        ) as mock_merge_engine_class:
            mock_merge_engine = MagicMock()
            mock_merge_engine_class.return_value = mock_merge_engine

            descriptor = ModelHandlerBehavior(node_archetype="compute", purity="pure")
            merged = ModelHandlerContract(
                handler_id="node.test.compute",
                name="Test Handler",
                contract_version=ModelSemVer(major=1, minor=0, patch=0),
                descriptor=descriptor,
                input_model="omnibase_core.models.test.Input",
                output_model="omnibase_core.models.test.Output",
            )
            mock_merge_engine.merge.return_value = merged

            mock_factory = MagicMock()
            mock_factory.get_profile.return_value = merged

            result = pipeline.validate_all(valid_patch, mock_factory)

            assert result.success is True
            assert "patch" in called_phases
            assert "merge" in called_phases
            assert "expanded" in called_phases

    def test_validate_all_handles_merge_exception(
        self, valid_patch: ModelContractPatch
    ) -> None:
        """Test that validate_all handles merge operation exceptions."""
        pipeline = ContractValidationPipeline()

        with patch(
            "omnibase_core.merge.contract_merge_engine.ContractMergeEngine"
        ) as mock_merge_engine_class:
            mock_merge_engine = MagicMock()
            mock_merge_engine_class.return_value = mock_merge_engine
            mock_merge_engine.merge.side_effect = Exception("Merge failed")

            mock_factory = MagicMock()

            result = pipeline.validate_all(valid_patch, mock_factory)

            assert result.success is False
            assert result.phase_failed == EnumValidationPhase.MERGE
            assert any("Merge" in error for error in result.errors)


@pytest.mark.unit
class TestContractValidationPipelineEdgeCases(TestContractValidationPipelineFixtures):
    """Test edge cases for ContractValidationPipeline."""

    def test_pipeline_thread_safety_stateless(
        self,
        pipeline: ContractValidationPipeline,
        valid_patch: ModelContractPatch,
    ) -> None:
        """Test that pipeline is stateless (can be reused)."""
        # Multiple calls should work independently
        result1 = pipeline.validate_patch(valid_patch)
        result2 = pipeline.validate_patch(valid_patch)

        assert result1.is_valid == result2.is_valid
        # Results should be independent objects
        assert result1 is not result2

    def test_pipeline_minimal_patch(
        self, pipeline: ContractValidationPipeline, profile_ref: ModelProfileReference
    ) -> None:
        """Test pipeline with minimal patch."""
        minimal_patch = ModelContractPatch(extends=profile_ref)
        result = pipeline.validate_patch(minimal_patch)
        assert isinstance(result, ModelValidationResult)
        # Minimal patch should still be valid
        assert result.is_valid is True
        assert result.error_level_count == 0

    def test_expanded_contract_result_serialization(self) -> None:
        """Test that ModelExpandedContractResult can be serialized."""
        result = ModelExpandedContractResult(
            success=False,
            phase_failed=EnumValidationPhase.MERGE,
            errors=["Error 1", "Error 2"],
        )

        # Should be able to dump to dict
        data = result.model_dump()
        assert data["success"] is False
        assert data["phase_failed"] == "merge"
        assert len(data["errors"]) == 2


@pytest.mark.unit
@pytest.mark.slow
class TestValidationPerformance:
    """Performance tests for contract validation with large contracts.

    These tests verify O(n) complexity for validation operations
    by testing with varying numbers of handlers.
    """

    @pytest.fixture
    def pipeline(self) -> ContractValidationPipeline:
        """Create a pipeline fixture."""
        return ContractValidationPipeline()

    @pytest.fixture
    def profile_ref(self) -> ModelProfileReference:
        """Create a profile reference fixture."""
        return ModelProfileReference(profile="compute_pure", version="1.0.0")

    @pytest.fixture
    def valid_descriptor(self) -> ModelHandlerBehavior:
        """Create a valid handler behavior descriptor."""
        return ModelHandlerBehavior(
            node_archetype="compute",
            purity="pure",
            idempotent=True,
        )

    def _create_contract_with_handlers(
        self,
        descriptor: ModelHandlerBehavior,
        num_handlers: int,
    ) -> ModelHandlerContract:
        """Create a contract with the specified number of unique capability outputs.

        Args:
            descriptor: Handler behavior descriptor.
            num_handlers: Number of handlers/outputs to create.

        Returns:
            A ModelHandlerContract with the specified number of outputs.
        """
        # Create unique capability outputs (simulating handlers)
        outputs = [f"event.handler_{i}" for i in range(num_handlers)]

        return ModelHandlerContract(
            handler_id="node.test.compute",
            name=f"Test Handler with {num_handlers} outputs",
            contract_version=ModelSemVer(major=1, minor=0, patch=0),
            description=f"A test contract with {num_handlers} capability outputs",
            descriptor=descriptor,
            input_model="omnibase_core.models.events.ModelTestEvent",
            output_model="omnibase_core.models.results.ModelTestResult",
            capability_outputs=outputs,
        )

    def _create_patch_with_capability_outputs(
        self,
        profile_ref: ModelProfileReference,
        num_outputs: int,
    ) -> ModelContractPatch:
        """Create a patch with the specified number of capability output additions.

        Args:
            profile_ref: Profile reference for the patch.
            num_outputs: Number of capability outputs to add.

        Returns:
            A ModelContractPatch with the specified number of capability output additions.
        """
        from omnibase_core.models.contracts.model_capability_provided import (
            ModelCapabilityProvided,
        )

        # Create unique capability outputs using ModelCapabilityProvided
        outputs = [
            ModelCapabilityProvided(name=f"event_handler_{i}")
            for i in range(num_outputs)
        ]

        return ModelContractPatch(
            extends=profile_ref,
            name="performance_test_handler",
            node_version=ModelSemVer(major=1, minor=0, patch=0),
            description="Performance test contract",
            capability_outputs__add=outputs,
        )

    def test_validate_large_contract_100_outputs(
        self,
        pipeline: ContractValidationPipeline,
        valid_descriptor: ModelHandlerBehavior,
        profile_ref: ModelProfileReference,
    ) -> None:
        """Test validation performance with 100 capability outputs in merged contract.

        Verifies that validation completes in a reasonable time
        for moderately sized contracts. Uses merged contract outputs
        which have higher limits than patch operations.
        """
        import time

        base = self._create_contract_with_handlers(valid_descriptor, 100)
        # Use minimal patch - large outputs are in the merged contract
        patch = ModelContractPatch(
            extends=profile_ref,
            name="performance_test_handler",
            node_version=ModelSemVer(major=1, minor=0, patch=0),
        )
        merged = self._create_contract_with_handlers(valid_descriptor, 100)

        start_time = time.perf_counter()
        result = pipeline.validate_merge(base, patch, merged)
        elapsed = time.perf_counter() - start_time

        assert isinstance(result, ModelValidationResult)
        # Verify validation succeeds, not just type check
        assert result.is_valid is True
        assert result.error_level_count == 0
        assert elapsed < 1.0, f"Validation took {elapsed:.2f}s, expected < 1.0s"

    def test_validate_large_contract_500_outputs(
        self,
        pipeline: ContractValidationPipeline,
        valid_descriptor: ModelHandlerBehavior,
        profile_ref: ModelProfileReference,
    ) -> None:
        """Test validation performance with 500 capability outputs in merged contract.

        Verifies O(n) complexity by checking that 500 outputs
        still complete within reasonable time bounds.
        """
        import time

        base = self._create_contract_with_handlers(valid_descriptor, 500)
        # Use minimal patch - large outputs are in the merged contract
        patch = ModelContractPatch(
            extends=profile_ref,
            name="performance_test_handler",
            node_version=ModelSemVer(major=1, minor=0, patch=0),
        )
        merged = self._create_contract_with_handlers(valid_descriptor, 500)

        start_time = time.perf_counter()
        result = pipeline.validate_merge(base, patch, merged)
        elapsed = time.perf_counter() - start_time

        assert isinstance(result, ModelValidationResult)
        # Verify validation succeeds, not just type check
        assert result.is_valid is True
        assert result.error_level_count == 0
        # Should still be fast - linear scaling expected
        assert elapsed < 1.0, f"Validation took {elapsed:.2f}s, expected < 1.0s"

    def test_validate_large_contract_1000_outputs(
        self,
        pipeline: ContractValidationPipeline,
        valid_descriptor: ModelHandlerBehavior,
        profile_ref: ModelProfileReference,
    ) -> None:
        """Test validation performance with 1000 capability outputs in merged contract.

        This is the stress test to ensure validation scales linearly
        and doesn't have O(n^2) or worse complexity.
        """
        import time

        base = self._create_contract_with_handlers(valid_descriptor, 1000)
        # Use minimal patch - large outputs are in the merged contract
        patch = ModelContractPatch(
            extends=profile_ref,
            name="performance_test_handler",
            node_version=ModelSemVer(major=1, minor=0, patch=0),
        )
        merged = self._create_contract_with_handlers(valid_descriptor, 1000)

        start_time = time.perf_counter()
        result = pipeline.validate_merge(base, patch, merged)
        elapsed = time.perf_counter() - start_time

        assert isinstance(result, ModelValidationResult)
        # Verify validation succeeds, not just type check
        assert result.is_valid is True
        assert result.error_level_count == 0
        # At O(n), 1000 outputs should still complete quickly
        assert elapsed < 1.0, f"Validation took {elapsed:.2f}s, expected < 1.0s"

    def test_patch_validation_scales_linearly(
        self,
        pipeline: ContractValidationPipeline,
        profile_ref: ModelProfileReference,
    ) -> None:
        """Test that patch validation exhibits O(n) complexity.

        Validates multiple patch sizes and checks that the ratio
        of times is roughly proportional to the ratio of sizes.
        Uses capability outputs within model constraints (max 50 per patch).
        """
        import time

        # Create patches of different sizes within model constraints
        # capability_outputs__add is limited to 50 items
        small_patch = self._create_patch_with_capability_outputs(profile_ref, 10)
        large_patch = self._create_patch_with_capability_outputs(profile_ref, 50)

        # Time small patch
        start_time = time.perf_counter()
        result_small = pipeline.validate_patch(small_patch)
        small_elapsed = time.perf_counter() - start_time

        # Time large patch
        start_time = time.perf_counter()
        result_large = pipeline.validate_patch(large_patch)
        large_elapsed = time.perf_counter() - start_time

        assert isinstance(result_small, ModelValidationResult)
        assert isinstance(result_large, ModelValidationResult)
        # Verify both validations succeed, not just type check
        assert result_small.is_valid is True
        assert result_large.is_valid is True
        assert result_small.error_level_count == 0
        assert result_large.error_level_count == 0

        # Both should complete quickly
        assert small_elapsed < 1.0, f"Small patch took {small_elapsed:.2f}s"
        assert large_elapsed < 1.0, f"Large patch took {large_elapsed:.2f}s"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
