"""
Input state model for Qdrant version retrieval operations.

This model defines the input parameters for getting Qdrant server version,
following ONEX canonical patterns with OnexInputState inheritance.
"""

from omnibase_core.model.core.model_onex_input_state import OnexInputState


class ModelGetVersionInputState(OnexInputState):
    """
    Input state for Qdrant version retrieval operations.

    Inherits standard fields from OnexInputState including:
    - correlation_id: Request correlation identifier
    - timestamp: Request timestamp
    - node_id: Source node identifier
    """

    pass  # No additional fields needed for version request
