"""Masked Data Model Configuration.

Pydantic configuration for ModelMaskedData.
"""

from pydantic import ConfigDict


class ModelConfig:
    """Pydantic configuration."""

    arbitrary_types_allowed = True
