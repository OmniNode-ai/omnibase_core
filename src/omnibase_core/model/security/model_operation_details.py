"""
ModelOperationDetails: Details about a security operation performed by a node.

This model captures structured information about operations performed
during envelope processing with type-safe fields.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class ModelOperationDetails(BaseModel):
    """Details about a security operation performed by a node."""

    routing_decision: Optional[str] = Field(None, description="Routing decision made")
    delivery_status: Optional[str] = Field(None, description="Delivery status")
    operation_time_ms: Optional[int] = Field(
        None, description="Operation duration in milliseconds"
    )
    bytes_processed: Optional[int] = Field(
        None, description="Number of bytes processed"
    )
    compression_ratio: Optional[float] = Field(
        None, description="Compression ratio achieved"
    )
    encryption_applied: Optional[bool] = Field(
        None, description="Whether encryption was applied"
    )
    algorithms_used: List[str] = Field(
        default_factory=list, description="Cryptographic algorithms used"
    )
    validation_passed: Optional[bool] = Field(
        None, description="Whether validation passed"
    )
    error_code: Optional[str] = Field(
        None, description="Error code if operation failed"
    )
    warning_codes: List[str] = Field(
        default_factory=list, description="Warning codes generated"
    )
