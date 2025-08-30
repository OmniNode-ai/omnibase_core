"""
Input state model for Qdrant vector scrolling operations.

This model defines the input parameters for scrolling through vectors,
following ONEX canonical patterns with OnexInputState inheritance.
"""

from typing import Any, Dict, Optional

from pydantic import Field

from omnibase_core.model.core.model_onex_input_state import OnexInputState


class ModelScrollVectorsInputState(OnexInputState):
    """
    Input state for Qdrant vector scrolling operations.

    Inherits standard fields from OnexInputState including:
    - correlation_id: Request correlation identifier
    - timestamp: Request timestamp
    - node_id: Source node identifier
    """

    collection_name: str = Field(
        ..., description="Name of the collection to scroll through"
    )
    filter_conditions: Optional[Dict[str, Any]] = Field(
        default=None, description="Metadata filter conditions"
    )
    limit: int = Field(
        default=100, description="Maximum number of vectors to return per page"
    )
    offset: Optional[str] = Field(
        default=None, description="Pagination offset for continuing from previous page"
    )
    with_payload: bool = Field(
        default=True, description="Include metadata payload in results"
    )
    with_vectors: bool = Field(
        default=False, description="Include vector data in results"
    )
