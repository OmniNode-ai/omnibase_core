"""
Model for tool specification representation in ONEX NodeBase implementation.

This model supports the PATTERN-005 NodeBase functionality for
tool resolution from contract specifications.

"""

from pydantic import BaseModel, ConfigDict, Field


class ModelToolSpecification(BaseModel):
    """Model representing tool specification for NodeBase tool resolution."""

    model_config = ConfigDict(extra="ignore")

    main_tool_class: str = Field(
        default=...,
        description="Main tool class name for instantiation",
    )
