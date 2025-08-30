"""Event Registry Coordinator Output model for ONEX Discovery & Integration Event Registry.

This module defines the output model for Event Registry Coordinator operations.
"""

from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.model.discovery.model_event_descriptor import \
    ServiceStatusEnum


class ModelEventRegistryCoordinatorOutput(BaseModel):
    """Output model for Event Registry Coordinator operations."""

    coordinator_result: str = Field(..., description="Coordinator operation result")

    phase_initialization_success: Optional[bool] = Field(
        None, description="Phase initialization success"
    )

    active_adapters: Optional[List[str]] = Field(
        None, description="List of active Container Adapter IDs"
    )

    routing_success: Optional[bool] = Field(None, description="Event routing success")

    coordination_success: Optional[bool] = Field(
        None, description="Cross-adapter coordination success"
    )

    adapter_health_status: Optional[Dict[str, ServiceStatusEnum]] = Field(
        None, description="Health status of Container Adapters"
    )

    operation_timestamp: str = Field(..., description="Operation timestamp")

    error_details: Optional[str] = Field(
        None, description="Error details if operation failed"
    )

    operation_successful: bool = Field(
        True, description="Whether operation was successful"
    )

    model_config = ConfigDict(extra="forbid")
