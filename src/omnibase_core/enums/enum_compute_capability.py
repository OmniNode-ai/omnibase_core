"""
Compute Capability Enumeration.

Defines the available capabilities for COMPUTE nodes in the ONEX four-node architecture.
COMPUTE nodes handle data processing and transformation including calculations,
validations, and data mapping.
"""

from __future__ import annotations

from enum import Enum, unique
from typing import Never, NoReturn

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumComputeCapability(StrValueHelper, str, Enum):
    """
    Enumeration of supported compute node capabilities.

    SINGLE SOURCE OF TRUTH for compute capability values.
    Replaces magic strings in handler capability constants.

    Using an enum instead of raw strings:
    - Prevents typos ("transform" vs "Transform")
    - Enables IDE autocompletion
    - Provides exhaustiveness checking
    - Centralizes capability definitions
    - Preserves full type safety

    Capabilities:
        TRANSFORM: Data transformation operations
        VALIDATE: Data validation operations

    Example:
        >>> from omnibase_core.enums import EnumComputeCapability
        >>> cap = EnumComputeCapability.TRANSFORM
        >>> str(cap)
        'transform'
        >>> cap.value
        'transform'
    """

    TRANSFORM = "transform"
    """Data transformation operations."""

    VALIDATE = "validate"
    """Data validation operations."""

    @classmethod
    def values(cls) -> list[str]:
        """Return all capability values as strings."""
        return [member.value for member in cls]

    @staticmethod
    def assert_exhaustive(value: Never) -> NoReturn:
        """Ensures exhaustive handling of all enum values in match statements.

        This method enables static type checkers to verify that all enum values
        are handled in match/case statements. If a case is missing, mypy will
        report an error at the call site.

        Usage:
            match capability:
                case EnumComputeCapability.TRANSFORM:
                    handle_transform()
                case EnumComputeCapability.VALIDATE:
                    handle_validate()
                case _ as unreachable:
                    EnumComputeCapability.assert_exhaustive(unreachable)

        Args:
            value: The unhandled enum value (typed as Never for exhaustiveness).

        Raises:
            AssertionError: Always raised if this code path is reached at runtime.
        """
        # error-ok: exhaustiveness check - enums cannot import models
        raise AssertionError(f"Unhandled enum value: {value}")


__all__ = ["EnumComputeCapability"]
