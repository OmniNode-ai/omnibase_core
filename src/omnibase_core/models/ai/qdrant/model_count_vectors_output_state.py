"""
Output state model for Qdrant vector counting operations.

This model defines the output results for counting vectors in collections,
following ONEX canonical patterns with OnexOutputState inheritance.
"""

from pydantic import Field

from omnibase_core.models.core.model_onex_output_state import OnexOutputState


class ModelCountVectorsOutputState(OnexOutputState):
    """
    Output state for Qdrant vector counting operations.

    Inherits standard fields from OnexOutputState including:
    - status: Execution status
    - message: Status message
    - execution_time_seconds: Execution duration
    """

    count: int = Field(..., description="Number of vectors matching the criteria")
    is_exact: bool = Field(..., description="Whether the count is exact or approximate")
    collection_name: str = Field(
        ...,
        description="Name of the collection that was counted",
    )
