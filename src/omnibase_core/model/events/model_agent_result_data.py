"""
Model for agent task result data.

Provides strongly-typed structure for agent task results with proper ONEX compliance.
"""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class ModelAgentTaskResultData(BaseModel):
    """
    Structured result data from agent task execution.

    Replaces Dict[str, Any] usage for ONEX compliance.
    """

    execution_time_ms: Optional[int] = Field(
        None, description="Execution time in milliseconds"
    )
    tokens_used: Optional[int] = Field(None, description="Number of tokens consumed")
    model_name: Optional[str] = Field(None, description="Model used for task execution")
    output_files: List[str] = Field(
        default_factory=list, description="Files created/modified"
    )
    metrics: Dict[str, float] = Field(
        default_factory=dict, description="Performance metrics"
    )
    metadata: Dict[str, str] = Field(
        default_factory=dict, description="Additional metadata"
    )
