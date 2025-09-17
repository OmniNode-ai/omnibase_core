#!/usr/bin/env python3
"""
RSD Trigger Context Model - ONEX Standards Compliant.

Strongly-typed model for trigger context in RSD algorithm.
"""

from datetime import datetime

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_rsd_trigger_type import EnumRSDTriggerType
from omnibase_core.models.rsd.model_event_data import ModelEventData


class ModelTriggerContext(BaseModel):
    """
    Model for context information during RSD algorithm trigger evaluation.

    Used to capture and track the context and metadata when RSD algorithm
    reprioritization is triggered by various events in the system.
    """

    trigger_id: str = Field(description="Unique trigger identifier")

    trigger_type: EnumRSDTriggerType = Field(
        description="Type of trigger that initiated reprioritization",
    )

    event_data: ModelEventData = Field(
        description="Raw event data that triggered reprioritization",
    )

    affected_tickets: list[str] = Field(
        description="List of ticket IDs affected by this trigger",
        default_factory=list,
    )

    timestamp: datetime = Field(
        description="When the trigger occurred",
        default_factory=datetime.now,
    )

    processing_complete: bool = Field(
        description="Whether trigger processing is complete",
        default=False,
    )

    class Config:
        """Pydantic model configuration for ONEX compliance."""

        validate_assignment = True
        json_encoders = {datetime: lambda v: v.isoformat()}
