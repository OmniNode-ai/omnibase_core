"""
Conflict resolution model for data reduction operations.

Handles conflict resolution during data reduction with configurable strategies.

Author: ONEX Framework Team
"""

from collections.abc import Callable
from typing import Any

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_reducer_types import EnumConflictResolution
from omnibase_core.models.errors.model_onex_error import ModelOnexError


class ModelConflictResolver:
    """
    Handles conflict resolution during data reduction.

    Provides configurable strategies for resolving conflicts when
    merging or reducing data with overlapping keys.
    """

    def __init__(
        self,
        strategy: EnumConflictResolution,
        custom_resolver: Callable[..., Any] | None = None,
    ):
        """
        Initialize conflict resolver.

        Args:
            strategy: Conflict resolution strategy to use
            custom_resolver: Optional custom resolution function for CUSTOM strategy
        """
        self.strategy = strategy
        self.custom_resolver = custom_resolver
        self.conflicts_count = 0

    def resolve(
        self,
        existing_value: Any,
        new_value: Any,
        key: str | None = None,
    ) -> Any:
        """
        Resolve conflict between existing and new values.

        Args:
            existing_value: Current value
            new_value: New conflicting value
            key: Optional key for context in error messages

        Returns:
            Resolved value based on strategy

        Raises:
            ModelOnexError: If conflict resolution fails with ERROR strategy
        """
        self.conflicts_count += 1

        if self.strategy == EnumConflictResolution.FIRST_WINS:
            return existing_value
        if self.strategy == EnumConflictResolution.LAST_WINS:
            return new_value
        if self.strategy == EnumConflictResolution.MERGE:
            return self._merge_values(existing_value, new_value)
        if self.strategy == EnumConflictResolution.ERROR:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Conflict detected for key: {key}",
                context={
                    "existing_value": str(existing_value),
                    "new_value": str(new_value),
                    "key": key,
                },
            )
        if self.strategy == EnumConflictResolution.CUSTOM and self.custom_resolver:
            return self.custom_resolver(existing_value, new_value, key)
        # Default to last wins
        return new_value

    def _merge_values(self, existing: Any, new: Any) -> Any:
        """
        Attempt to merge two values intelligently.

        Args:
            existing: Existing value
            new: New value to merge

        Returns:
            Merged value
        """
        # Handle numeric values
        if isinstance(existing, int | float) and isinstance(new, int | float):
            return existing + new

        # Handle string concatenation
        if isinstance(existing, str) and isinstance(new, str):
            return f"{existing}, {new}"

        # Handle list merging
        if isinstance(existing, list) and isinstance(new, list):
            return existing + new

        # Handle dict merging
        if isinstance(existing, dict) and isinstance(new, dict):
            merged = existing.copy()
            merged.update(new)
            return merged

        # Default to new value if can't merge
        return new
