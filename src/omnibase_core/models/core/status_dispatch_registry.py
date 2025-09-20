"""
Status Dispatch Registry.

Registry pattern for mapping enum values to status check functions,
replacing large boolean method chains with maintainable dispatch tables.
"""

from typing import Any, Callable, Dict, Set, TypeVar

from omnibase_core.enums.enum_metadata_node_complexity import EnumMetadataNodeComplexity
from omnibase_core.enums.enum_metadata_node_status import EnumMetadataNodeStatus

# Type variable for enum types
E = TypeVar("E")


class StatusDispatchRegistry:
    """
    Registry for status-based dispatch patterns.

    Replaces large if/elif chains with maintainable registry tables
    that map enum values to corresponding check functions.
    """

    def __init__(self) -> None:
        """Initialize dispatch registry."""
        self._status_checks: Dict[EnumMetadataNodeStatus, Callable[[], bool]] = {}
        self._complexity_checks: Dict[EnumMetadataNodeComplexity, Callable[[], bool]] = {}
        self._status_sets: Dict[str, Set[EnumMetadataNodeStatus]] = {}
        self._complexity_sets: Dict[str, Set[EnumMetadataNodeComplexity]] = {}

        # Initialize predefined sets
        self._initialize_status_sets()
        self._initialize_complexity_sets()

    def register_status_check(
        self,
        status: EnumMetadataNodeStatus,
        check_func: Callable[[], bool]
    ) -> None:
        """
        Register a status check function.

        Args:
            status: Status enum value
            check_func: Function to check for this status
        """
        self._status_checks[status] = check_func

    def register_complexity_check(
        self,
        complexity: EnumMetadataNodeComplexity,
        check_func: Callable[[], bool]
    ) -> None:
        """
        Register a complexity check function.

        Args:
            complexity: Complexity enum value
            check_func: Function to check for this complexity
        """
        self._complexity_checks[complexity] = check_func

    def check_status(self, status: EnumMetadataNodeStatus) -> bool:
        """
        Check if current instance matches the given status.

        Args:
            status: Status to check

        Returns:
            True if status matches
        """
        check_func = self._status_checks.get(status)
        return check_func() if check_func else False

    def check_complexity(self, complexity: EnumMetadataNodeComplexity) -> bool:
        """
        Check if current instance matches the given complexity.

        Args:
            complexity: Complexity to check

        Returns:
            True if complexity matches
        """
        check_func = self._complexity_checks.get(complexity)
        return check_func() if check_func else False

    def check_status_group(self, group_name: str) -> bool:
        """
        Check if current status is in the named group.

        Args:
            group_name: Name of status group

        Returns:
            True if current status is in group
        """
        status_set = self._status_sets.get(group_name, set())
        return any(self.check_status(status) for status in status_set)

    def check_complexity_group(self, group_name: str) -> bool:
        """
        Check if current complexity is in the named group.

        Args:
            group_name: Name of complexity group

        Returns:
            True if current complexity is in group
        """
        complexity_set = self._complexity_sets.get(group_name, set())
        return any(self.check_complexity(complexity) for complexity in complexity_set)

    def _initialize_status_sets(self) -> None:
        """Initialize predefined status groups."""
        self._status_sets = {
            "operational": {
                EnumMetadataNodeStatus.ACTIVE,
                EnumMetadataNodeStatus.STABLE,
            },
            "development": {
                EnumMetadataNodeStatus.EXPERIMENTAL,
            },
            "inactive": {
                EnumMetadataNodeStatus.DEPRECATED,
                EnumMetadataNodeStatus.DISABLED,
            },
        }

    def _initialize_complexity_sets(self) -> None:
        """Initialize predefined complexity groups."""
        self._complexity_sets = {
            "simple": {
                EnumMetadataNodeComplexity.SIMPLE,
            },
            "moderate": {
                EnumMetadataNodeComplexity.MODERATE,
            },
            "complex": {
                EnumMetadataNodeComplexity.COMPLEX,
                EnumMetadataNodeComplexity.ADVANCED,
            },
        }

    def get_available_status_groups(self) -> list[str]:
        """Get list of available status group names."""
        return list(self._status_sets.keys())

    def get_available_complexity_groups(self) -> list[str]:
        """Get list of available complexity group names."""
        return list(self._complexity_sets.keys())

    def get_statuses_in_group(self, group_name: str) -> Set[EnumMetadataNodeStatus]:
        """Get status enum values in a group."""
        return self._status_sets.get(group_name, set()).copy()

    def get_complexities_in_group(self, group_name: str) -> Set[EnumMetadataNodeComplexity]:
        """Get complexity enum values in a group."""
        return self._complexity_sets.get(group_name, set()).copy()


# Export for use
__all__ = ["StatusDispatchRegistry"]