# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Discover ONEX nodes registered via Python entry points."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from importlib.metadata import entry_points

from omnibase_core.errors.error_node_discovery import NodeDiscoveryError

logger = logging.getLogger(__name__)
ENTRY_POINT_GROUP = "onex.nodes"


@dataclass(frozen=True)
class DiscoveredNode:
    """Metadata for a discovered external node."""

    name: str
    node_class: type
    package_name: str
    package_version: str


def discover_external_nodes(*, strict: bool = False) -> dict[str, DiscoveredNode]:
    """Discover ONEX nodes registered via entry points.

    Args:
        strict: If True, raise on duplicate entry-point names.

    Returns:
        Dictionary mapping entry-point names to DiscoveredNode metadata.
    """
    discovered: dict[str, DiscoveredNode] = {}
    for ep in entry_points(group=ENTRY_POINT_GROUP):
        dist = ep.dist
        dist_name = dist.name if dist is not None else "unknown"
        dist_version = dist.version if dist is not None else "0.0.0"

        if ep.name in discovered:
            existing = discovered[ep.name]
            msg = (
                f"Duplicate entry-point name '{ep.name}': "
                f"registered by both '{existing.package_name}' and '{dist_name}'. "
                f"Keeping '{existing.package_name}' (first registered)."
            )
            if strict:
                raise NodeDiscoveryError(msg)
            logger.warning(msg)
            continue

        try:
            loaded = ep.load()
        except Exception:  # noqa: BLE001  # catch-all-ok: entry point loading can fail in many ways
            logger.warning(
                "Failed to load entry point '%s' from '%s'",
                ep.name,
                dist_name,
                exc_info=True,
            )
            continue

        if not _is_valid_node_class(loaded):
            logger.warning(
                "Entry point '%s' from '%s' is not a valid node class (got %s)",
                ep.name,
                dist_name,
                type(loaded).__name__,
            )
            continue

        discovered[ep.name] = DiscoveredNode(
            name=ep.name,
            node_class=loaded,
            package_name=dist_name,
            package_version=dist_version,
        )
        logger.info(
            "Discovered external node: %s from %s %s",
            ep.name,
            dist_name,
            dist_version,
        )
    return discovered


def _is_valid_node_class(obj: object) -> bool:
    """Check that a loaded object looks like a valid ONEX node class.

    A valid node class must be an actual class (not an instance or function)
    and must have either a ``process`` / ``handle`` method or a ``contract_path`` /
    ``__onex_node_type__`` attribute.

    Args:
        obj: The object loaded from an entry point.

    Returns:
        True if the object appears to be a valid ONEX node class.
    """
    if not isinstance(obj, type):
        return False
    has_process = callable(getattr(obj, "process", None))
    has_handle = callable(getattr(obj, "handle", None))
    has_contract = hasattr(obj, "contract_path") or hasattr(obj, "__onex_node_type__")
    return has_process or has_handle or has_contract
