"""
ModelSecurityPolicyData: Security policy data container.

This model represents the serialized data structure for security policies.
"""

from datetime import datetime
from typing import Union

from pydantic import BaseModel, Field

# Type alias for policy values that can be serialized
PolicyValue = Union[str, int, float, bool, list[str], datetime, None]


class ModelSecurityPolicyData(BaseModel):
    """Security policy data container for serialization."""

    data: dict[str, PolicyValue] = Field(
        default_factory=dict,
        description="Policy data fields",
    )

    class Config:
        """Pydantic configuration."""

        arbitrary_types_allowed = True
