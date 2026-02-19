# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Integration tests for contract-driven NodeCompute pipeline execution.

Tests complete pipeline scenarios including multi-step execution,
error propagation, and complex data flows.

These tests verify:
1. Full pipeline execution with multiple chained steps
2. Error propagation and abort-on-first-failure semantics
3. Mapping steps referencing multiple prior step outputs
4. Disabled step handling
5. Large data handling performance baseline
"""

import concurrent.futures
from uuid import uuid4

import pytest

from omnibase_core.enums.enum_case_mode import EnumCaseMode
from omnibase_core.enums.enum_compute_step_type import EnumComputeStepType
from omnibase_core.enums.enum_regex_flag import EnumRegexFlag
from omnibase_core.enums.enum_transformation_type import EnumTransformationType
from omnibase_core.enums.enum_trim_mode import EnumTrimMode
from omnibase_core.enums.enum_unicode_form import EnumUnicodeForm
from omnibase_core.models.compute.model_compute_execution_context import (
    ModelComputeExecutionContext,
)
from omnibase_core.models.contracts.subcontracts.model_compute_pipeline_step import (
    ModelComputePipelineStep,
)
from omnibase_core.models.contracts.subcontracts.model_compute_subcontract import (
    ModelComputeSubcontract,
)
from omnibase_core.models.transformations.model_mapping_config import ModelMappingConfig
from omnibase_core.models.transformations.model_transform_case_config import (
    ModelTransformCaseConfig,
)
from omnibase_core.models.transformations.model_transform_regex_config import (
    ModelTransformRegexConfig,
)
from omnibase_core.models.transformations.model_transform_trim_config import (
    ModelTransformTrimConfig,
)
from omnibase_core.models.transformations.model_transform_unicode_config import (
    ModelTransformUnicodeConfig,
)
from omnibase_core.models.transformations.model_validation_step_config import (
    ModelValidationStepConfig,
)
from omnibase_core.utils.util_compute_executor import execute_compute_pipeline
from tests.integration.conftest import ComputeContextFactory


@pytest.mark.integration
@pytest.mark.timeout(60)
class TestComputePipelineIntegration:
    """Integration tests for complete pipeline scenarios.

    Note: 60-second timeout protects against pipeline execution hangs.
    Uses compute_execution_context_factory fixture for context creation.
    """

    def test_multi_step_pipeline_execution(
        self, compute_execution_context_factory: ComputeContextFactory
    ) -> None:
        """Test pipeline with multiple transformation steps chained together.

        Verifies that:
        - Multiple steps execute in sequence
        - Each step receives the output of the previous step
        - Final output reflects all transformations
        - All steps are tracked in steps_executed
        """
        # Create a pipeline: TRIM -> CASE_CONVERSION -> IDENTITY
        contract = ModelComputeSubcontract(
            operation_name="multi_step_test",
            operation_version={"major": 1, "minor": 0, "patch": 0},
            pipeline=[
                ModelComputePipelineStep(
                    step_name="trim_input",
                    step_type=EnumComputeStepType.TRANSFORMATION,
                    transformation_type=EnumTransformationType.TRIM,
                    transformation_config=ModelTransformTrimConfig(
                        mode=EnumTrimMode.BOTH
                    ),
                ),
                ModelComputePipelineStep(
                    step_name="uppercase",
                    step_type=EnumComputeStepType.TRANSFORMATION,
                    transformation_type=EnumTransformationType.CASE_CONVERSION,
                    transformation_config=ModelTransformCaseConfig(
                        mode=EnumCaseMode.UPPER
                    ),
                ),
                ModelComputePipelineStep(
                    step_name="identity_pass",
                    step_type=EnumComputeStepType.TRANSFORMATION,
                    transformation_type=EnumTransformationType.IDENTITY,
                ),
            ],
        )

        result = execute_compute_pipeline(
            contract=contract,
            input_data="  hello world  ",
            context=compute_execution_context_factory(),
        )

        assert result.success is True
        assert result.output == "HELLO WORLD"
        assert len(result.steps_executed) == 3
        assert result.steps_executed == ["trim_input", "uppercase", "identity_pass"]
        assert result.error_step is None
        assert result.error_message is None

    def test_error_propagation_aborts_pipeline(
        self, compute_execution_context_factory: ComputeContextFactory
    ) -> None:
        """Test that failure in middle step aborts the pipeline.

        Verifies abort-on-first-failure semantics:
        - Step 1 (IDENTITY) succeeds with integer input
        - Step 2 (TRIM) fails because it requires string input
        - Step 3 never executes
        - Pipeline reports failure with correct error step
        """
        # Create a pipeline where step 2 will fail (integer input to TRIM)
        contract = ModelComputeSubcontract(
            operation_name="error_test",
            operation_version={"major": 1, "minor": 0, "patch": 0},
            pipeline=[
                ModelComputePipelineStep(
                    step_name="step1_identity",
                    step_type=EnumComputeStepType.TRANSFORMATION,
                    transformation_type=EnumTransformationType.IDENTITY,
                ),
                # This will fail because step1 output is not a string
                ModelComputePipelineStep(
                    step_name="step2_trim_fails",
                    step_type=EnumComputeStepType.TRANSFORMATION,
                    transformation_type=EnumTransformationType.TRIM,
                    transformation_config=ModelTransformTrimConfig(
                        mode=EnumTrimMode.BOTH
                    ),
                ),
                ModelComputePipelineStep(
                    step_name="step3_never_reached",
                    step_type=EnumComputeStepType.TRANSFORMATION,
                    transformation_type=EnumTransformationType.IDENTITY,
                ),
            ],
        )

        # Pass integer to cause TRIM to fail (TRIM requires string input)
        result = execute_compute_pipeline(
            contract=contract,
            input_data=12345,
            context=compute_execution_context_factory(),
        )

        assert result.success is False
        assert result.error_step == "step2_trim_fails"
        # step2_trim_fails is added to steps_executed even though it failed
        assert "step2_trim_fails" in result.steps_executed
        # step3 should never be executed
        assert "step3_never_reached" not in result.steps_executed
        assert result.error_message is not None
        assert (
            "string" in result.error_message.lower()
            or "str" in result.error_message.lower()
        )

    def test_mapping_references_multiple_prior_steps(
        self, compute_execution_context_factory: ComputeContextFactory
    ) -> None:
        """Test mapping step that references outputs from multiple prior steps.

        Verifies that:
        - Mapping can reference $.input for original input
        - Mapping can reference $.steps.<name>.output for step outputs
        - Multiple fields can be constructed from different sources
        """
        contract = ModelComputeSubcontract(
            operation_name="mapping_test",
            operation_version={"major": 1, "minor": 0, "patch": 0},
            pipeline=[
                ModelComputePipelineStep(
                    step_name="uppercase_name",
                    step_type=EnumComputeStepType.TRANSFORMATION,
                    transformation_type=EnumTransformationType.CASE_CONVERSION,
                    transformation_config=ModelTransformCaseConfig(
                        mode=EnumCaseMode.UPPER
                    ),
                ),
                # This step creates a mapping from prior step and input
                ModelComputePipelineStep(
                    step_name="combine_results",
                    step_type=EnumComputeStepType.MAPPING,
                    mapping_config=ModelMappingConfig(
                        field_mappings={
                            "original": "$.input",
                            "transformed": "$.steps.uppercase_name.output",
                        }
                    ),
                ),
            ],
        )

        result = execute_compute_pipeline(
            contract=contract,
            input_data="hello",
            context=compute_execution_context_factory(),
        )

        assert result.success is True
        assert isinstance(result.output, dict)
        assert result.output["original"] == "hello"
        assert result.output["transformed"] == "HELLO"

    def test_disabled_steps_are_skipped(
        self, compute_execution_context_factory: ComputeContextFactory
    ) -> None:
        """Test that disabled steps are properly skipped.

        Verifies that:
        - Disabled steps don't execute
        - Disabled steps don't appear in steps_executed
        - Pipeline continues past disabled steps
        - Output reflects only enabled transformations
        """
        contract = ModelComputeSubcontract(
            operation_name="disabled_step_test",
            operation_version={"major": 1, "minor": 0, "patch": 0},
            pipeline=[
                ModelComputePipelineStep(
                    step_name="step1",
                    step_type=EnumComputeStepType.TRANSFORMATION,
                    transformation_type=EnumTransformationType.CASE_CONVERSION,
                    transformation_config=ModelTransformCaseConfig(
                        mode=EnumCaseMode.UPPER
                    ),
                ),
                ModelComputePipelineStep(
                    step_name="step2_disabled",
                    step_type=EnumComputeStepType.TRANSFORMATION,
                    transformation_type=EnumTransformationType.CASE_CONVERSION,
                    transformation_config=ModelTransformCaseConfig(
                        mode=EnumCaseMode.LOWER
                    ),
                    enabled=False,
                ),
                ModelComputePipelineStep(
                    step_name="step3",
                    step_type=EnumComputeStepType.TRANSFORMATION,
                    transformation_type=EnumTransformationType.IDENTITY,
                ),
            ],
        )

        result = execute_compute_pipeline(
            contract=contract,
            input_data="Hello",
            context=compute_execution_context_factory(),
        )

        assert result.success is True
        assert result.output == "HELLO"  # Not "hello" - step2 was skipped
        assert "step2_disabled" not in result.steps_executed
        assert result.steps_executed == ["step1", "step3"]

    def test_complex_pipeline_with_regex_and_unicode(
        self, compute_execution_context_factory: ComputeContextFactory
    ) -> None:
        """Test complex pipeline with regex and unicode normalization.

        Verifies that:
        - Regex transformations work correctly
        - Unicode normalization integrates with other steps
        - Complex multi-step pipelines execute correctly
        """
        contract = ModelComputeSubcontract(
            operation_name="complex_pipeline",
            operation_version={"major": 1, "minor": 0, "patch": 0},
            pipeline=[
                # Step 1: Normalize multiple spaces to single space
                ModelComputePipelineStep(
                    step_name="normalize_spaces",
                    step_type=EnumComputeStepType.TRANSFORMATION,
                    transformation_type=EnumTransformationType.REGEX,
                    transformation_config=ModelTransformRegexConfig(
                        pattern=r"\s+",
                        replacement=" ",
                    ),
                ),
                # Step 2: Trim whitespace
                ModelComputePipelineStep(
                    step_name="trim",
                    step_type=EnumComputeStepType.TRANSFORMATION,
                    transformation_type=EnumTransformationType.TRIM,
                    transformation_config=ModelTransformTrimConfig(
                        mode=EnumTrimMode.BOTH
                    ),
                ),
                # Step 3: Convert to uppercase
                ModelComputePipelineStep(
                    step_name="uppercase",
                    step_type=EnumComputeStepType.TRANSFORMATION,
                    transformation_type=EnumTransformationType.CASE_CONVERSION,
                    transformation_config=ModelTransformCaseConfig(
                        mode=EnumCaseMode.UPPER
                    ),
                ),
            ],
        )

        result = execute_compute_pipeline(
            contract=contract,
            input_data="  hello    world   test  ",
            context=compute_execution_context_factory(),
        )

        assert result.success is True
        assert result.output == "HELLO WORLD TEST"
        assert len(result.steps_executed) == 3

    def test_mapping_with_nested_input_access(
        self, compute_execution_context_factory: ComputeContextFactory
    ) -> None:
        """Test mapping step accessing nested fields in input.

        Verifies that:
        - Mapping can access nested fields via $.input.field.subfield
        - Complex input structures are properly traversed
        """
        contract = ModelComputeSubcontract(
            operation_name="nested_mapping_test",
            operation_version={"major": 1, "minor": 0, "patch": 0},
            pipeline=[
                ModelComputePipelineStep(
                    step_name="extract_fields",
                    step_type=EnumComputeStepType.MAPPING,
                    mapping_config=ModelMappingConfig(
                        field_mappings={
                            "user_name": "$.input.user.name",
                            "user_email": "$.input.user.email",
                            "full_input": "$.input",
                        }
                    ),
                ),
            ],
        )

        input_data = {
            "user": {
                "name": "John Doe",
                "email": "john@example.com",
            },
            "metadata": {
                "created": "2024-01-01",
            },
        }

        result = execute_compute_pipeline(
            contract=contract,
            input_data=input_data,
            context=compute_execution_context_factory(),
        )

        assert result.success is True
        assert result.output["user_name"] == "John Doe"
        assert result.output["user_email"] == "john@example.com"
        assert result.output["full_input"] == input_data

    def test_chained_transformations_with_intermediate_mapping(
        self, compute_execution_context_factory: ComputeContextFactory
    ) -> None:
        """Test pipeline with transformations and intermediate mapping.

        Verifies complex data flow:
        1. Transform input to uppercase
        2. Transform input to lowercase (on original input via mapping)
        3. Combine both in final mapping
        """
        contract = ModelComputeSubcontract(
            operation_name="chained_with_mapping",
            operation_version={"major": 1, "minor": 0, "patch": 0},
            pipeline=[
                # Step 1: Uppercase transformation
                ModelComputePipelineStep(
                    step_name="to_upper",
                    step_type=EnumComputeStepType.TRANSFORMATION,
                    transformation_type=EnumTransformationType.CASE_CONVERSION,
                    transformation_config=ModelTransformCaseConfig(
                        mode=EnumCaseMode.UPPER
                    ),
                ),
                # Step 2: Create intermediate mapping preserving original
                ModelComputePipelineStep(
                    step_name="preserve_both",
                    step_type=EnumComputeStepType.MAPPING,
                    mapping_config=ModelMappingConfig(
                        field_mappings={
                            "upper_version": "$.steps.to_upper.output",
                            "original": "$.input",
                        }
                    ),
                ),
            ],
        )

        result = execute_compute_pipeline(
            contract=contract,
            input_data="Hello World",
            context=compute_execution_context_factory(),
        )

        assert result.success is True
        assert result.output["upper_version"] == "HELLO WORLD"
        assert result.output["original"] == "Hello World"

    def test_pipeline_timing_is_tracked(
        self, compute_execution_context_factory: ComputeContextFactory
    ) -> None:
        """Test that pipeline timing information is properly tracked.

        Verifies that:
        - Total processing time is recorded
        - Individual step durations are recorded
        - All timing values are non-negative
        """
        contract = ModelComputeSubcontract(
            operation_name="timing_test",
            operation_version={"major": 1, "minor": 0, "patch": 0},
            pipeline=[
                ModelComputePipelineStep(
                    step_name="step1",
                    step_type=EnumComputeStepType.TRANSFORMATION,
                    transformation_type=EnumTransformationType.CASE_CONVERSION,
                    transformation_config=ModelTransformCaseConfig(
                        mode=EnumCaseMode.UPPER
                    ),
                ),
                ModelComputePipelineStep(
                    step_name="step2",
                    step_type=EnumComputeStepType.TRANSFORMATION,
                    transformation_type=EnumTransformationType.TRIM,
                    transformation_config=ModelTransformTrimConfig(
                        mode=EnumTrimMode.BOTH
                    ),
                ),
            ],
        )

        result = execute_compute_pipeline(
            contract=contract,
            input_data="  hello  ",
            context=compute_execution_context_factory(),
        )

        assert result.success is True
        assert result.processing_time_ms >= 0

        # Check individual step timings
        for step_name in ["step1", "step2"]:
            step_result = result.step_results[step_name]
            assert step_result.metadata.duration_ms >= 0

    def test_empty_pipeline_returns_input_unchanged(
        self, compute_execution_context_factory: ComputeContextFactory
    ) -> None:
        """Test that empty pipeline returns input unchanged."""
        contract = ModelComputeSubcontract(
            operation_name="empty_pipeline",
            operation_version={"major": 1, "minor": 0, "patch": 0},
            pipeline=[],
        )

        input_data = {"key": "value", "nested": {"data": 123}}

        result = execute_compute_pipeline(
            contract=contract,
            input_data=input_data,
            context=compute_execution_context_factory(),
        )

        assert result.success is True
        assert result.output == input_data
        assert result.steps_executed == []

    def test_regex_with_flags(
        self, compute_execution_context_factory: ComputeContextFactory
    ) -> None:
        """Test regex transformation with IGNORECASE flag.

        Verifies that:
        - IGNORECASE flag replaces all case variations
        - Exactly 3 replacements occur (HELLO, hello, HeLLo)
        """
        contract = ModelComputeSubcontract(
            operation_name="regex_flags_test",
            operation_version={"major": 1, "minor": 0, "patch": 0},
            pipeline=[
                ModelComputePipelineStep(
                    step_name="case_insensitive_replace",
                    step_type=EnumComputeStepType.TRANSFORMATION,
                    transformation_type=EnumTransformationType.REGEX,
                    transformation_config=ModelTransformRegexConfig(
                        pattern=r"hello",
                        replacement="hi",
                        flags=[EnumRegexFlag.IGNORECASE],
                    ),
                ),
            ],
        )

        input_data = "HELLO World, hello friend, HeLLo there"
        result = execute_compute_pipeline(
            contract=contract,
            input_data=input_data,
            context=compute_execution_context_factory(),
        )

        assert result.success is True
        # Verify exact output - all 3 case variations replaced
        assert result.output == "hi World, hi friend, hi there"
        # Verify count: input has 3 "hello" variants, output has 3 "hi"
        assert input_data.lower().count("hello") == 3
        assert result.output.count("hi") == 3

    def test_unicode_normalization_in_pipeline(
        self, compute_execution_context_factory: ComputeContextFactory
    ) -> None:
        """Test unicode normalization as part of a pipeline.

        Verifies that:
        - Unicode normalization works correctly
        - Can be combined with other transformations
        """
        contract = ModelComputeSubcontract(
            operation_name="unicode_pipeline",
            operation_version={"major": 1, "minor": 0, "patch": 0},
            pipeline=[
                ModelComputePipelineStep(
                    step_name="normalize",
                    step_type=EnumComputeStepType.TRANSFORMATION,
                    transformation_type=EnumTransformationType.NORMALIZE_UNICODE,
                    transformation_config=ModelTransformUnicodeConfig(
                        form=EnumUnicodeForm.NFC
                    ),
                ),
                ModelComputePipelineStep(
                    step_name="uppercase",
                    step_type=EnumComputeStepType.TRANSFORMATION,
                    transformation_type=EnumTransformationType.CASE_CONVERSION,
                    transformation_config=ModelTransformCaseConfig(
                        mode=EnumCaseMode.UPPER
                    ),
                ),
            ],
        )

        # Use decomposed form (e + combining accent)
        decomposed = "cafe\u0301"  # cafe with combining acute accent on e

        result = execute_compute_pipeline(
            contract=contract,
            input_data=decomposed,
            context=compute_execution_context_factory(),
        )

        assert result.success is True
        # Should be normalized and uppercased
        assert result.output == "CAF\xc9"  # CAFE with composed E-acute

    @pytest.mark.slow
    def test_large_data_performance_baseline(
        self, compute_execution_context_factory: ComputeContextFactory
    ) -> None:
        """Test pipeline performance with larger data sets.

        Verifies that:
        - Pipeline handles large inputs without issues
        - Processing completes in reasonable time
        - Output is correct for large data
        """
        # Create a simple pipeline
        contract = ModelComputeSubcontract(
            operation_name="performance_test",
            operation_version={"major": 1, "minor": 0, "patch": 0},
            pipeline=[
                ModelComputePipelineStep(
                    step_name="trim",
                    step_type=EnumComputeStepType.TRANSFORMATION,
                    transformation_type=EnumTransformationType.TRIM,
                    transformation_config=ModelTransformTrimConfig(
                        mode=EnumTrimMode.BOTH
                    ),
                ),
                ModelComputePipelineStep(
                    step_name="uppercase",
                    step_type=EnumComputeStepType.TRANSFORMATION,
                    transformation_type=EnumTransformationType.CASE_CONVERSION,
                    transformation_config=ModelTransformCaseConfig(
                        mode=EnumCaseMode.UPPER
                    ),
                ),
            ],
        )

        # Generate large input (100KB of text)
        large_input = "  " + "a" * 100000 + "  "

        result = execute_compute_pipeline(
            contract=contract,
            input_data=large_input,
            context=compute_execution_context_factory(),
        )

        assert result.success is True
        assert len(result.output) == 100000
        assert result.output == "A" * 100000
        # Performance baseline: should complete in reasonable time (under 1 second)
        assert result.processing_time_ms < 1000

    @pytest.mark.slow
    def test_many_steps_pipeline(
        self, compute_execution_context_factory: ComputeContextFactory
    ) -> None:
        """Test pipeline with many steps.

        Verifies that:
        - Pipeline can handle many sequential steps
        - All steps are tracked correctly
        - Performance remains reasonable
        """
        # Create a pipeline with many identity steps
        steps = []
        for i in range(50):
            steps.append(
                ModelComputePipelineStep(
                    step_name=f"step_{i:02d}",
                    step_type=EnumComputeStepType.TRANSFORMATION,
                    transformation_type=EnumTransformationType.IDENTITY,
                )
            )

        # Add a final transformation to verify data flows through
        steps.append(
            ModelComputePipelineStep(
                step_name="final_uppercase",
                step_type=EnumComputeStepType.TRANSFORMATION,
                transformation_type=EnumTransformationType.CASE_CONVERSION,
                transformation_config=ModelTransformCaseConfig(mode=EnumCaseMode.UPPER),
            )
        )

        contract = ModelComputeSubcontract(
            operation_name="many_steps_test",
            operation_version={"major": 1, "minor": 0, "patch": 0},
            pipeline=steps,
        )

        result = execute_compute_pipeline(
            contract=contract,
            input_data="hello world",
            context=compute_execution_context_factory(),
        )

        assert result.success is True
        assert result.output == "HELLO WORLD"
        assert len(result.steps_executed) == 51
        # Performance: should complete quickly despite many steps
        assert result.processing_time_ms < 500


@pytest.mark.integration
@pytest.mark.timeout(60)
class TestComputePipelineErrorScenarios:
    """Integration tests for error handling scenarios.

    Note: 60-second timeout protects against pipeline execution hangs.
    Uses compute_execution_context_factory fixture for context creation.
    """

    def test_invalid_regex_pattern_fails_gracefully(
        self, compute_execution_context_factory: ComputeContextFactory
    ) -> None:
        """Test that invalid regex pattern causes proper failure."""
        contract = ModelComputeSubcontract(
            operation_name="invalid_regex",
            operation_version={"major": 1, "minor": 0, "patch": 0},
            pipeline=[
                ModelComputePipelineStep(
                    step_name="bad_regex",
                    step_type=EnumComputeStepType.TRANSFORMATION,
                    transformation_type=EnumTransformationType.REGEX,
                    transformation_config=ModelTransformRegexConfig(
                        pattern=r"[invalid",  # Unclosed bracket
                        replacement="x",
                    ),
                ),
            ],
        )

        result = execute_compute_pipeline(
            contract=contract,
            input_data="test input",
            context=compute_execution_context_factory(),
        )

        assert result.success is False
        assert result.error_step == "bad_regex"
        assert result.error_message is not None

    def test_missing_mapping_path_fails(
        self, compute_execution_context_factory: ComputeContextFactory
    ) -> None:
        """Test that referencing non-existent path in mapping fails."""
        contract = ModelComputeSubcontract(
            operation_name="missing_path",
            operation_version={"major": 1, "minor": 0, "patch": 0},
            pipeline=[
                ModelComputePipelineStep(
                    step_name="bad_mapping",
                    step_type=EnumComputeStepType.MAPPING,
                    mapping_config=ModelMappingConfig(
                        field_mappings={
                            "missing": "$.input.nonexistent.field",
                        }
                    ),
                ),
            ],
        )

        result = execute_compute_pipeline(
            contract=contract,
            input_data={"actual": "data"},
            context=compute_execution_context_factory(),
        )

        assert result.success is False
        assert result.error_step == "bad_mapping"
        assert result.error_message is not None

    def test_referencing_nonexistent_step_fails(
        self, compute_execution_context_factory: ComputeContextFactory
    ) -> None:
        """Test that referencing non-existent step in mapping fails."""
        contract = ModelComputeSubcontract(
            operation_name="missing_step",
            operation_version={"major": 1, "minor": 0, "patch": 0},
            pipeline=[
                ModelComputePipelineStep(
                    step_name="bad_mapping",
                    step_type=EnumComputeStepType.MAPPING,
                    mapping_config=ModelMappingConfig(
                        field_mappings={
                            "missing": "$.steps.nonexistent_step.output",
                        }
                    ),
                ),
            ],
        )

        result = execute_compute_pipeline(
            contract=contract,
            input_data="test",
            context=compute_execution_context_factory(),
        )

        assert result.success is False
        assert result.error_step == "bad_mapping"
        assert (
            "nonexistent_step" in result.error_message
            or "not found" in result.error_message.lower()
        )

    def test_type_mismatch_in_middle_step(
        self, compute_execution_context_factory: ComputeContextFactory
    ) -> None:
        """Test that type mismatch in middle of pipeline aborts correctly."""
        contract = ModelComputeSubcontract(
            operation_name="type_mismatch",
            operation_version={"major": 1, "minor": 0, "patch": 0},
            pipeline=[
                # Step 1: Create a mapping (outputs dict)
                ModelComputePipelineStep(
                    step_name="create_mapping",
                    step_type=EnumComputeStepType.MAPPING,
                    mapping_config=ModelMappingConfig(
                        field_mappings={
                            "value": "$.input",
                        }
                    ),
                ),
                # Step 2: Try to uppercase (expects string, gets dict)
                ModelComputePipelineStep(
                    step_name="uppercase_fails",
                    step_type=EnumComputeStepType.TRANSFORMATION,
                    transformation_type=EnumTransformationType.CASE_CONVERSION,
                    transformation_config=ModelTransformCaseConfig(
                        mode=EnumCaseMode.UPPER
                    ),
                ),
                # Step 3: Should never be reached
                ModelComputePipelineStep(
                    step_name="never_reached",
                    step_type=EnumComputeStepType.TRANSFORMATION,
                    transformation_type=EnumTransformationType.IDENTITY,
                ),
            ],
        )

        result = execute_compute_pipeline(
            contract=contract,
            input_data="test input",
            context=compute_execution_context_factory(),
        )

        assert result.success is False
        assert result.error_step == "uppercase_fails"
        assert "never_reached" not in result.steps_executed


@pytest.mark.integration
@pytest.mark.timeout(60)
class TestComputePipelineContextTracking:
    """Integration tests for context and correlation ID tracking.

    Note: 60-second timeout protects against pipeline execution hangs.
    """

    def test_context_ids_are_preserved(
        self, compute_execution_context_factory: ComputeContextFactory
    ) -> None:
        """Test that operation and correlation IDs are available in context."""
        operation_id = uuid4()
        correlation_id = uuid4()

        context = ModelComputeExecutionContext(
            operation_id=operation_id,
            correlation_id=correlation_id,
            node_id="test-node-001",
        )

        contract = ModelComputeSubcontract(
            operation_name="context_test",
            operation_version={"major": 1, "minor": 0, "patch": 0},
            pipeline=[
                ModelComputePipelineStep(
                    step_name="identity",
                    step_type=EnumComputeStepType.TRANSFORMATION,
                    transformation_type=EnumTransformationType.IDENTITY,
                ),
            ],
        )

        result = execute_compute_pipeline(
            contract=contract,
            input_data="test",
            context=context,
        )

        assert result.success is True
        # Context should be passed through (though we can't directly inspect it
        # from the result, we verify the pipeline executed successfully with it)

    def test_context_without_correlation_id(
        self, compute_execution_context_factory: ComputeContextFactory
    ) -> None:
        """Test that context works without optional correlation ID."""
        context = ModelComputeExecutionContext(
            operation_id=uuid4(),
            # correlation_id is optional
        )

        contract = ModelComputeSubcontract(
            operation_name="minimal_context_test",
            operation_version={"major": 1, "minor": 0, "patch": 0},
            pipeline=[
                ModelComputePipelineStep(
                    step_name="identity",
                    step_type=EnumComputeStepType.TRANSFORMATION,
                    transformation_type=EnumTransformationType.IDENTITY,
                ),
            ],
        )

        result = execute_compute_pipeline(
            contract=contract,
            input_data="test",
            context=context,
        )

        assert result.success is True


@pytest.mark.integration
@pytest.mark.timeout(60)
class TestComputePipelineSingleStepScenarios:
    """Integration tests for single-step pipeline edge cases.

    Note: 60-second timeout protects against pipeline execution hangs.
    Uses compute_execution_context_factory fixture for context creation.
    """

    def test_single_transformation_step(
        self, compute_execution_context_factory: ComputeContextFactory
    ) -> None:
        """Test pipeline with exactly one transformation step.

        Verifies that:
        - Single step executes correctly
        - Output reflects the transformation
        - Steps executed list contains exactly one step
        """
        contract = ModelComputeSubcontract(
            operation_name="single_step_test",
            operation_version={"major": 1, "minor": 0, "patch": 0},
            pipeline=[
                ModelComputePipelineStep(
                    step_name="only_step",
                    step_type=EnumComputeStepType.TRANSFORMATION,
                    transformation_type=EnumTransformationType.CASE_CONVERSION,
                    transformation_config=ModelTransformCaseConfig(
                        mode=EnumCaseMode.UPPER
                    ),
                ),
            ],
        )

        result = execute_compute_pipeline(
            contract=contract,
            input_data="hello",
            context=compute_execution_context_factory(),
        )

        assert result.success is True
        assert result.output == "HELLO"
        assert len(result.steps_executed) == 1
        assert result.steps_executed == ["only_step"]
        assert "only_step" in result.step_results

    def test_single_mapping_step(
        self, compute_execution_context_factory: ComputeContextFactory
    ) -> None:
        """Test pipeline with exactly one mapping step.

        Verifies that:
        - Mapping step can access input directly
        - Single mapping produces correct output structure
        """
        contract = ModelComputeSubcontract(
            operation_name="single_mapping_test",
            operation_version={"major": 1, "minor": 0, "patch": 0},
            pipeline=[
                ModelComputePipelineStep(
                    step_name="only_mapping",
                    step_type=EnumComputeStepType.MAPPING,
                    mapping_config=ModelMappingConfig(
                        field_mappings={
                            "wrapped_input": "$.input",
                            "user_name": "$.input.user.name",
                        }
                    ),
                ),
            ],
        )

        input_data = {"user": {"name": "Alice", "age": 30}}

        result = execute_compute_pipeline(
            contract=contract,
            input_data=input_data,
            context=compute_execution_context_factory(),
        )

        assert result.success is True
        assert result.output["wrapped_input"] == input_data
        assert result.output["user_name"] == "Alice"
        assert len(result.steps_executed) == 1

    def test_single_step_failure(
        self, compute_execution_context_factory: ComputeContextFactory
    ) -> None:
        """Test pipeline with single failing step.

        Verifies that:
        - Error is properly captured
        - Error step is identified
        - Steps executed contains the failed step
        """
        contract = ModelComputeSubcontract(
            operation_name="single_fail_test",
            operation_version={"major": 1, "minor": 0, "patch": 0},
            pipeline=[
                ModelComputePipelineStep(
                    step_name="failing_step",
                    step_type=EnumComputeStepType.TRANSFORMATION,
                    transformation_type=EnumTransformationType.TRIM,
                    transformation_config=ModelTransformTrimConfig(
                        mode=EnumTrimMode.BOTH
                    ),
                ),
            ],
        )

        # Integer input will fail TRIM (requires string)
        result = execute_compute_pipeline(
            contract=contract,
            input_data=12345,
            context=compute_execution_context_factory(),
        )

        assert result.success is False
        assert result.error_step == "failing_step"
        assert "failing_step" in result.steps_executed
        assert result.error_message is not None


@pytest.mark.integration
@pytest.mark.timeout(60)
class TestComputePipelineStepResultAccumulation:
    """Integration tests for step result accumulation and field mapping across steps.

    Note: 60-second timeout protects against pipeline execution hangs.
    Uses compute_execution_context_factory fixture for context creation.
    """

    def test_step_results_accumulate_correctly(
        self, compute_execution_context_factory: ComputeContextFactory
    ) -> None:
        """Test that all step results are accumulated and accessible.

        Verifies that:
        - Each step result is stored with correct step_name key
        - Step outputs are preserved correctly
        - Success flags are accurate per step
        - Timing metadata is captured for each step
        """
        contract = ModelComputeSubcontract(
            operation_name="accumulation_test",
            operation_version={"major": 1, "minor": 0, "patch": 0},
            pipeline=[
                ModelComputePipelineStep(
                    step_name="step_trim",
                    step_type=EnumComputeStepType.TRANSFORMATION,
                    transformation_type=EnumTransformationType.TRIM,
                    transformation_config=ModelTransformTrimConfig(
                        mode=EnumTrimMode.BOTH
                    ),
                ),
                ModelComputePipelineStep(
                    step_name="step_upper",
                    step_type=EnumComputeStepType.TRANSFORMATION,
                    transformation_type=EnumTransformationType.CASE_CONVERSION,
                    transformation_config=ModelTransformCaseConfig(
                        mode=EnumCaseMode.UPPER
                    ),
                ),
                ModelComputePipelineStep(
                    step_name="step_identity",
                    step_type=EnumComputeStepType.TRANSFORMATION,
                    transformation_type=EnumTransformationType.IDENTITY,
                ),
            ],
        )

        result = execute_compute_pipeline(
            contract=contract,
            input_data="  hello world  ",
            context=compute_execution_context_factory(),
        )

        assert result.success is True
        assert len(result.step_results) == 3

        # Verify step_trim result
        assert "step_trim" in result.step_results
        trim_result = result.step_results["step_trim"]
        assert trim_result.success is True
        assert trim_result.output == "hello world"
        assert trim_result.metadata.duration_ms >= 0

        # Verify step_upper result
        assert "step_upper" in result.step_results
        upper_result = result.step_results["step_upper"]
        assert upper_result.success is True
        assert upper_result.output == "HELLO WORLD"
        assert upper_result.metadata.duration_ms >= 0

        # Verify step_identity result
        assert "step_identity" in result.step_results
        identity_result = result.step_results["step_identity"]
        assert identity_result.success is True
        assert identity_result.output == "HELLO WORLD"
        assert identity_result.metadata.duration_ms >= 0

    def test_mapping_references_all_prior_step_outputs(
        self, compute_execution_context_factory: ComputeContextFactory
    ) -> None:
        """Test mapping step that references outputs from ALL prior steps.

        Verifies that:
        - Mapping can access any prior step's output
        - Original input remains accessible
        - Complex aggregation of multiple step outputs works
        """
        contract = ModelComputeSubcontract(
            operation_name="multi_reference_mapping",
            operation_version={"major": 1, "minor": 0, "patch": 0},
            pipeline=[
                ModelComputePipelineStep(
                    step_name="upper_version",
                    step_type=EnumComputeStepType.TRANSFORMATION,
                    transformation_type=EnumTransformationType.CASE_CONVERSION,
                    transformation_config=ModelTransformCaseConfig(
                        mode=EnumCaseMode.UPPER
                    ),
                ),
                ModelComputePipelineStep(
                    step_name="lower_version",
                    step_type=EnumComputeStepType.TRANSFORMATION,
                    transformation_type=EnumTransformationType.CASE_CONVERSION,
                    transformation_config=ModelTransformCaseConfig(
                        mode=EnumCaseMode.LOWER
                    ),
                    # Note: This operates on upper_version output
                ),
                ModelComputePipelineStep(
                    step_name="aggregate_all",
                    step_type=EnumComputeStepType.MAPPING,
                    mapping_config=ModelMappingConfig(
                        field_mappings={
                            "original": "$.input",
                            "uppercase": "$.steps.upper_version.output",
                            "lowercase": "$.steps.lower_version.output",
                        }
                    ),
                ),
            ],
        )

        result = execute_compute_pipeline(
            contract=contract,
            input_data="Hello World",
            context=compute_execution_context_factory(),
        )

        assert result.success is True
        assert isinstance(result.output, dict)
        assert result.output["original"] == "Hello World"
        assert result.output["uppercase"] == "HELLO WORLD"
        assert result.output["lowercase"] == "hello world"

    def test_sequential_mappings_build_complex_structures(
        self, compute_execution_context_factory: ComputeContextFactory
    ) -> None:
        """Test multiple mapping steps building complex nested structures.

        Verifies that:
        - Mapping output can be used by subsequent steps
        - Nested structures are properly constructed
        - Deep nesting paths work correctly
        """
        contract = ModelComputeSubcontract(
            operation_name="nested_mapping_build",
            operation_version={"major": 1, "minor": 0, "patch": 0},
            pipeline=[
                ModelComputePipelineStep(
                    step_name="first_mapping",
                    step_type=EnumComputeStepType.MAPPING,
                    mapping_config=ModelMappingConfig(
                        field_mappings={
                            "level1_data": "$.input",
                        }
                    ),
                ),
                ModelComputePipelineStep(
                    step_name="second_mapping",
                    step_type=EnumComputeStepType.MAPPING,
                    mapping_config=ModelMappingConfig(
                        field_mappings={
                            "level2_wrapper": "$.steps.first_mapping.output",
                            "original_preserved": "$.input",
                        }
                    ),
                ),
            ],
        )

        input_data = {"name": "test", "value": 42}

        result = execute_compute_pipeline(
            contract=contract,
            input_data=input_data,
            context=compute_execution_context_factory(),
        )

        assert result.success is True
        assert result.output["level2_wrapper"]["level1_data"] == input_data
        assert result.output["original_preserved"] == input_data

    def test_transformation_metadata_tracking(
        self, compute_execution_context_factory: ComputeContextFactory
    ) -> None:
        """Test that transformation type metadata is correctly tracked per step.

        Verifies that:
        - transformation_type is recorded in step metadata
        - Different transformation types are distinguished
        """
        contract = ModelComputeSubcontract(
            operation_name="metadata_tracking_test",
            operation_version={"major": 1, "minor": 0, "patch": 0},
            pipeline=[
                ModelComputePipelineStep(
                    step_name="trim_step",
                    step_type=EnumComputeStepType.TRANSFORMATION,
                    transformation_type=EnumTransformationType.TRIM,
                    transformation_config=ModelTransformTrimConfig(
                        mode=EnumTrimMode.BOTH
                    ),
                ),
                ModelComputePipelineStep(
                    step_name="case_step",
                    step_type=EnumComputeStepType.TRANSFORMATION,
                    transformation_type=EnumTransformationType.CASE_CONVERSION,
                    transformation_config=ModelTransformCaseConfig(
                        mode=EnumCaseMode.UPPER
                    ),
                ),
                ModelComputePipelineStep(
                    step_name="mapping_step",
                    step_type=EnumComputeStepType.MAPPING,
                    mapping_config=ModelMappingConfig(
                        field_mappings={"result": "$.input"}
                    ),
                ),
            ],
        )

        result = execute_compute_pipeline(
            contract=contract,
            input_data="  hello  ",
            context=compute_execution_context_factory(),
        )

        assert result.success is True

        # Verify transformation_type metadata (enum values are lowercase)
        assert result.step_results["trim_step"].metadata.transformation_type == "trim"
        assert (
            result.step_results["case_step"].metadata.transformation_type
            == "case_conversion"
        )
        # Mapping steps don't have transformation_type
        assert result.step_results["mapping_step"].metadata.transformation_type is None


@pytest.mark.integration
@pytest.mark.timeout(60)
class TestComputePipelineAllStepTypes:
    """Integration tests covering all supported step types in various combinations.

    Note: 60-second timeout protects against pipeline execution hangs.
    Uses compute_execution_context_factory fixture for context creation.
    """

    def test_all_transformation_types_in_pipeline(
        self, compute_execution_context_factory: ComputeContextFactory
    ) -> None:
        """Test pipeline using all major transformation types.

        Verifies that:
        - IDENTITY, TRIM, CASE_CONVERSION, REGEX, NORMALIZE_UNICODE all work together
        - Transformations chain correctly
        """
        contract = ModelComputeSubcontract(
            operation_name="all_transforms_test",
            operation_version={"major": 1, "minor": 0, "patch": 0},
            pipeline=[
                # Step 1: Normalize unicode
                ModelComputePipelineStep(
                    step_name="normalize",
                    step_type=EnumComputeStepType.TRANSFORMATION,
                    transformation_type=EnumTransformationType.NORMALIZE_UNICODE,
                    transformation_config=ModelTransformUnicodeConfig(
                        form=EnumUnicodeForm.NFC
                    ),
                ),
                # Step 2: Regex - normalize whitespace
                ModelComputePipelineStep(
                    step_name="regex_normalize",
                    step_type=EnumComputeStepType.TRANSFORMATION,
                    transformation_type=EnumTransformationType.REGEX,
                    transformation_config=ModelTransformRegexConfig(
                        pattern=r"\s+",
                        replacement=" ",
                    ),
                ),
                # Step 3: Trim
                ModelComputePipelineStep(
                    step_name="trim",
                    step_type=EnumComputeStepType.TRANSFORMATION,
                    transformation_type=EnumTransformationType.TRIM,
                    transformation_config=ModelTransformTrimConfig(
                        mode=EnumTrimMode.BOTH
                    ),
                ),
                # Step 4: Case conversion
                ModelComputePipelineStep(
                    step_name="uppercase",
                    step_type=EnumComputeStepType.TRANSFORMATION,
                    transformation_type=EnumTransformationType.CASE_CONVERSION,
                    transformation_config=ModelTransformCaseConfig(
                        mode=EnumCaseMode.UPPER
                    ),
                ),
                # Step 5: Identity (pass-through)
                ModelComputePipelineStep(
                    step_name="final_identity",
                    step_type=EnumComputeStepType.TRANSFORMATION,
                    transformation_type=EnumTransformationType.IDENTITY,
                ),
            ],
        )

        # Input with multiple spaces and trailing whitespace
        result = execute_compute_pipeline(
            contract=contract,
            input_data="  hello    world  ",
            context=compute_execution_context_factory(),
        )

        assert result.success is True
        assert result.output == "HELLO WORLD"
        assert len(result.steps_executed) == 5

    def test_mixed_step_types_transform_and_mapping(
        self, compute_execution_context_factory: ComputeContextFactory
    ) -> None:
        """Test pipeline mixing transformation and mapping steps.

        Verifies correct data flow between different step types.
        """
        contract = ModelComputeSubcontract(
            operation_name="mixed_types_test",
            operation_version={"major": 1, "minor": 0, "patch": 0},
            pipeline=[
                # Transform: uppercase
                ModelComputePipelineStep(
                    step_name="transform_upper",
                    step_type=EnumComputeStepType.TRANSFORMATION,
                    transformation_type=EnumTransformationType.CASE_CONVERSION,
                    transformation_config=ModelTransformCaseConfig(
                        mode=EnumCaseMode.UPPER
                    ),
                ),
                # Mapping: capture transformed and original
                ModelComputePipelineStep(
                    step_name="capture_mapping",
                    step_type=EnumComputeStepType.MAPPING,
                    mapping_config=ModelMappingConfig(
                        field_mappings={
                            "transformed": "$.steps.transform_upper.output",
                            "original": "$.input",
                        }
                    ),
                ),
            ],
        )

        result = execute_compute_pipeline(
            contract=contract,
            input_data="hello",
            context=compute_execution_context_factory(),
        )

        assert result.success is True
        assert result.output["transformed"] == "HELLO"
        assert result.output["original"] == "hello"

    def test_validation_step_passthrough(
        self, compute_execution_context_factory: ComputeContextFactory
    ) -> None:
        """Test validation step in v1.0 (pass-through mode).

        Verifies that:
        - Validation step doesn't modify data in v1.0
        - Pipeline continues after validation
        """
        contract = ModelComputeSubcontract(
            operation_name="validation_passthrough_test",
            operation_version={"major": 1, "minor": 0, "patch": 0},
            pipeline=[
                ModelComputePipelineStep(
                    step_name="validate_input",
                    step_type=EnumComputeStepType.VALIDATION,
                    validation_config=ModelValidationStepConfig(
                        schema_ref="schemas/test_schema.json",
                    ),
                ),
                ModelComputePipelineStep(
                    step_name="final_transform",
                    step_type=EnumComputeStepType.TRANSFORMATION,
                    transformation_type=EnumTransformationType.CASE_CONVERSION,
                    transformation_config=ModelTransformCaseConfig(
                        mode=EnumCaseMode.UPPER
                    ),
                ),
            ],
        )

        result = execute_compute_pipeline(
            contract=contract,
            input_data="hello",
            context=compute_execution_context_factory(),
        )

        assert result.success is True
        assert result.output == "HELLO"
        assert "validate_input" in result.steps_executed


@pytest.mark.integration
@pytest.mark.timeout(120)
class TestComputePipelineConcurrency:
    """Integration tests for concurrent pipeline execution scenarios.

    Note: 120-second timeout allows for concurrent execution overhead.
    Uses compute_execution_context_factory fixture for context creation.
    """

    def test_concurrent_pipeline_executions(
        self, compute_execution_context_factory: ComputeContextFactory
    ) -> None:
        """Test multiple pipeline executions with different inputs concurrently.

        Verifies that:
        - Multiple executions don't interfere with each other
        - Each execution produces correct output for its input
        - No shared state corruption occurs
        """
        contract = ModelComputeSubcontract(
            operation_name="concurrent_test",
            operation_version={"major": 1, "minor": 0, "patch": 0},
            pipeline=[
                ModelComputePipelineStep(
                    step_name="uppercase",
                    step_type=EnumComputeStepType.TRANSFORMATION,
                    transformation_type=EnumTransformationType.CASE_CONVERSION,
                    transformation_config=ModelTransformCaseConfig(
                        mode=EnumCaseMode.UPPER
                    ),
                ),
            ],
        )

        # Define inputs and expected outputs
        test_cases = [
            ("hello", "HELLO"),
            ("world", "WORLD"),
            ("test", "TEST"),
            ("data", "DATA"),
            ("pipeline", "PIPELINE"),
        ]

        def execute_pipeline(
            input_output_pair: tuple[str, str],
        ) -> tuple[bool, str, str]:
            input_data, expected = input_output_pair
            context = compute_execution_context_factory()
            result = execute_compute_pipeline(
                contract=contract,
                input_data=input_data,
                context=context,
            )
            return (result.success, result.output, expected)

        # Execute concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(execute_pipeline, tc) for tc in test_cases]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        # Verify all executions succeeded with correct output
        for success, actual, expected in results:
            assert success is True
            assert actual == expected

    def test_concurrent_different_pipelines(
        self, compute_execution_context_factory: ComputeContextFactory
    ) -> None:
        """Test concurrent execution of different pipeline contracts.

        Verifies that:
        - Different contracts can execute concurrently
        - Each contract produces correct results
        """
        contract_upper = ModelComputeSubcontract(
            operation_name="upper_pipeline",
            operation_version={"major": 1, "minor": 0, "patch": 0},
            pipeline=[
                ModelComputePipelineStep(
                    step_name="uppercase",
                    step_type=EnumComputeStepType.TRANSFORMATION,
                    transformation_type=EnumTransformationType.CASE_CONVERSION,
                    transformation_config=ModelTransformCaseConfig(
                        mode=EnumCaseMode.UPPER
                    ),
                ),
            ],
        )

        contract_lower = ModelComputeSubcontract(
            operation_name="lower_pipeline",
            operation_version={"major": 1, "minor": 0, "patch": 0},
            pipeline=[
                ModelComputePipelineStep(
                    step_name="lowercase",
                    step_type=EnumComputeStepType.TRANSFORMATION,
                    transformation_type=EnumTransformationType.CASE_CONVERSION,
                    transformation_config=ModelTransformCaseConfig(
                        mode=EnumCaseMode.LOWER
                    ),
                ),
            ],
        )

        test_cases = [
            (contract_upper, "hello", "HELLO"),
            (contract_lower, "HELLO", "hello"),
            (contract_upper, "world", "WORLD"),
            (contract_lower, "WORLD", "world"),
        ]

        def execute_with_contract(
            args: tuple[ModelComputeSubcontract, str, str],
        ) -> tuple[bool, str, str]:
            contract, input_data, expected = args
            context = ModelComputeExecutionContext(
                operation_id=uuid4(),
                correlation_id=uuid4(),
            )
            result = execute_compute_pipeline(
                contract=contract,
                input_data=input_data,
                context=context,
            )
            return (result.success, result.output, expected)

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(execute_with_contract, tc) for tc in test_cases]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        for success, actual, expected in results:
            assert success is True
            assert actual == expected


@pytest.mark.integration
@pytest.mark.timeout(60)
class TestComputePipelineEdgeCases:
    """Integration tests for pipeline edge cases and boundary conditions.

    Note: 60-second timeout protects against pipeline execution hangs.
    Uses compute_execution_context_factory fixture for context creation.
    """

    def test_all_disabled_steps_returns_input(
        self, compute_execution_context_factory: ComputeContextFactory
    ) -> None:
        """Test pipeline where all steps are disabled.

        Verifies that:
        - Output equals input when all steps disabled
        - No steps appear in steps_executed
        """
        contract = ModelComputeSubcontract(
            operation_name="all_disabled_test",
            operation_version={"major": 1, "minor": 0, "patch": 0},
            pipeline=[
                ModelComputePipelineStep(
                    step_name="disabled1",
                    step_type=EnumComputeStepType.TRANSFORMATION,
                    transformation_type=EnumTransformationType.CASE_CONVERSION,
                    transformation_config=ModelTransformCaseConfig(
                        mode=EnumCaseMode.UPPER
                    ),
                    enabled=False,
                ),
                ModelComputePipelineStep(
                    step_name="disabled2",
                    step_type=EnumComputeStepType.TRANSFORMATION,
                    transformation_type=EnumTransformationType.TRIM,
                    transformation_config=ModelTransformTrimConfig(
                        mode=EnumTrimMode.BOTH
                    ),
                    enabled=False,
                ),
            ],
        )

        input_data = "  hello  "

        result = execute_compute_pipeline(
            contract=contract,
            input_data=input_data,
            context=compute_execution_context_factory(),
        )

        assert result.success is True
        assert result.output == input_data  # Unchanged
        assert result.steps_executed == []  # No steps executed

    def test_special_characters_in_input(
        self, compute_execution_context_factory: ComputeContextFactory
    ) -> None:
        """Test pipeline handles special characters correctly.

        Verifies that:
        - Unicode characters pass through correctly
        - Special regex characters don't cause issues
        - Newlines and tabs are handled
        """
        contract = ModelComputeSubcontract(
            operation_name="special_chars_test",
            operation_version={"major": 1, "minor": 0, "patch": 0},
            pipeline=[
                ModelComputePipelineStep(
                    step_name="identity",
                    step_type=EnumComputeStepType.TRANSFORMATION,
                    transformation_type=EnumTransformationType.IDENTITY,
                ),
            ],
        )

        # Test various special characters
        special_inputs = [
            "hello\nworld",  # Newline
            "hello\tworld",  # Tab
            "hello 世界",  # Unicode
            "test [regex] (chars) {special}",  # Regex chars
            "line1\r\nline2",  # Windows newline
            "",  # Empty string
        ]

        for input_data in special_inputs:
            result = execute_compute_pipeline(
                contract=contract,
                input_data=input_data,
                context=compute_execution_context_factory(),
            )
            assert result.success is True
            assert result.output == input_data

    def test_deeply_nested_input_data(
        self, compute_execution_context_factory: ComputeContextFactory
    ) -> None:
        """Test pipeline handles deeply nested input structures.

        Verifies that:
        - Deep nesting doesn't cause stack overflow
        - Mapping can access deeply nested fields
        """
        # Create deeply nested structure
        deep_input: dict = {
            "level0": {"level1": {"level2": {"level3": {"value": "found"}}}}
        }

        contract = ModelComputeSubcontract(
            operation_name="deep_nesting_test",
            operation_version={"major": 1, "minor": 0, "patch": 0},
            pipeline=[
                ModelComputePipelineStep(
                    step_name="extract_deep",
                    step_type=EnumComputeStepType.MAPPING,
                    mapping_config=ModelMappingConfig(
                        field_mappings={
                            "deep_value": "$.input.level0.level1.level2.level3.value",
                            "full_input": "$.input",
                        }
                    ),
                ),
            ],
        )

        result = execute_compute_pipeline(
            contract=contract,
            input_data=deep_input,
            context=compute_execution_context_factory(),
        )

        assert result.success is True
        assert result.output["deep_value"] == "found"
        assert result.output["full_input"] == deep_input

    def test_null_and_empty_values_in_input(
        self, compute_execution_context_factory: ComputeContextFactory
    ) -> None:
        """Test pipeline handles None and empty values.

        Verifies that:
        - None values pass through correctly
        - Empty strings and lists are handled
        - Empty dicts are handled
        """
        contract = ModelComputeSubcontract(
            operation_name="null_empty_test",
            operation_version={"major": 1, "minor": 0, "patch": 0},
            pipeline=[
                ModelComputePipelineStep(
                    step_name="identity",
                    step_type=EnumComputeStepType.TRANSFORMATION,
                    transformation_type=EnumTransformationType.IDENTITY,
                ),
            ],
        )

        # Test various null/empty inputs
        test_inputs: list[None | str | list | dict] = [
            None,
            "",
            [],
            {},
            {"key": None},
            {"key": ""},
            {"key": []},
        ]

        for input_data in test_inputs:
            result = execute_compute_pipeline(
                contract=contract,
                input_data=input_data,
                context=compute_execution_context_factory(),
            )
            assert result.success is True
            assert result.output == input_data

    def test_large_list_input(
        self, compute_execution_context_factory: ComputeContextFactory
    ) -> None:
        """Test pipeline handles large list inputs.

        Verifies that:
        - Large lists pass through without performance degradation
        - Identity transformation handles lists correctly
        """
        contract = ModelComputeSubcontract(
            operation_name="large_list_test",
            operation_version={"major": 1, "minor": 0, "patch": 0},
            pipeline=[
                ModelComputePipelineStep(
                    step_name="identity",
                    step_type=EnumComputeStepType.TRANSFORMATION,
                    transformation_type=EnumTransformationType.IDENTITY,
                ),
            ],
        )

        # Create large list
        large_list = list(range(10000))

        result = execute_compute_pipeline(
            contract=contract,
            input_data=large_list,
            context=compute_execution_context_factory(),
        )

        assert result.success is True
        assert result.output == large_list
        assert len(result.output) == 10000
        # Should complete reasonably fast
        assert result.processing_time_ms < 1000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
