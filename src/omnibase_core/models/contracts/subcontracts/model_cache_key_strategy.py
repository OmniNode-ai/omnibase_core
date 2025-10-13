from pydantic import Field

"""
Cache Key Strategy Model - ONEX Standards Compliant.

Model for cache key generation strategies in the ONEX caching system.
"""

from pydantic import BaseModel


class ModelCacheKeyStrategy(BaseModel):
    """
    Cache key generation strategy.

    Defines how cache keys are generated,
    including namespacing, hashing, and versioning.
    """

    key_generation_method: str = Field(
        default=...,
        description="Method for generating cache keys",
        min_length=1,
    )

    namespace: str | None = Field(
        default=None,
        description="Namespace prefix for cache keys",
    )

    include_version: bool = Field(
        default=True,
        description="Include version in cache keys",
    )

    hash_algorithm: str = Field(
        default="sha256",
        description="Hash algorithm for key generation",
    )

    key_separator: str = Field(
        default=":",
        description="Separator for cache key components",
    )

    max_key_length: int = Field(
        default=250,
        description="Maximum length for cache keys",
        ge=1,
    )

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }
