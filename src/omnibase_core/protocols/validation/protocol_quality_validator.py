"""
Protocol definition for quality validation operations.

This module provides the ProtocolQualityValidator protocol which validates
code quality including metrics, issues, and standards.

Design Principles:
- Protocol-first: Use typing.Protocol for interface definitions
- Minimal interfaces: Only define what Core actually needs
- Runtime checkable: Use @runtime_checkable for duck typing support
- Complete type hints: Full mypy strict mode compliance
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from omnibase_core.protocols.validation.protocol_validation_result import (
        ProtocolValidationResult,
    )


@runtime_checkable
class ProtocolQualityValidator(Protocol):
    """
    Protocol for quality validation operations.

    Validates code quality including metrics, issues, and standards.
    """

    async def validate_quality(
        self, file_path: str, content: str | None = None
    ) -> ProtocolValidationResult:
        """
        Validate quality for a file.

        Args:
            file_path: Path to the file
            content: Optional content override

        Returns:
            Validation result
        """
        ...


__all__ = ["ProtocolQualityValidator"]
