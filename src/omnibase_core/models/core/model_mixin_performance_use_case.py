"""Pydantic model for mixin performance use case data.

This module provides the ModelMixinPerformanceUseCase class for defining
performance characteristics for specific use cases.
"""

from pydantic import BaseModel, Field


class ModelMixinPerformanceUseCase(BaseModel):
    """Performance data for specific use case.

    Attributes:
        use_case: Use case name
        recommended_config: Recommended preset name
        expected_overhead: Expected overhead description
    """

    use_case: str = Field(..., description="Use case name")
    recommended_config: str = Field(..., description="Recommended preset")
    expected_overhead: str = Field(..., description="Expected overhead")
