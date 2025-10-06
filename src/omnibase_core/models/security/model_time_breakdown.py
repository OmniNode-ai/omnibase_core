from pydantic import BaseModel, Field


class ModelTimeBreakdown(BaseModel):
    """Time breakdown for signature verification operations."""

    total_time_ms: float = Field(
        default=0.0,
        description="Total verification time in milliseconds",
    )
    certificate_validation_ms: float = Field(
        default=0.0,
        description="Certificate validation time in milliseconds",
    )
    signature_verification_ms: float = Field(
        default=0.0,
        description="Signature verification time in milliseconds",
    )
    chain_validation_ms: float = Field(
        default=0.0,
        description="Chain validation time in milliseconds",
    )
    cache_lookup_ms: float = Field(
        default=0.0,
        description="Cache lookup time in milliseconds",
    )
    network_operations_ms: float = Field(
        default=0.0,
        description="Network operations time in milliseconds",
    )
