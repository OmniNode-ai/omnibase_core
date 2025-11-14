from pydantic import BaseModel, Field


class ModelCacheSizes(BaseModel):
    """Cache size information for monitoring."""

    signature_cache_size: int = Field(
        default=0,
        description="Number of cached signature results",
    )
    certificate_cache_size: int = Field(
        default=0,
        description="Number of cached certificate validations",
    )
    content_hash_cache_size: int = Field(
        default=0,
        description="Number of cached content hashes",
    )
    max_cache_size: int = Field(default=1000, description="Maximum cache size limit")
