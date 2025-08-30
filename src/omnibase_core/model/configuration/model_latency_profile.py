"""
Latency profile assessment model to replace Dict[str, Any] usage.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ModelLatencyProfile(BaseModel):
    """
    Latency profile assessment with typed fields.
    Replaces Dict[str, Any] for _get_latency_profile() returns.
    """

    # Latency assessments
    connection_latency: str = Field(
        ..., description="Connection latency level (low/medium/high)"
    )
    query_latency: str = Field(..., description="Query latency level (low/medium/high)")
    overall_latency: str = Field(..., description="Overall latency assessment")

    # Latency factors
    factors: List[str] = Field(
        default_factory=list, description="Factors affecting latency"
    )

    # Specific measurements
    avg_connection_time_ms: Optional[float] = Field(
        None, description="Average connection time"
    )
    avg_query_time_ms: Optional[float] = Field(None, description="Average query time")
    p95_connection_time_ms: Optional[float] = Field(
        None, description="95th percentile connection time"
    )
    p95_query_time_ms: Optional[float] = Field(
        None, description="95th percentile query time"
    )

    # Recommendations
    optimization_suggestions: List[str] = Field(
        default_factory=list, description="Latency optimization suggestions"
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for backward compatibility."""
        return self.dict(exclude_none=True)
