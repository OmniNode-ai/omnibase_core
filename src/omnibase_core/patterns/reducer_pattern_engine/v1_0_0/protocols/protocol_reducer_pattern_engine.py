"""Protocol definition for Reducer Pattern Engine ONEX compliance."""

from abc import ABC, abstractmethod
from typing import Protocol, runtime_checkable

from ..models.model_reducer_pattern_engine_input import ModelReducerPatternEngineInput
from ..models.model_reducer_pattern_engine_output import ModelReducerPatternEngineOutput


@runtime_checkable
class ProtocolReducerPatternEngine(Protocol):
    """
    Protocol definition for Reducer Pattern Engine implementations.

    Defines the contract that all Reducer Pattern Engine implementations
    must follow for ONEX compliance and interoperability.
    """

    async def process_workflow(
        self, engine_input: ModelReducerPatternEngineInput
    ) -> ModelReducerPatternEngineOutput:
        """
        Process a workflow through the Reducer Pattern Engine.

        Args:
            engine_input: ONEX-compliant input with workflow request and optional envelope

        Returns:
            ModelReducerPatternEngineOutput: ONEX-compliant output with response and envelope

        Raises:
            OnexError: If processing fails
        """
        ...

    async def health_check(self) -> bool:
        """
        Check the health status of the engine.

        Returns:
            bool: True if engine is healthy, False otherwise
        """
        ...

    def get_supported_workflow_types(self) -> list[str]:
        """
        Get list of supported workflow types.

        Returns:
            list[str]: List of workflow type strings
        """
        ...


class BaseReducerPatternEngine(ABC):
    """
    Abstract base class for Reducer Pattern Engine implementations.

    Provides common functionality and enforces the protocol contract
    for all concrete implementations.
    """

    @abstractmethod
    async def process_workflow(
        self, engine_input: ModelReducerPatternEngineInput
    ) -> ModelReducerPatternEngineOutput:
        """
        Process a workflow through the Reducer Pattern Engine.

        Args:
            engine_input: ONEX-compliant input with workflow request and optional envelope

        Returns:
            ModelReducerPatternEngineOutput: ONEX-compliant output with response and envelope

        Raises:
            OnexError: If processing fails
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check the health status of the engine.

        Returns:
            bool: True if engine is healthy, False otherwise
        """
        pass

    @abstractmethod
    def get_supported_workflow_types(self) -> list[str]:
        """
        Get list of supported workflow types.

        Returns:
            list[str]: List of workflow type strings
        """
        pass

    async def validate_input(
        self, engine_input: ModelReducerPatternEngineInput
    ) -> None:
        """
        Validate engine input for protocol compliance.

        Args:
            engine_input: Input to validate

        Raises:
            ValueError: If input is invalid
        """
        if not isinstance(engine_input, ModelReducerPatternEngineInput):
            raise ValueError("Input must be ModelReducerPatternEngineInput")

        # Validate workflow request
        if not engine_input.workflow_request:
            raise ValueError("Workflow request is required")

        # Validate workflow type is supported
        supported_types = self.get_supported_workflow_types()

        # Handle both enum and string values for workflow_type
        workflow_type = engine_input.workflow_request.workflow_type
        if hasattr(workflow_type, "value"):
            # It's an enum, get the value
            workflow_type_str = workflow_type.value
        else:
            # It's already a string
            workflow_type_str = str(workflow_type)

        if workflow_type_str not in supported_types:
            raise ValueError(
                f"Unsupported workflow type: {workflow_type_str}. "
                f"Supported types: {supported_types}"
            )

    def create_error_output(
        self,
        engine_input: ModelReducerPatternEngineInput,
        error_message: str,
        error_details: dict = None,
    ) -> ModelReducerPatternEngineOutput:
        """
        Create an error output for failed processing.

        Args:
            engine_input: Original input that caused the error
            error_message: Error message
            error_details: Additional error details

        Returns:
            ModelReducerPatternEngineOutput: Error response
        """
        from ..models.model_workflow_error import ModelWorkflowError
        from ..models.model_workflow_response import ModelWorkflowResponse
        from ..models.model_workflow_result import ModelWorkflowResult
        from ..models.model_workflow_types import WorkflowStatus

        # Create error workflow response
        workflow_response = ModelWorkflowResponse(
            workflow_id=engine_input.workflow_request.workflow_id,
            workflow_type=engine_input.workflow_request.workflow_type,
            instance_id=engine_input.workflow_request.instance_id,
            correlation_id=engine_input.workflow_request.correlation_id,
            status=WorkflowStatus.FAILED,
            result=ModelWorkflowResult(success=False),
            error=ModelWorkflowError(
                error_code="UNSUPPORTED_WORKFLOW",
                error_message=error_message,
                error_context=error_details or {},
            ),
            processing_time_ms=0.0,
            subreducer_name="error_handler",
        )

        return ModelReducerPatternEngineOutput.from_workflow_response(
            workflow_response=workflow_response,
            correlation_id=engine_input.get_correlation_id(),
            source_node_id="reducer_pattern_engine",
            target_node_id=engine_input.get_source_node_id(),
            processing_metadata={
                "error": True,
                "error_message": error_message,
                "error_details": error_details or {},
            },
        )
