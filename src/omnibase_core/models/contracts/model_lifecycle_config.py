from pydantic import Field

"""
EnumLifecycle Configuration Model - ONEX Standards Compliant.

EnumLifecycle management configuration for node initialization and cleanup providing:
- Initialization, error handling, and state management policies
- Health check and timeout configuration
- Error recovery mechanisms and persistence settings
- Contract-driven lifecycle management specifications

ZERO TOLERANCE: No Any types allowed in implementation.
"""

from typing import Any

from pydantic import BaseModel


class ModelLifecycleConfig(BaseModel):
    """
    EnumLifecycle management configuration for node initialization and cleanup.

    Defines initialization, error handling, state management and cleanup
    policies for contract-driven lifecycle management.
    """

    initialization_timeout_s: int = Field(
        default=30,
        description="Maximum time for node initialization in seconds",
        ge=1,
    )

    cleanup_timeout_s: int = Field(
        default=30,
        description="Maximum time for node cleanup in seconds",
        ge=1,
    )

    error_recovery_enabled: bool = Field(
        default=True,
        description="Enable automatic error recovery mechanisms",
    )

    state_persistence_enabled: bool = Field(
        default=False,
        description="Enable state persistence across restarts",
    )

    health_check_interval_s: int = Field(
        default=60,
        description="Health check interval in seconds",
        ge=1,
    )

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }
