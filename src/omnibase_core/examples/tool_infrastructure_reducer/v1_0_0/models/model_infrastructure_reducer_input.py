"""Input model for Infrastructure Reducer operations."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ModelInfrastructureReducerInput(BaseModel):
    """Input model for Infrastructure Reducer operations."""

    operation_type: str = Field(
        ..., description="Type of reduction operation to perform"
    )
    adapter_results: List[Dict[str, Any]] = Field(
        ..., description="Results from infrastructure adapters to aggregate"
    )
    correlation_id: Optional[str] = Field(
        None, description="Correlation ID for tracking the operation"
    )
