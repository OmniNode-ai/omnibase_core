from pydantic import Field

"""
State Synchronization Model - ONEX Standards Compliant.

Individual model for state synchronization configuration.
Part of the State Management Subcontract Model family.

ZERO TOLERANCE: No Any types allowed in implementation.
"""

from typing import Any

from pydantic import BaseModel

from omnibase_core.enums.enum_state_management import (
    EnumConflictResolution,
    EnumConsistencyLevel,
)


class ModelStateSynchronization(BaseModel):
    """
    State synchronization configuration.

    Defines synchronization policies for distributed
    state management and consistency guarantees.
    """

    synchronization_enabled: bool = Field(
        default=False,
        description="Enable state synchronization",
    )

    consistency_level: EnumConsistencyLevel = Field(
        default=EnumConsistencyLevel.EVENTUAL,
        description="Consistency level for distributed state",
    )

    sync_interval_ms: int = Field(
        default=30000,
        description="Synchronization interval",
        ge=1000,
    )

    conflict_resolution: EnumConflictResolution = Field(
        default=EnumConflictResolution.TIMESTAMP_BASED,
        description="Conflict resolution strategy",
    )

    replication_factor: int = Field(
        default=1,
        description="Number of state replicas",
        ge=1,
    )

    leader_election_enabled: bool = Field(
        default=False,
        description="Enable leader election for coordination",
    )

    distributed_locking: bool = Field(
        default=False,
        description="Enable distributed locking for state access",
    )

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }
