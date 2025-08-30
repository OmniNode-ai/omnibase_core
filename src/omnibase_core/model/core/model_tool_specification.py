"""
Model for tool specification representation in ONEX NodeBase implementation.

This model supports the PATTERN-005 NodeBase functionality for
tool resolution from contract specifications.

Author: ONEX Framework Team
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.core.enums.enum_business_logic_pattern import (
    EnumBusinessLogicPattern,
)


class ModelToolSpecification(BaseModel):
    """Model representing tool specification for NodeBase tool resolution."""

    model_config = ConfigDict(extra="ignore")

    main_tool_class: str = Field(
        ...,
        description="Main tool class name for instantiation",
    )
    business_logic_pattern: EnumBusinessLogicPattern = Field(
        default=EnumBusinessLogicPattern.COMPUTE,
        description="Business logic pattern type",
    )
