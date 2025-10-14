from typing import Literal

from pydantic import Field

from omnibase_core.enums.enum_event_type import EnumEventType
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.operations.model_event_data_base import ModelEventDataBase


class ModelSystemEventData(ModelEventDataBase):
    """System-level event data."""

    event_type: Literal[EnumEventType.SYSTEM] = Field(
        default=EnumEventType.SYSTEM,
        description="System event type",
    )
    system_component: str = Field(
        default=...,
        description="System component that generated the event",
    )
    severity_level: str = Field(default="info", description="Event severity level")
    diagnostic_data: dict[str, ModelSchemaValue] = Field(
        default_factory=dict,
        description="System diagnostic data",
    )
    correlation_trace: list[str] = Field(
        default_factory=list,
        description="Event correlation trace",
    )
