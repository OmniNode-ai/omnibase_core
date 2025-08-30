"""
LLM routing statistics model for model router.

Provides strongly-typed routing statistics to replace Dict[str, Any] usage
with proper ONEX naming conventions.
"""

from typing import Dict

from pydantic import BaseModel, ConfigDict, Field


class ModelLLMRoutingStats(BaseModel):
    """
    Strongly-typed LLM routing statistics model.

    Replaces Dict[str, Any] usage in router statistics
    with proper type safety and validation.
    """

    total_requests: int = Field(
        default=0, ge=0, description="Total number of LLM requests processed"
    )

    successful_requests: int = Field(
        default=0, ge=0, description="Number of successful LLM requests"
    )

    failed_requests: int = Field(
        default=0, ge=0, description="Number of failed LLM requests"
    )

    provider_usage: Dict[str, int] = Field(
        default_factory=dict, description="Request count per LLM provider"
    )

    failover_attempts: int = Field(
        default=0, ge=0, description="Number of failover attempts between providers"
    )

    cost_savings: float = Field(
        default=0.0,
        ge=0.0,
        description="Estimated cost savings from intelligent routing",
    )

    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total_requests == 0:
            return 0.0
        return (self.successful_requests / self.total_requests) * 100.0

    @property
    def failure_rate(self) -> float:
        """Calculate failure rate percentage."""
        if self.total_requests == 0:
            return 0.0
        return (self.failed_requests / self.total_requests) * 100.0

    model_config = ConfigDict(validate_assignment=True, extra="forbid")
