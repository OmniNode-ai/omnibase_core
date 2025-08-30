"""
Model for hash computation results.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from .model_hash_algorithm import EnumHashAlgorithm


class ModelHashResult(BaseModel):
    """Model representing the result of a hash computation."""

    hash_value: str = Field(..., description="Computed hash value")

    algorithm: EnumHashAlgorithm = Field(
        ..., description="Algorithm used for hash computation"
    )

    input_size: int = Field(..., description="Size of input data in bytes")

    output_format: str = Field(
        ..., description="Format of the hash output (hex, base64, etc.)"
    )

    computed_at: datetime = Field(
        default_factory=datetime.utcnow, description="Timestamp when hash was computed"
    )

    encoding_used: Optional[str] = Field(
        None, description="Text encoding used if input was string"
    )

    digest_size: int = Field(..., description="Size of the hash digest in bytes")

    is_keyed: bool = Field(False, description="Whether a key was used for hashing")
