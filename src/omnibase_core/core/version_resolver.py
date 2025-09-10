# === OmniNode:Metadata ===
# metadata_version: 0.1.0
# protocol_version: 1.1.0
# owner: OmniNode Team
# copyright: OmniNode Team
# schema_version: 1.1.0
# name: version_resolver.py
# version: 1.0.0
# uuid: ab0e5aea-80c7-404c-a08d-97fbcf51ca16
# author: OmniNode Team
# created_at: 2025-05-25T18:02:07.777556
# last_modified_at: 2025-05-25T22:11:50.171149
# description: Stamped by ToolPython
# state_contract: state_contract://default
# lifecycle: active
# hash: 6e2307a080abe47216c28978ea9f87137d73c2b4f399e80872a3bd34bc124d0d
# entrypoint: python@version_resolver.py
# runtime_language_hint: python>=3.11
# namespace: onex.stamped.version_resolver
# meta_type: tool
# === /OmniNode:Metadata ===


"""
Version Resolution Utilities for ONEX Nodes.

This module provides utilities for automatically resolving node versions,
discovering available versions, and managing version compatibility.
"""

import re
from pathlib import Path
from typing import Any

from packaging import version


class NodeVersionResolver:
    """
    Utility for resolving ONEX node versions automatically.

    Provides auto-discovery of latest versions, version compatibility checking,
    and simplified CLI interfaces without requiring explicit version numbers.
    """

    def __init__(self, nodes_directory: str = "src/omnibase_core/nodes"):
        """Initialize the version resolver with nodes directory."""
        self.nodes_directory = Path(nodes_directory)

    def discover_node_versions(self, node_name: str) -> list[str]:
        """
        Discover all available versions for a given node.

        Args:
            node_name: Name of the node to discover versions for

        Returns:
            List of version strings sorted from oldest to newest
        """
        node_path = self.nodes_directory / node_name
        if not node_path.exists():
            return []

        versions = []
        version_pattern = re.compile(r"^v(\d+)_(\d+)_(\d+)$")

        for version_dir in node_path.iterdir():
            if version_dir.is_dir() and version_pattern.match(version_dir.name):
                # Check if this version has a node.py file
                node_file = version_dir / "node.py"
                if node_file.exists():
                    versions.append(version_dir.name)

        # Sort versions using semantic versioning
        def version_key(v: str) -> version.Version:
            # Convert v1_2_3 to 1.2.3 for proper sorting
            match = version_pattern.match(v)
            if match:
                major, minor, patch = match.groups()
                return version.Version(f"{major}.{minor}.{patch}")
            return version.Version("0.0.0")

        return sorted(versions, key=version_key)

    def get_latest_version(self, node_name: str) -> str | None:
        """
        Get the latest version for a given node.

        Args:
            node_name: Name of the node

        Returns:
            Latest version string or None if no versions found
        """
        versions = self.discover_node_versions(node_name)
        return versions[-1] if versions else None

    def resolve_version(
        self,
        node_name: str,
        requested_version: str | None = None,
    ) -> str | None:
        """
        Resolve a version for a node, defaulting to latest if not specified.

        Args:
            node_name: Name of the node
            requested_version: Specific version requested, or None for latest

        Returns:
            Resolved version string or None if not found
        """
        if requested_version:
            # Validate that the requested version exists
            available_versions = self.discover_node_versions(node_name)
            if requested_version in available_versions:
                return requested_version
            return None
        # Return latest version
        return self.get_latest_version(node_name)

    def get_module_path(
        self,
        node_name: str,
        version: str | None = None,
    ) -> str | None:
        """
        Get the Python module path for a node, auto-resolving version if needed.

        Args:
            node_name: Name of the node
            version: Specific version or None for latest

        Returns:
            Module path string or None if not found
        """
        resolved_version = self.resolve_version(node_name, version)
        if resolved_version:
            return f"omnibase.nodes.{node_name}.{resolved_version}.node"
        return None

    def discover_all_nodes(self) -> dict[str, list[str]]:
        """
        Discover all nodes and their available versions.

        Returns:
            Dictionary mapping node names to lists of available versions
        """
        nodes: dict[str, list[str]] = {}

        if not self.nodes_directory.exists():
            return nodes

        for node_dir in self.nodes_directory.iterdir():
            if node_dir.is_dir() and not node_dir.name.startswith("."):
                versions = self.discover_node_versions(node_dir.name)
                if versions:
                    nodes[node_dir.name] = versions

        return nodes

    def get_version_info(self, node_name: str) -> dict[str, Any]:
        """
        Get comprehensive version information for a node.

        Args:
            node_name: Name of the node

        Returns:
            Dictionary with version information
        """
        versions = self.discover_node_versions(node_name)
        latest = self.get_latest_version(node_name)

        return {
            "node_name": node_name,
            "available_versions": versions,
            "latest_version": latest,
            "total_versions": len(versions),
            "module_path_latest": self.get_module_path(node_name) if latest else None,
            "version_status": {
                v: "latest" if v == latest else "supported" for v in versions
            },
        }


# Global resolver instance
global_resolver = NodeVersionResolver()


def resolve_node_version(
    node_name: str,
    version: str | None = None,
) -> str | None:
    """
    Resolve a node version, defaulting to latest if not specified.

    Args:
        node_name: Name of the node
        version: Specific version or None for latest

    Returns:
        Resolved version string or None if not found
    """
    return global_resolver.resolve_version(node_name, version)


def get_node_module_path(
    node_name: str,
    version: str | None = None,
) -> str | None:
    """
    Get the Python module path for a node with auto-version resolution.

    Args:
        node_name: Name of the node
        version: Specific version or None for latest

    Returns:
        Module path string or None if not found
    """
    return global_resolver.get_module_path(node_name, version)


def list_available_nodes() -> dict[str, list[str]]:
    """
    List all available nodes and their versions.

    Returns:
        Dictionary mapping node names to lists of available versions
    """
    return global_resolver.discover_all_nodes()


def get_node_version_info(node_name: str) -> dict[str, Any]:
    """
    Get comprehensive version information for a node.

    Args:
        node_name: Name of the node

    Returns:
        Dictionary with version information
    """
    return global_resolver.get_version_info(node_name)
