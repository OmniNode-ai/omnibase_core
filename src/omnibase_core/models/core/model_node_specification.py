"""
Model for node specification representation in ONEX NodeBase implementation.

This model supports the PATTERN-005 NodeBase functionality for
node resolution from contract specifications.

Author: ONEX Framework Team
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelNodeSpecification(BaseModel):
    """Model representing node specification for NodeBase node resolution."""

    model_config = ConfigDict(extra="ignore")

    main_node_class: str = Field(
        ...,
        description="Main node class name for instantiation",
    )
    # TODO: Re-enable when enum is available
    # business_logic_pattern: EnumBusinessLogicPattern = Field(
    #     default=EnumBusinessLogicPattern.COMPUTE,
    #     description="Business logic pattern type",
    # )
