"""TypedDict for binary computation output summary.

Provides strongly-typed summary return values for binary computation output,
replacing dict[str, Any] return types in get_binary_summary() methods.
"""

from typing import TypedDict


class TypedDictBinaryComputationSummary(TypedDict):
    """Summary of binary computation output.

    Attributes:
        result_count: Number of binary results
        total_size_bytes: Total size of binary data in bytes
        checksums_verified: Whether checksums have been verified
        compression_ratio: Compression ratio achieved
        data_integrity_status: Status of data integrity checks
        is_data_intact: Whether all data is intact
        compression_efficiency: Description of compression efficiency
    """

    result_count: int
    total_size_bytes: int
    checksums_verified: bool
    compression_ratio: float
    data_integrity_status: str
    is_data_intact: bool
    compression_efficiency: str


__all__ = ["TypedDictBinaryComputationSummary"]
