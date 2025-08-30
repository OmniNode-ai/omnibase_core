"""
Output state model for Qdrant vector scrolling operations.

This model defines the output results for scrolling through vectors,
following ONEX canonical patterns with OnexOutputState inheritance.
"""

from typing import Any, Dict, List, Optional

from pydantic import Field

from omnibase_core.model.core.model_onex_output_state import OnexOutputState


class ModelScrollVectorsOutputState(OnexOutputState):
    """
    Output state for Qdrant vector scrolling operations.

    Inherits standard fields from OnexOutputState including:
    - status: Execution status
    - message: Status message
    - execution_time_seconds: Execution duration
    """

    vectors: List[Dict[str, Any]] = Field(
        ..., description="List of vector records with metadata"
    )
    next_offset: Optional[str] = Field(
        default=None, description="Offset for next page, None if no more results"
    )
    total_count: Optional[int] = Field(
        default=None, description="Total number of vectors in collection (if available)"
    )
    collection_name: str = Field(
        ..., description="Name of the collection that was scrolled"
    )
