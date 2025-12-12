"""
Binary Computation Output Model.

Binary data computation output with integrity verification and compression tracking.
"""

from pydantic import Field

from omnibase_core.enums.enum_computation_type import EnumComputationType
from omnibase_core.models.operations.model_computation_output_base import (
    ModelComputationOutputBase,
)
from omnibase_core.types.typed_dict_binary_computation_summary import (
    TypedDictBinaryComputationSummary,
)


class ModelBinaryComputationOutput(ModelComputationOutputBase):
    """Binary data computation output."""

    computation_type: EnumComputationType = Field(
        default=EnumComputationType.BINARY,
        description="Binary computation type",
    )
    binary_results: dict[str, bytes] = Field(
        default_factory=dict,
        description="Binary computation results",
    )
    checksums_verified: bool = Field(
        default=True,
        description="Whether all checksums were verified",
    )
    compression_ratio: float = Field(
        default=1.0,
        description="Achieved compression ratio",
    )
    data_integrity_status: str = Field(
        default="verified",
        description="Data integrity status",
    )

    def add_binary_result(
        self, key: str, value: bytes
    ) -> "ModelBinaryComputationOutput":
        """Add a binary result."""
        new_results = {**self.binary_results, key: value}
        return self.model_copy(update={"binary_results": new_results})

    def get_binary_result(self, key: str) -> bytes | None:
        """Get a binary result by key."""
        return self.binary_results.get(key)

    def set_checksums_verified(self, verified: bool) -> "ModelBinaryComputationOutput":
        """Set checksum verification status."""
        return self.model_copy(update={"checksums_verified": verified})

    def set_compression_ratio(self, ratio: float) -> "ModelBinaryComputationOutput":
        """Set compression ratio."""
        return self.model_copy(update={"compression_ratio": ratio})

    def set_data_integrity_status(self, status: str) -> "ModelBinaryComputationOutput":
        """Set data integrity status."""
        return self.model_copy(update={"data_integrity_status": status})

    def is_data_intact(self) -> bool:
        """Check if data integrity is verified."""
        return self.checksums_verified and self.data_integrity_status == "verified"

    def is_compressed(self) -> bool:
        """Check if data was compressed."""
        return self.compression_ratio < 1.0

    def get_compression_efficiency(self) -> str:
        """Get compression efficiency description."""
        if self.compression_ratio >= 1.0:
            return "no_compression"
        elif self.compression_ratio >= 0.5:
            return "good_compression"
        elif self.compression_ratio >= 0.3:
            return "excellent_compression"
        else:
            return "outstanding_compression"

    def get_total_size_bytes(self) -> int:
        """Get total size of all binary results in bytes."""
        return sum(len(data) for data in self.binary_results.values())

    def get_binary_summary(self) -> TypedDictBinaryComputationSummary:
        """Get binary processing summary."""
        return TypedDictBinaryComputationSummary(
            result_count=len(self.binary_results),
            total_size_bytes=self.get_total_size_bytes(),
            checksums_verified=self.checksums_verified,
            compression_ratio=self.compression_ratio,
            data_integrity_status=self.data_integrity_status,
            is_data_intact=self.is_data_intact(),
            compression_efficiency=self.get_compression_efficiency(),
        )
