#!/usr/bin/env python3
"""
ONEX Mock Event Bus Models

This module provides strongly typed Pydantic models for mock event bus service
to replace Dict[str, Any] usage with proper type safety.
"""

from datetime import datetime
from uuid import UUID

from omnibase.enums.enum_log_level import LogLevelEnum
from pydantic import BaseModel, Field


class ModelMockEventBusConfig(BaseModel):
    """Configuration model for mock event bus behavior"""

    deterministic_responses: dict[str, dict[str, dict]] = Field(
        default_factory=dict,
        description="Deterministic responses for different methods",
    )
    failure_injection: dict[str, bool] = Field(
        default_factory=dict,
        description="Failure injection configuration",
    )
    response_delays: dict[str, float] = Field(
        default_factory=dict,
        description="Response delay configuration in seconds",
    )


class ModelEmittedEvent(BaseModel):
    """Model for emitted event data"""

    event_id: str = Field(description="Unique event identifier")
    event_type: str = Field(description="Type of event emitted")
    event_data: dict = Field(description="Event payload data")
    correlation_id: UUID = Field(description="Correlation ID for tracing")
    timestamp: datetime = Field(description="When the event was emitted")
    sequence_number: int = Field(description="Event sequence number")


class ModelEmittedLog(BaseModel):
    """Model for emitted log data"""

    log_id: str = Field(description="Unique log identifier")
    level: LogLevelEnum = Field(description="Log level")
    message: str = Field(description="Log message")
    correlation_id: UUID = Field(description="Correlation ID for tracing")
    timestamp: datetime = Field(description="When the log was emitted")
    sequence_number: int = Field(description="Log sequence number")
    additional_data: dict | None = Field(
        default=None,
        description="Additional log data",
    )


class ModelEventResponse(BaseModel):
    """Model for event emission response"""

    event_id: str = Field(description="Generated event ID")
    status: str = Field(description="Emission status")
    timestamp: str = Field(description="Response timestamp")
    correlation_id: str = Field(description="Correlation ID as string")


class ModelLogResponse(BaseModel):
    """Model for log emission response"""

    log_id: str = Field(description="Generated log ID")
    level: str = Field(description="Log level")
    status: str = Field(description="Emission status")
    timestamp: str = Field(description="Response timestamp")
    correlation_id: str = Field(description="Correlation ID as string")


class ModelMockState(BaseModel):
    """Model for mock event bus state"""

    total_events_emitted: int = Field(description="Total number of events emitted")
    total_logs_emitted: int = Field(description="Total number of logs emitted")
    event_sequence: int = Field(description="Current event sequence number")
    log_sequence: int = Field(description="Current log sequence number")
    failure_injection_enabled: bool = Field(
        description="Whether failure injection is enabled",
    )
    failure_injection_type: str | None = Field(
        default=None,
        description="Type of failure injection active",
    )
    emitted_events_count: int = Field(description="Count of emitted events")
    emitted_logs_count: int = Field(description="Count of emitted logs")


class ModelDefaultResponse(BaseModel):
    """Model for default mock responses"""

    method_name: str = Field(description="Method that was called")
    response_type: str = Field(description="Type of response")
    status: str = Field(description="Response status")
    timestamp: str = Field(description="Response timestamp")
    response_data: dict = Field(description="Mock response data")
