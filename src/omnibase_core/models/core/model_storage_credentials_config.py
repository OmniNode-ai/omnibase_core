"""
Storage Credentials Model Config.

Pydantic model configuration for ONEX compliance.
"""

from pydantic import SecretStr


class ModelConfig:
    """Pydantic model configuration for ONEX compliance."""

    validate_assignment = True
