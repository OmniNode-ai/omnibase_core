"""
Output state model for Qdrant version retrieval operations.

This model defines the output results for getting Qdrant server version,
following ONEX canonical patterns with OnexOutputState inheritance.
"""

from pydantic import Field

from omnibase_core.models.core.model_onex_output_state import OnexOutputState


class ModelGetVersionOutputState(OnexOutputState):
    """
    Output state for Qdrant version retrieval operations.

    Inherits standard fields from OnexOutputState including:
    - status: Execution status
    - message: Status message
    - execution_time_seconds: Execution duration
    """

    version: str = Field(..., description="Qdrant server version string")
    build_info: dict = Field(
        default_factory=dict,
        description="Additional build information",
    )
    server_uptime_seconds: float = Field(
        default=0.0,
        description="Server uptime in seconds",
    )
