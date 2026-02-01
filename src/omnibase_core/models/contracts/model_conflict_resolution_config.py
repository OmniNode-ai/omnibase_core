"""
Conflict Resolution Configuration Model.

Conflict resolution strategies and merge policies for NodeReducer implementations.
Defines conflict detection, resolution strategies, and merge policies for handling
data conflicts during reduction operations.

Part of the "one model per file" convention for clean architecture.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelConflictResolutionConfig(BaseModel):
    """
    Conflict resolution strategies and merge policies.

    Defines conflict detection, resolution strategies,
    and merge policies for handling data conflicts during reduction.
    """

    strategy: str = Field(
        default="last_writer_wins",
        description="Conflict resolution strategy (last_writer_wins, first_writer_wins, merge, manual)",
    )

    detection_enabled: bool = Field(
        default=True,
        description="Enable automatic conflict detection",
    )

    timestamp_based_resolution: bool = Field(
        default=True,
        description="Use timestamps for conflict resolution",
    )

    conflict_logging_enabled: bool = Field(
        default=True,
        description="Enable detailed conflict logging",
    )

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )
