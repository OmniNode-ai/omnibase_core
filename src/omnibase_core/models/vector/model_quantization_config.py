"""Vector quantization configuration model.

This module provides the ModelQuantizationConfig class for vector quantization settings.

Thread Safety:
    ModelQuantizationConfig instances are immutable (frozen=True) after creation,
    making them thread-safe for concurrent read access.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelQuantizationConfig(BaseModel):
    """Vector quantization configuration for memory optimization.

    Quantization reduces memory usage by compressing vector representations.

    Attributes:
        enabled: Whether quantization is enabled.
        type: Quantization type (scalar, product, binary).
        bits: Number of bits for scalar quantization (4, 8, 16).

    Example:
        >>> config = ModelQuantizationConfig(enabled=True, type="scalar", bits=8)
    """

    enabled: bool = Field(
        default=False,
        description="Whether quantization is enabled",
    )
    type: str = Field(
        default="scalar",
        description="Quantization type (scalar, product, binary)",
    )
    bits: int = Field(
        default=8,
        ge=4,
        le=16,
        description="Number of bits for quantization (4, 8, 16)",
    )

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)


__all__ = ["ModelQuantizationConfig"]
