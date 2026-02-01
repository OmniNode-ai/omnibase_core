"""
State Synchronization Model.

Individual model for state synchronization configuration.
Part of the State Management Subcontract Model family.

Strict typing is enforced: No Any types allowed in implementation.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.constants import TIMEOUT_DEFAULT_MS, TIMEOUT_MIN_MS
from omnibase_core.enums.enum_state_management import (
    EnumConflictResolution,
    EnumConsistencyLevel,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelStateSynchronization(BaseModel):
    """
    State synchronization configuration.

    Defines synchronization policies for distributed
    state management and consistency guarantees.
    """

    # Model version for instance tracking
    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Subcontract version (auto-generated if not provided)",
    )

    synchronization_enabled: bool = Field(
        default=False,
        description="Enable state synchronization",
    )

    consistency_level: EnumConsistencyLevel = Field(
        default=EnumConsistencyLevel.EVENTUAL,
        description="Consistency level for distributed state",
    )

    sync_interval_ms: int = Field(
        default=TIMEOUT_DEFAULT_MS,
        description="Synchronization interval",
        ge=TIMEOUT_MIN_MS,
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

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )
