"""
Model specialization model for LLM model capabilities and use cases.

Provides strongly-typed model specialization definitions including
use cases, descriptions, and capability information.
"""

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_query_type import EnumQueryType


class ModelModelSpecialization(BaseModel):
    """
    Model specialization definition for LLM models.

    Provides strongly-typed specification of model capabilities,
    use cases, and performance characteristics.
    """

    use_cases: list[EnumQueryType] = Field(
        default_factory=list,
        description="Query types this model specializes in",
    )
    description: str = Field(..., description="Description of model specialization")
    performance_tier: str = Field(
        default="standard",
        description="Performance tier classification",
    )
    recommended_for: list[str] = Field(
        default_factory=list,
        description="Recommended use scenarios",
    )
