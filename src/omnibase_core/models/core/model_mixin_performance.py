"""Pydantic model for mixin performance characteristics.

This module provides the ModelMixinPerformance class for defining
performance characteristics and recommendations for mixins.
"""

from pydantic import BaseModel, Field

from omnibase_core.models.core.model_mixin_performance_use_case import (
    ModelMixinPerformanceUseCase,
)


class ModelMixinPerformance(BaseModel):
    """Performance characteristics and recommendations.

    Attributes:
        overhead_per_call: Overhead per call description
        memory_per_instance: Memory per instance description
        recommended_max_retries: Recommended maximum retries (if applicable)
        typical_use_cases: Performance data per use case
    """

    overhead_per_call: str | None = Field(None, description="Overhead per call")
    memory_per_instance: str | None = Field(None, description="Memory per instance")
    recommended_max_retries: int | None = Field(None, description="Max retries")
    typical_use_cases: list[ModelMixinPerformanceUseCase] = Field(
        default_factory=list, description="Use case performance data"
    )
