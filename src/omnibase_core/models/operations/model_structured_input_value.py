from __future__ import annotations

from pydantic import Field

"""
Strongly-typed structured input value model.

Represents structured data inputs for computation operations.
Follows ONEX strong typing principles and one-model-per-file architecture.
"""


from typing import Any

from pydantic import BaseModel

from omnibase_core.enums.enum_input_data_type import EnumInputDataType
from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelStructuredInputValue(BaseModel):
    """
    Strongly-typed structured input value for computation operations.

    Represents structured data inputs with explicit field definitions.
    """

    input_type: EnumInputDataType = Field(
        default=EnumInputDataType.STRUCTURED,
        description="Type identifier for structured input data",
    )
    data_structure: dict[str, Any] = Field(
        default_factory=dict,
        description="Structured data with field definitions",
    )
    schema_version: ModelSemVer = Field(
        default_factory=lambda: ModelSemVer(major=1, minor=0, patch=0),
        description="Schema version for the structured data",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata for structured input",
    )

    model_config = {
        "extra": "forbid",
        "use_enum_values": False,
        "validate_assignment": True,
    }


# Export for use
__all__ = ["ModelStructuredInputValue"]
