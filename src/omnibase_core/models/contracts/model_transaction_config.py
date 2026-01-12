"""
Transaction Configuration Model.

Defines transaction isolation, rollback policies,
and consistency guarantees for side-effect operations.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelTransactionConfig(BaseModel):
    """
    Transaction management configuration.

    Defines transaction isolation, rollback policies,
    and consistency guarantees for side-effect operations.
    """

    enabled: bool = Field(default=True, description="Enable transaction management")

    isolation_level: str = Field(
        default="read_committed",
        description="Transaction isolation level",
    )

    timeout_seconds: int = Field(
        default=30,
        description="Transaction timeout in seconds",
        ge=1,
    )

    rollback_on_error: bool = Field(
        default=True,
        description="Automatically rollback on error",
    )

    lock_timeout_seconds: int = Field(
        default=10,
        description="Lock acquisition timeout in seconds",
        ge=1,
    )

    deadlock_retry_count: int = Field(
        default=3,
        description="Number of retries for deadlock resolution",
        ge=0,
    )

    consistency_check_enabled: bool = Field(
        default=True,
        description="Enable consistency checking before commit",
    )

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )


__all__ = ["ModelTransactionConfig"]
