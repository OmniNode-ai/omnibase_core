"""
Shared utilities for contract profile factories.

This module contains internal utility functions used by the profile factory
modules. These functions are implementation details and should not be
imported directly by external code.

Thread Safety:
    All functions in this module are stateless and thread-safe.
"""

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors import OnexError
from omnibase_core.models.contracts.subcontracts.model_event_type_subcontract import (
    ModelEventTypeSubcontract,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer

__all__ = [
    "_create_minimal_event_type_subcontract",
    "_parse_version",
]


def _create_minimal_event_type_subcontract(
    version: ModelSemVer,
    primary_events: list[str],
    event_categories: list[str],
    subscribe_events: bool = False,
) -> ModelEventTypeSubcontract:
    """
    Create a minimal valid event type subcontract for node profiles.

    Provides basic event configuration for node participation
    in event-driven workflows.

    Args:
        version: The semantic version for the subcontract.
        primary_events: List of primary event names (e.g., ["compute_started", "compute_completed"]).
        event_categories: List of event category names (e.g., ["compute", "processing"]).
        subscribe_events: Whether the node subscribes to events. Defaults to False.

    Returns:
        A ModelEventTypeSubcontract with the specified configuration.

    Example:
        >>> version = ModelSemVer(major=1, minor=0, patch=0)
        >>> subcontract = _create_minimal_event_type_subcontract(
        ...     version=version,
        ...     primary_events=["compute_started", "compute_completed"],
        ...     event_categories=["compute", "processing"],
        ... )
    """
    return ModelEventTypeSubcontract(
        version=version,
        primary_events=primary_events,
        event_categories=event_categories,
        publish_events=True,
        subscribe_events=subscribe_events,
        event_routing="default",
    )


def _parse_version(version: str) -> ModelSemVer:
    """
    Parse a version string into a ModelSemVer instance.

    Args:
        version: A version string in "major.minor.patch" format.
                 Missing components default to 0 (except major defaults to 1).

    Returns:
        A ModelSemVer instance with parsed major, minor, patch values.

    Raises:
        OnexError: If the version string is empty or contains non-numeric
            components. Uses VALIDATION_ERROR error code.

    Example:
        >>> _parse_version("1.2.3")
        ModelSemVer(major=1, minor=2, patch=3)
        >>> _parse_version("2.0")
        ModelSemVer(major=2, minor=0, patch=0)
    """
    if not version or not version.strip():
        raise OnexError(
            message="Version string cannot be empty",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        )

    parts = version.split(".")

    try:
        return ModelSemVer(
            major=int(parts[0]) if len(parts) > 0 else 1,
            minor=int(parts[1]) if len(parts) > 1 else 0,
            patch=int(parts[2]) if len(parts) > 2 else 0,
        )
    except ValueError as e:
        raise OnexError(
            message=f"Invalid version string '{version}': version components must be numeric integers",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        ) from e
