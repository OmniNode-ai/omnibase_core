"""
Storage Result Model Config.

Pydantic model configuration for ONEX compliance.
"""

from datetime import datetime


class ModelConfig:
    """Pydantic model configuration for ONEX compliance."""

    validate_assignment = True
    json_encoders = {datetime: lambda v: v.isoformat()}
