"""
Core-native core protocols.

This module provides protocol definitions for core operations including
canonical serialization. These are Core-native equivalents of the SPI
core protocols.

Design Principles:
- Protocol-first: Use typing.Protocol for interface definitions
- Minimal interfaces: Only define what Core actually needs
- Runtime checkable: Use @runtime_checkable for duck typing support
- Complete type hints: Full mypy strict mode compliance
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from omnibase_core.protocols.base import ContextValue

# =============================================================================
# Canonical Serializer Protocol
# =============================================================================


@runtime_checkable
class ProtocolCanonicalSerializer(Protocol):
    """
    Protocol for deterministic canonical serialization and content normalization.

    Provides consistent, reproducible serialization for metadata blocks and content
    bodies, enabling deterministic hash computation, content stamping, and idempotency
    verification across all ONEX components.

    Key Features:
        - Deterministic serialization output for identical logical content
        - Volatile field replacement with configurable placeholders
        - Line ending normalization (CRLF -> LF)
        - Trailing whitespace removal
        - EOF newline enforcement
        - Reproducible hash computation foundation

    Normalization Rules:
        - All line endings normalized to LF
        - Trailing spaces removed from each line
        - Exactly one newline at end of file
        - Consistent field ordering in metadata blocks
        - Volatile fields replaced with placeholders
    """

    def canonicalize_metadata_block(self, metadata_block: dict[str, object]) -> str:
        """
        Canonicalize a metadata block for deterministic serialization.

        Replaces volatile fields (e.g., hash, last_modified_at) with placeholders.

        Args:
            metadata_block: The metadata block to canonicalize

        Returns:
            Canonical serialized string
        """
        ...

    def normalize_body(self, body: str) -> str:
        """
        Canonical normalization for file body content.

        - Strips trailing spaces
        - Normalizes all line endings to '\\n'
        - Ensures exactly one newline at EOF

        Args:
            body: The body content to normalize

        Returns:
            Normalized body string
        """
        ...

    def canonicalize_for_hash(
        self,
        block: dict[str, ContextValue],
        body: str,
        volatile_fields: tuple[str, ...] = (
            "hash",
            "last_modified_at",
        ),
        placeholder: str | None = None,
        **kwargs: ContextValue,
    ) -> str:
        """
        Canonicalize full content (block + body) for hash computation.

        Args:
            block: The metadata block
            body: The body content
            volatile_fields: Fields to replace with placeholders
            placeholder: The placeholder value (default: protocol-defined)
            **kwargs: Additional context values

        Returns:
            Canonical string suitable for hashing
        """
        ...


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "ProtocolCanonicalSerializer",
]
