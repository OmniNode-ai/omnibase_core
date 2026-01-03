# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Tests for ContractValidationPipeline.

Tests all aspects of the contract validation pipeline including:
- validate_patch delegates correctly
- validate_merge delegates correctly
- validate_expanded delegates correctly
- validate_all runs all phases
- Pipeline stops on first critical error
- constraint_validator seam (duck-typed injection)
- ExpandedContractResult model
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
from omnibase_core.validation.contract_patch_validator import ContractPatchValidator
from omnibase_core.validation.contract_validation_pipeline import (
    ContractValidationPipeline,
    ExpandedContractResult,
    ProtocolContractValidationPipeline,
)
from omnibase_core.validation.phases.expanded_validator import ExpandedContractValidator
from omnibase_core.validation.phases.merge_validator import MergeValidator


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
            handler_kind="compute",
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
            version="1.0.0",
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
            version="1.0.0",
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

    def test_validate_patch_returns_validation_result(
        self, pipeline: ContractValidationPipeline, valid_patch: ModelContractPatch
    ) -> None:
        """Test that validate_patch returns ModelValidationResult."""
        result = pipeline.validate_patch(valid_patch)
        assert isinstance(result, ModelValidationResult)
        assert hasattr(result, "is_valid")
        assert hasattr(result, "issues")

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

    def test_validate_merge_returns_validation_result(
        self,
        pipeline: ContractValidationPipeline,
        valid_base: ModelHandlerContract,
        valid_patch: ModelContractPatch,
        valid_merged: ModelHandlerContract,
    ) -> None:
        """Test that validate_merge returns ModelValidationResult."""
        result = pipeline.validate_merge(valid_base, valid_patch, valid_merged)
        assert isinstance(result, ModelValidationResult)

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

    def test_validate_expanded_returns_validation_result(
        self,
        pipeline: ContractValidationPipeline,
        valid_merged: ModelHandlerContract,
    ) -> None:
        """Test that validate_expanded returns ModelValidationResult."""
        result = pipeline.validate_expanded(valid_merged)
        assert isinstance(result, ModelValidationResult)

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
        # Should not crash
        result = pipeline.validate_merge(valid_base, valid_patch, valid_merged)
        assert isinstance(result, ModelValidationResult)


@pytest.mark.unit
class TestExpandedContractResultModel:
    """Tests for ExpandedContractResult model."""

    def test_default_values(self) -> None:
        """Test default values for ExpandedContractResult."""
        result = ExpandedContractResult()
        assert result.success is False
        assert result.contract is None
        assert result.validation_results == {}
        assert result.errors == []
        assert result.phase_failed is None

    def test_success_result(self) -> None:
        """Test successful result creation."""
        descriptor = ModelHandlerBehavior(
            handler_kind="compute",
            purity="pure",
        )
        contract = ModelHandlerContract(
            handler_id="node.test.compute",
            name="Test Handler",
            version="1.0.0",
            descriptor=descriptor,
            input_model="omnibase_core.models.test.Input",
            output_model="omnibase_core.models.test.Output",
        )

        result = ExpandedContractResult(
            success=True,
            contract=contract,
        )

        assert result.success is True
        assert result.contract is not None
        assert result.contract.name == "Test Handler"

    def test_failed_result_with_phase(self) -> None:
        """Test failed result with phase information."""
        result = ExpandedContractResult(
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

        result = ExpandedContractResult(
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
            descriptor = ModelHandlerBehavior(handler_kind="compute", purity="pure")
            merged = ModelHandlerContract(
                handler_id="node.test.compute",
                name="Merged Handler",
                version="1.0.0",
                descriptor=descriptor,
                input_model="omnibase_core.models.test.Input",
                output_model="omnibase_core.models.test.Output",
            )
            mock_merge_engine.merge.return_value = merged

            # Mock factory.get_profile to return a valid base
            mock_factory.get_profile.return_value = merged

            result = pipeline.validate_all(valid_patch, mock_factory)
            assert isinstance(result, ExpandedContractResult)

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
        # Merge should not be in results since we stopped at patch
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

            descriptor = ModelHandlerBehavior(handler_kind="compute", purity="pure")
            merged = ModelHandlerContract(
                handler_id="node.test.compute",
                name="Test Handler",
                version="1.0.0",
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

            descriptor = ModelHandlerBehavior(handler_kind="compute", purity="pure")
            merged = ModelHandlerContract(
                handler_id="node.test.compute",
                name="Test Handler",
                version="1.0.0",
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

    def test_expanded_contract_result_serialization(self) -> None:
        """Test that ExpandedContractResult can be serialized."""
        result = ExpandedContractResult(
            success=False,
            phase_failed=EnumValidationPhase.MERGE,
            errors=["Error 1", "Error 2"],
        )

        # Should be able to dump to dict
        data = result.model_dump()
        assert data["success"] is False
        assert data["phase_failed"] == "merge"
        assert len(data["errors"]) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
