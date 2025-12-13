"""
Strongly-typed binary computation input model.

Represents binary data inputs for computation operations.
Follows ONEX strong typing principles and one-model-per-file architecture.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from omnibase_core.enums.enum_computation_type import EnumComputationType
from omnibase_core.models.operations.model_computation_input_base import (
    ModelComputationInputBase,
)


class ModelBinaryComputationInput(ModelComputationInputBase):
    """
    Strongly-typed binary computation input for computation operations.

    Represents binary data inputs with format and compression specifications.
    """

    computation_type: Literal[EnumComputationType.BINARY] = Field(
        default=EnumComputationType.BINARY,
        description="Binary computation type discriminator",
    )
    binary_format: str = Field(default=..., description="Binary data format")
    compression_algorithm: str = Field(
        default="none",
        description="Compression algorithm used",
    )
    checksum_verification: bool = Field(
        default=True,
        description="Whether to verify data checksums",
    )
    byte_order: str = Field(
        default="big_endian",
        description="Byte order for binary data",
    )


# Export for use
__all__ = ["ModelBinaryComputationInput"]
