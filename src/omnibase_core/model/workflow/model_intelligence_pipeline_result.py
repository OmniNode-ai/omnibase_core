#!/usr/bin/env python3
"""
ModelIntelligencePipelineResult - Result from intelligence pipeline execution.

This model represents the result data structure from intelligence pipeline
execution in the ONEX platform's workflow 6 system integration.
"""

from typing import Dict, List, Union

from pydantic import BaseModel, Field

# Type aliases for strong typing
PipelineResult = Dict[str, Union[str, int, float, bool, List[str], Dict[str, str]]]
PipelineMetadata = Dict[str, Union[str, int, float, bool, List[str]]]
IntelligenceData = Dict[
    str, Union[str, int, float, bool, List[str], Dict[str, Union[str, int, float]]]
]


class ModelIntelligencePipelineResult(BaseModel):
    """Result from intelligence pipeline execution."""

    pipeline_id: str = Field(..., description="ID of the executed pipeline")
    intelligence_extracted: IntelligenceData = Field(
        ..., description="Extracted intelligence data"
    )
    learning_patterns: List[PipelineResult] = Field(
        default_factory=list, description="Identified learning patterns"
    )
    context_updates: PipelineResult = Field(
        default_factory=dict, description="Context rule updates"
    )
    metadata_generated: PipelineMetadata = Field(
        default_factory=dict, description="Generated metadata"
    )
    execution_metrics: PipelineMetadata = Field(
        default_factory=dict, description="Pipeline execution metrics"
    )
