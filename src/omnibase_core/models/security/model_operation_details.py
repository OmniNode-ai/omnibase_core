"""
ModelOperationDetails: Details about a security operation performed by a node.

This model captures structured information about operations performed
during envelope processing with type-safe fields.
"""

from pydantic import BaseModel, Field


class ModelOperationDetails(BaseModel):
    """Details about a security operation performed by a node."""

    routing_decision: str | None = Field(
        default=None, description="Routing decision made"
    )
    delivery_status: str | None = Field(default=None, description="Delivery status")
    operation_time_ms: int | None = Field(
        default=None,
        description="Operation duration in milliseconds",
    )
    bytes_processed: int | None = Field(
        default=None,
        description="Number of bytes processed",
    )
    compression_ratio: float | None = Field(
        default=None,
        description="Compression ratio achieved",
    )
    encryption_applied: bool | None = Field(
        default=None,
        description="Whether encryption was applied",
    )
    algorithms_used: list[str] = Field(
        default_factory=list,
        description="Cryptographic algorithms used",
    )
    validation_passed: bool | None = Field(
        default=None,
        description="Whether validation passed",
    )
    error_code: str | None = Field(
        default=None,
        description="Error code if operation failed",
    )
    warning_codes: list[str] = Field(
        default_factory=list,
        description="Warning codes generated",
    )
