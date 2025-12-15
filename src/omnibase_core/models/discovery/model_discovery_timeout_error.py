"""
Discovery Timeout Error Model

Exception raised when discovery requests timeout with partial results support.
"""

from omnibase_core.models.discovery.model_tool_discovery_response import (
    ModelDiscoveredTool,
)


class ModelDiscoveryTimeoutError(Exception):
    """
    Raised when a discovery request times out.

    Supports partial results when some registries respond before timeout.
    """

    def __init__(
        self,
        message: str,
        timeout_seconds: float,
        partial_results: list[ModelDiscoveredTool] | None = None,
    ):
        """
        Initialize discovery timeout error.

        Args:
            message: Error message describing the timeout
            timeout_seconds: Actual timeout duration in seconds
            partial_results: Any tools discovered before timeout occurred
        """
        super().__init__(message)
        self.timeout_seconds = timeout_seconds
        self.partial_results = partial_results if partial_results is not None else []

    def has_partial_results(self) -> bool:
        """Check if any partial results were obtained before timeout"""
        return len(self.partial_results) > 0

    def get_partial_count(self) -> int:
        """Get the number of partial results obtained"""
        return len(self.partial_results)
