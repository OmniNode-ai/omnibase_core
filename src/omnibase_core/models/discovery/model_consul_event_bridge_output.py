"""Consul Event Bridge Output model for ONEX Discovery & Integration Event Registry.

This module defines the output model for Consul Event Bridge operations.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.discovery.model_event_descriptor import ModelEventDescriptor


class ModelConsulEventBridgeOutput(BaseModel):
    """Output model for Consul Event Bridge operations."""

    bridge_result: str = Field(default=..., description="Bridge operation result")

    bridging_success: bool | None = Field(
        default=None, description="Event bridging success"
    )

    bridged_event_descriptor: ModelEventDescriptor | None = Field(
        default=None,
        description="Event descriptor created from Consul data",
    )

    sync_success: bool | None = Field(
        default=None,
        description="State synchronization success",
    )

    monitoring_started: bool | None = Field(
        default=None,
        description="Event monitoring started successfully",
    )

    operation_timestamp: str = Field(default=..., description="Operation timestamp")

    error_details: str | None = Field(
        default=None,
        description="Error details if operation failed",
    )

    operation_successful: bool = Field(
        default=True,
        description="Whether operation was successful",
    )

    model_config = ConfigDict(extra="forbid")
