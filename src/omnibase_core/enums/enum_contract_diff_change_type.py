"""
Contract Diff Change Type Enum.

Defines the types of changes that can occur between contract versions
during semantic diffing operations.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumContractDiffChangeType(StrValueHelper, str, Enum):
    """
    Types of changes detected during contract diff operations.

    This enum classifies the type of change that occurred to a field
    or element when comparing two versions of a contract. It supports
    bidirectional diff operations through the get_reverse() method.

    Attributes:
        ADDED: A new field or element was added to the contract.
        REMOVED: An existing field or element was removed from the contract.
        MODIFIED: A field's value was changed between versions.
        MOVED: An element changed position within a list (same identity key).
        UNCHANGED: The field or element has the same value in both versions.

    Example:
        >>> change = EnumContractDiffChangeType.ADDED
        >>> change.is_change
        True
        >>> change.get_reverse()
        <EnumContractDiffChangeType.REMOVED: 'removed'>

        >>> unchanged = EnumContractDiffChangeType.UNCHANGED
        >>> unchanged.is_change
        False
    """

    ADDED = "added"
    """A new field or element was added to the contract."""

    REMOVED = "removed"
    """An existing field or element was removed from the contract."""

    MODIFIED = "modified"
    """A field's value was changed between versions."""

    MOVED = "moved"
    """An element changed position within a list (identified by identity key)."""

    UNCHANGED = "unchanged"
    """The field or element has the same value in both versions."""

    @property
    def is_change(self) -> bool:
        """
        Check if this change type represents an actual modification.

        Returns:
            True if the change type indicates a modification (ADDED, REMOVED,
            MODIFIED, or MOVED), False if UNCHANGED.

        Example:
            >>> EnumContractDiffChangeType.ADDED.is_change
            True
            >>> EnumContractDiffChangeType.UNCHANGED.is_change
            False
        """
        return self != EnumContractDiffChangeType.UNCHANGED

    def get_reverse(self) -> "EnumContractDiffChangeType":
        """
        Get the reverse change type for bidirectional diff operations.

        This is useful when computing the inverse diff (what changes would
        reverse the diff). ADDED becomes REMOVED and vice versa. Other
        change types remain the same when reversed.

        Returns:
            The reverse change type:
            - ADDED -> REMOVED
            - REMOVED -> ADDED
            - MODIFIED -> MODIFIED
            - MOVED -> MOVED
            - UNCHANGED -> UNCHANGED

        Example:
            >>> EnumContractDiffChangeType.ADDED.get_reverse()
            <EnumContractDiffChangeType.REMOVED: 'removed'>
            >>> EnumContractDiffChangeType.REMOVED.get_reverse()
            <EnumContractDiffChangeType.ADDED: 'added'>
            >>> EnumContractDiffChangeType.MODIFIED.get_reverse()
            <EnumContractDiffChangeType.MODIFIED: 'modified'>
        """
        if self == EnumContractDiffChangeType.ADDED:
            return EnumContractDiffChangeType.REMOVED
        if self == EnumContractDiffChangeType.REMOVED:
            return EnumContractDiffChangeType.ADDED
        return self


__all__ = ["EnumContractDiffChangeType"]
