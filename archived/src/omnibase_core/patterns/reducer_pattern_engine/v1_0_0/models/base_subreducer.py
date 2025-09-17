"""Base subreducer interface for Reducer Pattern Engine."""

from .model_subreducer_result import ModelSubreducerResult
from .model_workflow_request import ModelWorkflowRequest
from .model_workflow_types import WorkflowType


class BaseSubreducer:
    """
    Abstract base interface for all subreducers.

    Defines the contract that all subreducers must implement
    for consistent integration with the Reducer Pattern Engine.
    """

    def __init__(self, name: str):
        """Initialize the subreducer with a name."""
        self.name = name

    async def process(self, request: ModelWorkflowRequest) -> ModelSubreducerResult:
        """
        Process a workflow request.

        Args:
            request: The workflow request to process

        Returns:
            ModelSubreducerResult: The processing result

        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError("Subclasses must implement process method")

    def supports_workflow_type(self, workflow_type: WorkflowType) -> bool:
        """
        Check if this subreducer supports the given workflow type.

        Args:
            workflow_type: The workflow type to check

        Returns:
            bool: True if supported, False otherwise
        """
        raise NotImplementedError(
            "Subclasses must implement supports_workflow_type method",
        )
