#!/usr/bin/env python3
"""
Tool Manifest Discovery Service

Discovers and manages tool manifests for automatic service startup and management.
"""

from dataclasses import dataclass
from pathlib import Path

import yaml
from omnibase.protocols.types import LogLevel

from omnibase_core.core.core_error_codes import CoreErrorCode
from omnibase_core.core.core_structured_logging import (
    emit_log_event_sync as emit_log_event,
)
from omnibase_core.exceptions import OnexError


@dataclass
class ToolVersionInfo:
    """Information about a specific tool version."""

    status: str
    node_module: str
    contract_path: str
    released: str
    features: list[str] = None
    deprecated_on: str | None = None


@dataclass
class ToolManifest:
    """Complete tool manifest information."""

    name: str
    domain: str
    description: str
    current_version: str
    tier: int
    classification: str
    versions: dict[str, ToolVersionInfo]
    service_config: dict
    manifest_path: Path


class ToolManifestDiscovery:
    """Service for discovering and managing tool manifests."""

    def __init__(self, base_path: Path | None = None):
        """
        Initialize tool manifest discovery.

        Args:
            base_path: Base path to search for tools (defaults to src/omnibase/tools)
        """
        if base_path is None:
            # Try to find src/omnibase/tools from current working directory
            cwd = Path.cwd()

            # Look for src/omnibase/tools relative to current directory
            possible_paths = [
                cwd / "src" / "omnibase" / "tools",
                cwd / "omnibase" / "tools",
                Path(__file__).parent.parent / "tools",
            ]

            for path in possible_paths:
                if path.exists() and path.is_dir():
                    base_path = path
                    break

            if base_path is None:
                raise OnexError(
                    code=CoreErrorCode.VALIDATION_ERROR,
                    message="Could not find tools directory. Please specify base_path.",
                    details={"searched_paths": [str(p) for p in possible_paths]},
                )

        self.base_path = Path(base_path)
        emit_log_event(
            LogLevel.INFO,
            "🔍 Tool manifest discovery initialized",
            {"base_path": str(self.base_path)},
        )

    def discover_all_manifests(self) -> list[ToolManifest]:
        """
        Discover all tool manifests in the base path.

        Returns:
            List of discovered tool manifests
        """
        manifests = []

        emit_log_event(
            LogLevel.INFO,
            f"🔎 Scanning for tool manifests in {self.base_path}",
            {"base_path": str(self.base_path)},
        )

        # Walk through all subdirectories looking for tool_manifest.yaml
        for manifest_file in self.base_path.rglob("tool_manifest.yaml"):
            try:
                manifest = self._load_manifest(manifest_file)
                manifests.append(manifest)

                emit_log_event(
                    LogLevel.INFO,
                    f"✅ Loaded manifest for {manifest.name}",
                    {
                        "tool_name": manifest.name,
                        "domain": manifest.domain,
                        "current_version": manifest.current_version,
                        "manifest_path": str(manifest_file),
                    },
                )

            except Exception as e:
                emit_log_event(
                    LogLevel.ERROR,
                    f"❌ Failed to load manifest: {manifest_file}",
                    {"manifest_path": str(manifest_file), "error": str(e)},
                )

        emit_log_event(
            LogLevel.INFO,
            f"🎯 Discovery complete: found {len(manifests)} tool manifests",
            {"manifest_count": len(manifests)},
        )

        return manifests

    def discover_by_domain(self, domain: str) -> list[ToolManifest]:
        """
        Discover tool manifests for a specific domain.

        Args:
            domain: Domain to filter by (e.g., 'generation', 'management')

        Returns:
            List of tool manifests in the specified domain
        """
        all_manifests = self.discover_all_manifests()
        domain_manifests = [m for m in all_manifests if m.domain == domain]

        emit_log_event(
            LogLevel.INFO,
            f"📋 Found {len(domain_manifests)} tools in '{domain}' domain",
            {
                "domain": domain,
                "tool_count": len(domain_manifests),
                "tools": [m.name for m in domain_manifests],
            },
        )

        return domain_manifests

    def get_active_tools(self, domain: str | None = None) -> list[ToolManifest]:
        """
        Get all tools with auto_start enabled.

        Args:
            domain: Optional domain filter

        Returns:
            List of tools that should be auto-started
        """
        if domain:
            manifests = self.discover_by_domain(domain)
        else:
            manifests = self.discover_all_manifests()

        active_tools = []
        for manifest in manifests:
            if manifest.service_config.get("auto_start", False):
                # Check if current version is active
                current_version = manifest.current_version
                if current_version in manifest.versions:
                    version_info = manifest.versions[current_version]
                    if version_info.status == "active":
                        active_tools.append(manifest)

        emit_log_event(
            LogLevel.INFO,
            f"🚀 Found {len(active_tools)} tools configured for auto-start",
            {
                "domain": domain,
                "active_tool_count": len(active_tools),
                "tools": [t.name for t in active_tools],
            },
        )

        return active_tools

    def _load_manifest(self, manifest_path: Path) -> ToolManifest:
        """
        Load a tool manifest from a YAML file.

        Args:
            manifest_path: Path to the tool_manifest.yaml file

        Returns:
            Parsed ToolManifest object
        """
        try:
            with open(manifest_path) as f:
                data = yaml.safe_load(f)

            # Parse tool metadata
            tool_meta = data["tool_metadata"]

            # Parse versions
            versions = {}
            for version_name, version_data in data["versions"].items():
                versions[version_name] = ToolVersionInfo(
                    status=version_data["status"],
                    node_module=version_data["node_module"],
                    contract_path=version_data["contract_path"],
                    released=version_data["released"],
                    features=version_data.get("features", []),
                    deprecated_on=version_data.get("deprecated_on"),
                )

            # Create manifest object
            return ToolManifest(
                name=tool_meta["name"],
                domain=tool_meta["domain"],
                description=tool_meta["description"],
                current_version=tool_meta["current_version"],
                tier=tool_meta.get("tier", 1),
                classification=tool_meta.get("classification", "general"),
                versions=versions,
                service_config=data.get("service_config", {}),
                manifest_path=manifest_path,
            )

        except Exception as e:
            raise OnexError(
                code=CoreErrorCode.OPERATION_FAILED,
                message=f"Failed to parse tool manifest: {e!s}",
                details={
                    "manifest_path": str(manifest_path),
                    "error_type": type(e).__name__,
                },
            ) from e


def main():
    """CLI entry point for tool manifest discovery."""
    import argparse

    parser = argparse.ArgumentParser(description="Discover ONEX tool manifests")
    parser.add_argument("--domain", help="Filter by domain")
    parser.add_argument(
        "--active-only",
        action="store_true",
        help="Show only auto-start tools",
    )
    parser.add_argument("--base-path", help="Base path to search for tools")

    args = parser.parse_args()

    # Initialize discovery
    base_path = Path(args.base_path) if args.base_path else None
    discovery = ToolManifestDiscovery(base_path)

    # Get manifests
    if args.active_only:
        manifests = discovery.get_active_tools(args.domain)
    elif args.domain:
        manifests = discovery.discover_by_domain(args.domain)
    else:
        manifests = discovery.discover_all_manifests()

    # Display results
    for manifest in manifests:
        manifest.versions[manifest.current_version]
        "🚀" if manifest.service_config.get("auto_start") else "⏹️"


if __name__ == "__main__":
    main()
