"""
Storage Credentials Model Config.

Pydantic model configuration for ONEX compliance.
"""

from pydantic import SecretStr


class ModelConfig:
    """Pydantic model configuration for ONEX compliance."""

    validate_assignment = True
    json_encoders = {SecretStr: lambda v: v.get_secret_value() if v else None}
