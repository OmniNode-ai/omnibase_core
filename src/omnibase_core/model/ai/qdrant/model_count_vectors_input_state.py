"""
Input state model for Qdrant vector counting operations.

This model defines the input parameters for counting vectors in collections,
following ONEX canonical patterns with OnexInputState inheritance.
"""

from typing import Any, Dict, Optional

from pydantic import Field

from omnibase_core.model.core.model_onex_input_state import OnexInputState


class ModelCountVectorsInputState(OnexInputState):
    """
    Input state for Qdrant vector counting operations.

    Inherits standard fields from OnexInputState including:
    - correlation_id: Request correlation identifier
    - timestamp: Request timestamp
    - node_id: Source node identifier
    """

    collection_name: str = Field(
        ..., description="Name of the collection to count vectors in"
    )
    filter_conditions: Optional[Dict[str, Any]] = Field(
        default=None, description="Metadata filter conditions for counting"
    )
    exact: bool = Field(
        default=False,
        description="Whether to perform exact counting (slower but precise)",
    )
