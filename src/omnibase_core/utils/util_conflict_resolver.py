"""
Conflict resolution utility for data reduction operations.

This module provides the UtilConflictResolver class that handles conflicts
during data reduction with configurable strategies including FIRST_WINS,
LAST_WINS, MERGE, ERROR, and CUSTOM.

Thread Safety:
    UtilConflictResolver is NOT thread-safe. Each thread should use its
    own instance. The conflicts_count attribute is mutated during resolution.

Key Features:
    - Multiple built-in conflict resolution strategies
    - Custom resolver support for domain-specific logic
    - Intelligent merging for numeric, string, list, and dict types
    - Conflict counting for metrics and debugging

Example:
    >>> from omnibase_core.utils.util_conflict_resolver import UtilConflictResolver
    >>> from omnibase_core.enums.enum_reducer_types import EnumConflictResolution
    >>>
    >>> # Use MERGE strategy for combining values
    >>> resolver = UtilConflictResolver(strategy=EnumConflictResolution.MERGE)
    >>> result = resolver.resolve(existing_value=10, new_value=5)
    >>> print(result)  # 15 (numeric values are summed)
    >>>
    >>> # Use custom resolver for domain-specific logic
    >>> def priority_resolver(existing, new, key):
    ...     return new if new.get("priority", 0) > existing.get("priority", 0) else existing
    >>>
    >>> custom_resolver = UtilConflictResolver(
    ...     strategy=EnumConflictResolution.CUSTOM,
    ...     custom_resolver=priority_resolver,
    ... )

See Also:
    - omnibase_core.models.reducer.model_reducer_input: Uses conflict resolution
    - omnibase_core.enums.enum_reducer_types.EnumConflictResolution: Strategy enum
"""

from collections.abc import Callable

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_reducer_types import EnumConflictResolution
from omnibase_core.models.errors.model_onex_error import ModelOnexError


class UtilConflictResolver:
    """
    Handles conflict resolution during data reduction.

    Provides configurable strategies for resolving conflicts when merging
    or reducing data with overlapping keys. Supports built-in strategies
    (FIRST_WINS, LAST_WINS, MERGE, ERROR) and custom resolution functions.

    Attributes:
        strategy: The conflict resolution strategy to use.
        custom_resolver: Optional custom resolution function for CUSTOM strategy.
            Signature: ``(existing_value, new_value, key) -> resolved_value``
        conflicts_count: Running count of conflicts resolved. Reset manually
            if needed between operations.

    Built-in Merge Behavior:
        - Numeric (int, float): Values are summed
        - Strings: Values are concatenated with ", " separator
        - Lists: Values are concatenated
        - Dicts: Values are shallow-merged (new overwrites existing keys)
        - Other types: New value replaces existing

    .. note::
        Previously named ``ModelConflictResolver``. Renamed in v0.4.0
        to follow ONEX naming conventions (OMN-1071). The ``Model``
        prefix is reserved for Pydantic BaseModel classes; ``Util``
        prefix indicates a utility class.
    """

    def __init__(
        self,
        strategy: EnumConflictResolution,
        custom_resolver: Callable[[object, object, str | None], object] | None = None,
    ):
        """
        Initialize conflict resolver.

        Args:
            strategy: Conflict resolution strategy to use
            custom_resolver: Optional custom resolution function for CUSTOM strategy.
                Signature: (existing_value, new_value, key) -> resolved_value

        Raises:
            ModelOnexError: If CUSTOM strategy is specified without a custom_resolver
        """
        if strategy == EnumConflictResolution.CUSTOM and custom_resolver is None:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="CUSTOM conflict resolution strategy requires a custom_resolver function",
                context={
                    "strategy": strategy.value,
                    "custom_resolver": "None",
                },
            )
        self.strategy = strategy
        self.custom_resolver = custom_resolver
        self.conflicts_count = 0

    def resolve(
        self,
        existing_value: object,
        new_value: object,
        key: str | None = None,
    ) -> object:
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

    def _merge_values(self, existing: object, new: object) -> object:
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


def __getattr__(name: str) -> type[UtilConflictResolver]:
    """
    Lazy loading for deprecated aliases per OMN-1071 renaming.

    Deprecated Aliases:
    -------------------
    All deprecated aliases emit DeprecationWarning when accessed:
    - ModelConflictResolver -> UtilConflictResolver (removed in v0.5.0)
    """
    import warnings

    if name == "ModelConflictResolver":
        warnings.warn(
            "'ModelConflictResolver' is deprecated, use 'UtilConflictResolver' "
            "from 'omnibase_core.utils.util_conflict_resolver' instead",
            DeprecationWarning,
            stacklevel=2,
        )
        return UtilConflictResolver

    raise AttributeError(  # error-ok: required for __getattr__ protocol
        f"module {__name__!r} has no attribute {name!r}"
    )
