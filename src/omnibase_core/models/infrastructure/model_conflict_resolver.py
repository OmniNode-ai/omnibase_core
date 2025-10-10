from typing import Callable

from omnibase_core.errors.model_onex_error import ModelOnexError

"""Conflict resolver model for handling data conflicts during reduction."""

from collections.abc import Callable as CallableABC
from typing import Any, Callable

from omnibase_core.enums.enum_conflict_resolution import EnumConflictResolution
from omnibase_core.errors.error_codes import EnumCoreErrorCode


class ModelConflictResolver:
    """
    Handles conflict resolution during data reduction.
    """

    def __init__(
        self,
        strategy: EnumConflictResolution,
        custom_resolver: Callable[..., Any] | None = None,
    ):
        self.strategy = strategy
        self.custom_resolver = custom_resolver
        self.conflicts_count = 0

    def resolve(
        self,
        existing_value: Any,
        new_value: Any,
        key: str | None = None,
    ) -> Any:
        """Resolve conflict between existing and new values."""
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
        """Attempt to merge two values intelligently."""
        # Handle numeric values
        if isinstance(existing, int | float) and isinstance(new, int | float):
            return existing + new

        # Handle string concatenation
        if isinstance(existing, str) and isinstance(new, str):
            return f"{existing}, {new}"

        # Handle list[Any]merging
        if isinstance(existing, list) and isinstance(new, list):
            return existing + new

        # Handle dict[str, Any]merging
        if isinstance(existing, dict) and isinstance(new, dict):
            merged = existing.copy()
            merged.update(new)
            return merged

        # Default to new value if can't merge
        return new
