"""
Input state model for Qdrant vector recommendation operations.

This model defines the input parameters for vector recommendations,
following ONEX canonical patterns with OnexInputState inheritance.
"""

from typing import Any

from pydantic import Field

from omnibase_core.model.core.model_onex_input_state import OnexInputState


class ModelRecommendVectorsInputState(OnexInputState):
    """
    Input state for Qdrant vector recommendation operations.

    Inherits standard fields from OnexInputState including:
    - correlation_id: Request correlation identifier
    - timestamp: Request timestamp
    - node_id: Source node identifier
    """

    collection_name: str = Field(..., description="Name of the collection to search in")
    positive_examples: list[str] = Field(
        ...,
        description="Vector IDs to use as positive examples",
    )
    negative_examples: list[str] | None = Field(
        default=None,
        description="Vector IDs to use as negative examples",
    )
    filter_conditions: dict[str, Any] | None = Field(
        default=None,
        description="Metadata filter conditions",
    )
    limit: int = Field(
        default=10,
        description="Maximum number of recommendations to return",
    )
    with_payload: bool = Field(
        default=True,
        description="Include metadata payload in results",
    )
    with_vectors: bool = Field(
        default=False,
        description="Include vector data in results",
    )
