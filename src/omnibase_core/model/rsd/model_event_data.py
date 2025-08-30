#!/usr/bin/env python3
"""
RSD Event Data Model - ONEX Standards Compliant.

Strongly-typed event data model for trigger context, replacing Union types.
Generated from contract: rsd_metadata_types_contract.yaml
"""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class ModelEventData(BaseModel):
    """
    Strongly-typed event data for trigger context.

    Replaces Dict[str, Union[str, int, float, bool, List[str]]] with specific typed fields.
    This model provides type safety and validation for event data in trigger contexts.
    """

    source_system: str = Field(description="System that generated the event")

    event_type: str = Field(description="Type of event that occurred")

    severity: Optional[str] = Field(None, description="Event severity level")

    affected_components: List[str] = Field(
        default_factory=list, description="List of affected component names"
    )

    numeric_metrics: Dict[str, float] = Field(
        default_factory=dict, description="Numeric metrics from the event"
    )

    text_details: Dict[str, str] = Field(
        default_factory=dict, description="Text-based event details"
    )

    class Config:
        """Pydantic model configuration for ONEX compliance."""

        validate_assignment = True
