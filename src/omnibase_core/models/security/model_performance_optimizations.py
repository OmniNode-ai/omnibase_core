from pydantic import BaseModel, Field


class ModelPerformanceOptimizations(BaseModel):
    """Performance optimization settings and status."""

    certificate_cached: bool = Field(
        default=False,
        description="Whether certificate was cached",
    )
    signature_cached: bool = Field(
        default=False,
        description="Whether signature was cached",
    )
    trusted_node: bool = Field(
        default=False,
        description="Whether node is in trusted list[Any]",
    )
    parallel_verification: bool = Field(
        default=False,
        description="Whether parallel verification was used",
    )
    fast_path: bool = Field(
        default=False,
        description="Whether fast verification path was used",
    )
