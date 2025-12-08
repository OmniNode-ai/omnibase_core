"""Unit tests for compute_executor error handling.

Tests focus on the execute_compute_pipeline function's handling of unexpected
exceptions, verifying that errors are captured in result objects rather than
propagated, and that proper logging occurs.

Related PR Review: PR #131 recommended adding tests for the error handling path.
"""

from unittest.mock import patch
from uuid import uuid4

import pytest

from omnibase_core.enums.enum_compute_step_type import EnumComputeStepType
from omnibase_core.enums.enum_transformation_type import EnumTransformationType
from omnibase_core.models.compute.model_compute_execution_context import (
    ModelComputeExecutionContext,
)
from omnibase_core.models.contracts.subcontracts.model_compute_pipeline_step import (
    ModelComputePipelineStep,
)
from omnibase_core.models.contracts.subcontracts.model_compute_subcontract import (
    ModelComputeSubcontract,
)
from omnibase_core.utils.compute_executor import execute_compute_pipeline


@pytest.mark.unit
@pytest.mark.timeout(10)
class TestPipelineExecutorUnexpectedErrors:
    """Tests for unexpected error handling in execute_compute_pipeline.

    The execute_compute_pipeline function captures unexpected exceptions
    (not ModelOnexError) in result objects rather than propagating them.
    This enables orchestration layers to handle failures gracefully.

    Note: 10-second timeout protects against pipeline execution hangs.
    """

    def test_unexpected_exception_sets_success_false(self) -> None:
        """Test that unexpected exceptions result in a failed pipeline status.

        Verifies that when a pipeline step raises an unexpected exception
        (not ModelOnexError), the pipeline result object has success=False,
        allowing callers to detect failures without catching exceptions.
        """
        contract = ModelComputeSubcontract(
            operation_name="failing_pipeline",
            operation_version="1.0.0",
            pipeline=[
                ModelComputePipelineStep(
                    step_name="failing_step",
                    step_type=EnumComputeStepType.TRANSFORMATION,
                    transformation_type=EnumTransformationType.IDENTITY,
                ),
            ],
        )
        context = ModelComputeExecutionContext(operation_id=uuid4())

        # Patch execute_pipeline_step to raise an unexpected exception
        with patch(
            "omnibase_core.utils.compute_executor.execute_pipeline_step"
        ) as mock_execute:
            mock_execute.side_effect = RuntimeError("Unexpected system failure")

            result = execute_compute_pipeline(contract, "test_input", context)

        assert result.success is False

    def test_unexpected_exception_sets_error_type_unexpected(self) -> None:
        """Test that unexpected exceptions are classified with error_type 'unexpected_error'.

        Verifies that non-ModelOnexError exceptions are categorized distinctly
        from structured ONEX errors, enabling orchestration layers to apply
        appropriate recovery strategies for unexpected failures.
        """
        contract = ModelComputeSubcontract(
            operation_name="failing_pipeline",
            operation_version="1.0.0",
            pipeline=[
                ModelComputePipelineStep(
                    step_name="failing_step",
                    step_type=EnumComputeStepType.TRANSFORMATION,
                    transformation_type=EnumTransformationType.IDENTITY,
                ),
            ],
        )
        context = ModelComputeExecutionContext(operation_id=uuid4())

        with patch(
            "omnibase_core.utils.compute_executor.execute_pipeline_step"
        ) as mock_execute:
            mock_execute.side_effect = ValueError("Invalid operation")

            result = execute_compute_pipeline(contract, "test_input", context)

        assert result.error_type == "unexpected_error"

    def test_unexpected_exception_captures_error_message(self) -> None:
        """Test that the original exception message is preserved in the result.

        Verifies that the error_message field contains the exception's message,
        providing diagnostic information for debugging without losing context
        about what caused the failure.
        """
        contract = ModelComputeSubcontract(
            operation_name="failing_pipeline",
            operation_version="1.0.0",
            pipeline=[
                ModelComputePipelineStep(
                    step_name="failing_step",
                    step_type=EnumComputeStepType.TRANSFORMATION,
                    transformation_type=EnumTransformationType.IDENTITY,
                ),
            ],
        )
        context = ModelComputeExecutionContext(operation_id=uuid4())
        expected_message = "Critical memory allocation failure"

        with patch(
            "omnibase_core.utils.compute_executor.execute_pipeline_step"
        ) as mock_execute:
            mock_execute.side_effect = MemoryError(expected_message)

            result = execute_compute_pipeline(contract, "test_input", context)

        assert result.error_message == expected_message

    def test_unexpected_exception_logs_via_logger_exception(self) -> None:
        """Test that unexpected errors trigger logger.exception with full traceback.

        Verifies that logger.exception is called (not logger.error), ensuring
        the full stack trace is captured for post-mortem debugging while the
        error is still gracefully handled in the result object.
        """
        contract = ModelComputeSubcontract(
            operation_name="failing_pipeline",
            operation_version="1.0.0",
            pipeline=[
                ModelComputePipelineStep(
                    step_name="failing_step",
                    step_type=EnumComputeStepType.TRANSFORMATION,
                    transformation_type=EnumTransformationType.IDENTITY,
                ),
            ],
        )
        context = ModelComputeExecutionContext(
            operation_id=uuid4(),
            correlation_id=uuid4(),
        )

        with (
            patch(
                "omnibase_core.utils.compute_executor.execute_pipeline_step"
            ) as mock_execute,
            patch("omnibase_core.utils.compute_executor.logger") as mock_logger,
        ):
            mock_execute.side_effect = OSError("Disk read error")

            execute_compute_pipeline(contract, "test_input", context)

            mock_logger.exception.assert_called_once()
            call_args = mock_logger.exception.call_args
            # Verify the log format string and arguments
            log_format = call_args[0][0]
            log_args = call_args[0][1:]
            assert "Unexpected error" in log_format
            # The step name is passed as the first argument to the format string
            assert "failing_step" in log_args

    def test_unexpected_exception_sets_error_step(self) -> None:
        """Test that the failing step is correctly identified in multi-step pipelines.

        Verifies that when a step fails in a multi-step pipeline, the error_step
        field correctly identifies which specific step caused the failure,
        enabling targeted debugging and partial recovery strategies.
        """
        contract = ModelComputeSubcontract(
            operation_name="failing_pipeline",
            operation_version="1.0.0",
            pipeline=[
                ModelComputePipelineStep(
                    step_name="step_one",
                    step_type=EnumComputeStepType.TRANSFORMATION,
                    transformation_type=EnumTransformationType.IDENTITY,
                ),
                ModelComputePipelineStep(
                    step_name="step_two_failing",
                    step_type=EnumComputeStepType.TRANSFORMATION,
                    transformation_type=EnumTransformationType.IDENTITY,
                ),
            ],
        )
        context = ModelComputeExecutionContext(operation_id=uuid4())

        call_count = 0

        def side_effect_fn(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First step succeeds
                return "step_one_output"
            # Second step fails
            raise KeyError("Missing required key")

        with patch(
            "omnibase_core.utils.compute_executor.execute_pipeline_step"
        ) as mock_execute:
            mock_execute.side_effect = side_effect_fn

            result = execute_compute_pipeline(contract, "test_input", context)

        assert result.error_step == "step_two_failing"

    def test_unexpected_exception_records_step_result(self) -> None:
        """Test that failing steps are recorded in step_results with error details.

        Verifies that the step_results dictionary contains an entry for the
        failing step with success=False, the error type, error message, and
        output=None, providing granular visibility into pipeline execution.
        """
        contract = ModelComputeSubcontract(
            operation_name="failing_pipeline",
            operation_version="1.0.0",
            pipeline=[
                ModelComputePipelineStep(
                    step_name="failing_step",
                    step_type=EnumComputeStepType.TRANSFORMATION,
                    transformation_type=EnumTransformationType.IDENTITY,
                ),
            ],
        )
        context = ModelComputeExecutionContext(operation_id=uuid4())

        with patch(
            "omnibase_core.utils.compute_executor.execute_pipeline_step"
        ) as mock_execute:
            mock_execute.side_effect = TypeError("Invalid type conversion")

            result = execute_compute_pipeline(contract, "test_input", context)

        assert "failing_step" in result.step_results
        step_result = result.step_results["failing_step"]
        assert step_result.success is False
        assert step_result.error_type == "unexpected_error"
        assert step_result.error_message == "Invalid type conversion"
        assert step_result.output is None

    def test_unexpected_exception_tracks_steps_executed(self) -> None:
        """Test that steps_executed accurately reflects execution progress.

        Verifies that the steps_executed list includes all steps that were
        attempted (including the failing step) but excludes steps that were
        never reached due to early termination, enabling progress tracking.
        """
        contract = ModelComputeSubcontract(
            operation_name="failing_pipeline",
            operation_version="1.0.0",
            pipeline=[
                ModelComputePipelineStep(
                    step_name="step_one",
                    step_type=EnumComputeStepType.TRANSFORMATION,
                    transformation_type=EnumTransformationType.IDENTITY,
                ),
                ModelComputePipelineStep(
                    step_name="failing_step",
                    step_type=EnumComputeStepType.TRANSFORMATION,
                    transformation_type=EnumTransformationType.IDENTITY,
                ),
                ModelComputePipelineStep(
                    step_name="never_reached",
                    step_type=EnumComputeStepType.TRANSFORMATION,
                    transformation_type=EnumTransformationType.IDENTITY,
                ),
            ],
        )
        context = ModelComputeExecutionContext(operation_id=uuid4())

        call_count = 0

        def side_effect_fn(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return "step_one_output"
            raise AttributeError("Object has no attribute 'foo'")

        with patch(
            "omnibase_core.utils.compute_executor.execute_pipeline_step"
        ) as mock_execute:
            mock_execute.side_effect = side_effect_fn

            result = execute_compute_pipeline(contract, "test_input", context)

        # step_one executed, failing_step recorded (with error), never_reached not executed
        assert "step_one" in result.steps_executed
        assert "failing_step" in result.steps_executed
        assert "never_reached" not in result.steps_executed

    def test_unexpected_exception_records_timing(self) -> None:
        """Test that timing metrics are recorded even when steps fail.

        Verifies that processing_time_ms and per-step duration_ms are captured
        regardless of success or failure, enabling performance analysis and
        identifying slow steps that may have contributed to failures.
        """
        contract = ModelComputeSubcontract(
            operation_name="failing_pipeline",
            operation_version="1.0.0",
            pipeline=[
                ModelComputePipelineStep(
                    step_name="failing_step",
                    step_type=EnumComputeStepType.TRANSFORMATION,
                    transformation_type=EnumTransformationType.IDENTITY,
                ),
            ],
        )
        context = ModelComputeExecutionContext(operation_id=uuid4())

        with patch(
            "omnibase_core.utils.compute_executor.execute_pipeline_step"
        ) as mock_execute:
            mock_execute.side_effect = Exception("Generic failure")

            result = execute_compute_pipeline(contract, "test_input", context)

        assert result.processing_time_ms >= 0
        assert result.step_results["failing_step"].metadata.duration_ms >= 0

    def test_unexpected_exception_does_not_propagate(self) -> None:
        """Test that no exception types propagate to callers from the pipeline.

        Verifies that various exception types (RuntimeError, ValueError,
        TypeError, KeyError, AttributeError, IOError, MemoryError) are all
        captured in the result object rather than propagating, ensuring
        callers can rely on result-based error handling.
        """
        contract = ModelComputeSubcontract(
            operation_name="failing_pipeline",
            operation_version="1.0.0",
            pipeline=[
                ModelComputePipelineStep(
                    step_name="failing_step",
                    step_type=EnumComputeStepType.TRANSFORMATION,
                    transformation_type=EnumTransformationType.IDENTITY,
                ),
            ],
        )
        context = ModelComputeExecutionContext(operation_id=uuid4())

        with patch(
            "omnibase_core.utils.compute_executor.execute_pipeline_step"
        ) as mock_execute:
            # Raise a variety of exception types to ensure none propagate
            for exc_class in [
                RuntimeError,
                ValueError,
                TypeError,
                KeyError,
                AttributeError,
                IOError,
                MemoryError,
            ]:
                mock_execute.side_effect = exc_class("Test exception")

                # Should NOT raise - errors are captured in result
                result = execute_compute_pipeline(contract, "test_input", context)

                assert result.success is False
                assert result.error_type == "unexpected_error"

    def test_unexpected_exception_includes_context_in_log(self) -> None:
        """Test that log output includes operation context for traceability.

        Verifies that operation_id and correlation_id from the execution
        context are included in log messages, enabling correlation of errors
        across distributed systems and log aggregation platforms.
        """
        contract = ModelComputeSubcontract(
            operation_name="failing_pipeline",
            operation_version="1.0.0",
            pipeline=[
                ModelComputePipelineStep(
                    step_name="failing_step",
                    step_type=EnumComputeStepType.TRANSFORMATION,
                    transformation_type=EnumTransformationType.IDENTITY,
                ),
            ],
        )
        operation_id = uuid4()
        correlation_id = uuid4()
        context = ModelComputeExecutionContext(
            operation_id=operation_id,
            correlation_id=correlation_id,
        )

        with (
            patch(
                "omnibase_core.utils.compute_executor.execute_pipeline_step"
            ) as mock_execute,
            patch("omnibase_core.utils.compute_executor.logger") as mock_logger,
        ):
            mock_execute.side_effect = RuntimeError("Test failure")

            execute_compute_pipeline(contract, "test_input", context)

            mock_logger.exception.assert_called_once()
            call_args = mock_logger.exception.call_args
            # Check that operation_id and correlation_id are passed as arguments
            log_args = call_args[0][1:]
            assert operation_id in log_args
            assert correlation_id in log_args


@pytest.mark.unit
@pytest.mark.timeout(5)
class TestPipelineExecutorLoggingDetails:
    """Tests for detailed logging behavior during error handling."""

    def test_logger_exception_includes_exception_type(self) -> None:
        """Test that log messages include the exception class name.

        Verifies that the exception type (e.g., 'ZeroDivisionError') is
        included in the log output, enabling quick categorization of
        failures in log analysis without parsing stack traces.
        """
        contract = ModelComputeSubcontract(
            operation_name="failing_pipeline",
            operation_version="1.0.0",
            pipeline=[
                ModelComputePipelineStep(
                    step_name="failing_step",
                    step_type=EnumComputeStepType.TRANSFORMATION,
                    transformation_type=EnumTransformationType.IDENTITY,
                ),
            ],
        )
        context = ModelComputeExecutionContext(operation_id=uuid4())

        with (
            patch(
                "omnibase_core.utils.compute_executor.execute_pipeline_step"
            ) as mock_execute,
            patch("omnibase_core.utils.compute_executor.logger") as mock_logger,
        ):
            mock_execute.side_effect = ZeroDivisionError("division by zero")

            execute_compute_pipeline(contract, "test_input", context)

            call_args = mock_logger.exception.call_args
            # The logger.exception format string includes type(e).__name__
            log_args = call_args[0][1:]
            assert "ZeroDivisionError" in log_args
