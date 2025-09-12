"""
Model for hash algorithm configuration used by metadata tools.
"""

from enum import Enum

from pydantic import BaseModel, Field, validator


class EnumHashAlgorithm(str, Enum):
    """Supported hash algorithms."""

    SHA256 = "sha256"
    SHA512 = "sha512"
    SHA1 = "sha1"
    MD5 = "md5"
    BLAKE2B = "blake2b"
    BLAKE2S = "blake2s"
    BLAKE3 = "blake3"


class ModelHashAlgorithm(BaseModel):
    """Model representing hash algorithm configuration."""

    algorithm: EnumHashAlgorithm = Field(..., description="Hash algorithm to use")

    encoding: str = Field("utf-8", description="Text encoding for string inputs")

    output_format: str = Field(
        "hex",
        description="Output format for hash",
        pattern="^(hex|base64|raw)$",
    )

    key: bytes | None = Field(
        None,
        description="Optional key for keyed hash algorithms (BLAKE2)",
    )

    digest_size: int | None = Field(
        None,
        description="Digest size for variable-length algorithms",
    )

    @validator("key")
    def validate_key_for_algorithm(self, v, values):
        """Ensure key is only provided for algorithms that support it."""
        algorithm = values.get("algorithm")
        if v is not None:
            if algorithm not in [EnumHashAlgorithm.BLAKE2B, EnumHashAlgorithm.BLAKE2S]:
                msg = f"Algorithm {algorithm} does not support keyed hashing"
                raise ValueError(
                    msg,
                )
        return v

    @validator("digest_size")
    def validate_digest_size(self, v, values):
        """Validate digest size for algorithms that support it."""
        if v is not None:
            algorithm = values.get("algorithm")
            if algorithm == EnumHashAlgorithm.BLAKE2B and (v < 1 or v > 64):
                msg = "BLAKE2B digest size must be between 1 and 64"
                raise ValueError(msg)
            if algorithm == EnumHashAlgorithm.BLAKE2S and (v < 1 or v > 32):
                msg = "BLAKE2S digest size must be between 1 and 32"
                raise ValueError(msg)
            if algorithm not in [
                EnumHashAlgorithm.BLAKE2B,
                EnumHashAlgorithm.BLAKE2S,
            ]:
                msg = f"Algorithm {algorithm} does not support variable digest size"
                raise ValueError(
                    msg,
                )
        return v
