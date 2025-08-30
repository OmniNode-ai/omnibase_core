#!/usr/bin/env python3
"""
ModelIntelligencePipelineInput - Input data for intelligence pipeline workflows.

This model represents input data structure for intelligence pipeline workflows
in the ONEX platform's workflow 6 system integration.
"""

from typing import Dict, List, Union

from pydantic import BaseModel, Field

# Type aliases for strong typing
PipelineInputData = Dict[str, Union[str, int, float, bool, List[str], Dict[str, str]]]
PipelineMetadata = Dict[str, Union[str, int, float, bool, List[str]]]


class ModelIntelligencePipelineInput(BaseModel):
    """Input data for intelligence pipeline workflows."""

    source_type: str = Field(
        ..., description="Type of intelligence source (file, conversation, interaction)"
    )
    source_data: PipelineInputData = Field(..., description="Raw source data")
    context_metadata: PipelineMetadata = Field(
        default_factory=dict, description="Contextual metadata"
    )
    correlation_id: str = Field(..., description="Correlation ID for tracking")
    priority_level: str = Field(default="normal", description="Processing priority")
