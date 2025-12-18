"""
Node Status Types.

ONEX discriminated union types for node status patterns.
"""

from typing import Any

from pydantic import Discriminator


def get_node_status_discriminator(v: Any) -> str:
    """Extract discriminator value for node status union."""
    if isinstance(v, dict):
        status_type = v.get("status_type", "active")
        return str(status_type)  # Ensure string type
    return str(getattr(v, "status_type", "active"))  # Ensure string type


# Discriminator for Pydantic validation of node status types
NodeStatusDiscriminator = Discriminator(
    get_node_status_discriminator,
    custom_error_type="node_status_discriminator",
    custom_error_message="Invalid node status type",
    custom_error_context={"discriminator": "status_type"},
)

__all__ = []
