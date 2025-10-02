#!/usr/bin/env python3
"""
Manifest-based Service Runner

Discovers tools via manifests and runs them as services automatically.
No need to specify module paths - uses tool manifests for discovery.
"""

import asyncio
import importlib
import os
import signal
import sys
import time
from pathlib import Path
from types import FrameType

from omnibase_core.core.errors.core_errors import CoreErrorCode
from omnibase_core.core.tool_manifest_discovery import (
    ToolManifest,
    ToolManifestDiscovery,
)
from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.exceptions import OnexError
from omnibase_core.logging.structured import emit_log_event_sync as emit_log_event

# Configuration constants
DEFAULT_EVENT_BUS_URL = os.getenv("EVENT_BUS_URL", "http://localhost:8083")
DEFAULT_LOG_LEVEL = "INFO"
SERVICE_ERROR_EXIT_CODE = 1
SIGINT_EXIT_CODE = 130


class ManifestServiceRunner:
    """Service runner that uses tool manifests for discovery and startup."""

    def __init__(self, domain: str | None = None, base_path: Path | None = None):
        """
        Initialize the manifest service runner.

        Args:
            domain: Domain to run tools for (e.g., 'generation'). If None, runs all domains.
            base_path: Base path for tool discovery
        """
        self.domain = domain
        self.discovery = ToolManifestDiscovery(base_path)
        self.running_tools: dict[str, object] = {}  # tool_name -> node_instance
        self.stop_requested = False
        self.introspection_handler = None

        emit_log_event(
            LogLevel.INFO,
            "🚀 Manifest Service Runner initialized",
            {"domain": domain or "all", "base_path": str(self.discovery.base_path)},
        )

    async def start_all_tools(self) -> None:
        """Start all active tools for the specified domain."""

        # Discover active tools
        active_tools = self.discovery.get_active_tools(self.domain)

        if not active_tools:
            emit_log_event(
                LogLevel.WARNING,
                "⚠️ No active tools found for startup",
                {"domain": self.domain or "all"},
            )
            return

        emit_log_event(
            LogLevel.INFO,
            f"🎯 Starting {len(active_tools)} tools",
            {"tool_count": len(active_tools), "tools": [t.name for t in active_tools]},
        )

        # Start each tool
        for manifest in active_tools:
            try:
                await self._start_tool(manifest)
            except Exception as e:
                emit_log_event(
                    LogLevel.ERROR,
                    f"❌ Failed to start {manifest.name}: {e!s}",
                    {
                        "tool_name": manifest.name,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                )

        emit_log_event(
            LogLevel.INFO,
            f"✅ Service startup complete. Running {len(self.running_tools)} tools",
            {"running_tools": list(self.running_tools.keys())},
        )

        # Set up introspection handler after all tools are started
        await self._setup_introspection_handler()

    async def _start_tool(self, manifest: ToolManifest) -> None:
        """Start a single tool from its manifest."""

        # Get current version info
        current_version = manifest.current_version
        if current_version not in manifest.versions:
            raise OnexError(
                code=CoreErrorCode.VALIDATION_ERROR,
                message=f"Current version {current_version} not found in manifest",
                details={
                    "tool_name": manifest.name,
                    "available_versions": list(manifest.versions.keys()),
                },
            )

        version_info = manifest.versions[current_version]

        if version_info.status != "active":
            emit_log_event(
                LogLevel.WARNING,
                f"⚠️ Skipping {manifest.name}: version {current_version} is {version_info.status}",
                {
                    "tool_name": manifest.name,
                    "version": current_version,
                    "status": version_info.status,
                },
            )
            return

        emit_log_event(
            LogLevel.INFO,
            f"🔧 Starting {manifest.name} {current_version}",
            {
                "tool_name": manifest.name,
                "version": current_version,
                "module": version_info.node_module,
            },
        )

        try:
            # Security: validate module is within allowed namespaces
            allowed_prefixes = [
                "omnibase_core.",
                "omnibase_spi.",
                "omnibase.",
                # Add other trusted prefixes as needed
            ]
            if not any(
                version_info.node_module.startswith(prefix)
                for prefix in allowed_prefixes
            ):
                raise OnexError(
                    code=CoreErrorCode.VALIDATION_ERROR,
                    message=f"Module path not in allowed namespace: {version_info.node_module}",
                    details={
                        "module_path": version_info.node_module,
                        "allowed_prefixes": allowed_prefixes,
                        "tool_name": manifest.name,
                    },
                )

            # Import and create the tool
            module = importlib.import_module(version_info.node_module)

            # For service mode, we need to directly create the ModelNodeBase instance
            # instead of going through main() which has argparse
            from pathlib import Path

            # Resolve event bus adapter from DI container
            from omnibase_core.core.registry_bootstrap import BootstrapRegistry
            from omnibase_core.infrastructure.node_base import ModelNodeBase

            registry = BootstrapRegistry()
            event_bus_adapter = registry.discover_event_bus_implementation()

            # Find the contract.yaml for this tool
            module_file = module.__file__
            if module_file is None:
                raise OnexError(
                    code=CoreErrorCode.VALIDATION_ERROR,
                    message=f"Module {manifest.name} has no __file__ attribute",
                )
            tool_dir = Path(module_file).parent
            contract_path = tool_dir / "contract.yaml"

            if not contract_path.exists():
                raise OnexError(
                    code=CoreErrorCode.VALIDATION_ERROR,
                    message=f"Contract file not found for {manifest.name}",
                    details={"expected_path": str(contract_path)},
                )

            # Create ModelNodeBase instance directly for service mode
            node = ModelNodeBase(
                contract_path=contract_path,
                event_bus=event_bus_adapter,
            )

            # Set up event bus
            await self._setup_event_bus(node, manifest)

            # Store the running tool
            tool_info: dict[str, object] = {
                "node": node,
                "manifest": manifest,
                "started_at": time.time(),
            }
            self.running_tools[manifest.name] = tool_info

            # Log introspection capabilities
            emit_log_event(
                LogLevel.INFO,
                f"🔍 Checking introspection capabilities for {manifest.name}",
                {
                    "tool_name": manifest.name,
                    "has_introspection_mixin": hasattr(
                        node,
                        "_setup_request_response_introspection",
                    ),
                    "has_event_bus": hasattr(node, "_event_bus")
                    and node._event_bus is not None,
                    "has_cached_introspection": hasattr(node, "_cached_introspection"),
                    "node_name": getattr(node, "node_name", "unknown"),
                    "node_id": getattr(node, "_node_id", "unknown"),
                },
            )

            emit_log_event(
                LogLevel.INFO,
                f"✅ {manifest.name} started successfully",
                {
                    "tool_name": manifest.name,
                    "version": current_version,
                    "event_patterns": manifest.service_config.get("event_patterns", []),
                },
            )

        except Exception as e:
            raise OnexError(
                code=CoreErrorCode.OPERATION_FAILED,
                message=f"Failed to start {manifest.name}: {e!s}",
                details={
                    "tool_name": manifest.name,
                    "module": version_info.node_module,
                },
            ) from e

    async def _setup_event_bus(self, node: object, manifest: ToolManifest) -> None:
        """Set up event bus connection for a tool node."""

        # Get event bus URL from environment or service config
        event_bus_url = os.getenv("EVENT_BUS_URL", DEFAULT_EVENT_BUS_URL)
        service_env = manifest.service_config.get("environment", [])

        # Parse environment variables from manifest
        for env_var in service_env:
            if "EVENT_BUS_URL=" in env_var and "${EVENT_BUS_URL" not in env_var:
                # Extract hardcoded URL from manifest
                event_bus_url = env_var.split("EVENT_BUS_URL=")[1]
                break

        emit_log_event(
            LogLevel.INFO,
            f"🌐 Connecting {manifest.name} to event bus",
            {"tool_name": manifest.name, "event_bus_url": event_bus_url},
        )

        # Import event bus components
        from omnibase_core.services.event_bus_adapter import EventBusAdapter
        from omnibase_core.services.event_bus_client import EventBusClient

        # Create event bus client
        event_bus_client = EventBusClient(event_bus_url)
        event_bus_client.start_websocket_connection()

        # Wait for connection
        connected = await asyncio.to_thread(
            event_bus_client.wait_for_connection,
            timeout=30,
        )

        if not connected:
            raise OnexError(
                code=CoreErrorCode.SERVICE_INITIALIZATION_FAILED,
                message=f"Failed to connect to Event Bus at {event_bus_url}",
            )

        # Create adapter and inject into node
        event_bus_adapter = EventBusAdapter(event_bus_url)

        if hasattr(node, "event_bus"):
            node.event_bus = event_bus_adapter
        if hasattr(node, "_event_bus"):
            node._event_bus = event_bus_adapter

        # Start event listener
        if hasattr(node, "start_event_listener") and callable(
            node.start_event_listener,
        ):
            node.start_event_listener()

            emit_log_event(
                LogLevel.INFO,
                f"🔔 Event listener started for {manifest.name}",
                {
                    "tool_name": manifest.name,
                    "event_patterns": manifest.service_config.get("event_patterns", []),
                },
            )

    async def run_forever(self) -> None:
        """Run all tools and keep them running until stopped."""

        # Set up signal handlers
        def signal_handler(signum: int, frame: FrameType | None) -> None:
            emit_log_event(
                LogLevel.INFO,
                f"📡 Received signal {signum}, initiating graceful shutdown",
                {"signal": signum, "running_tools": len(self.running_tools)},
            )
            self.stop_requested = True

        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)

        try:
            # Start all tools
            await self.start_all_tools()

            if not self.running_tools:
                emit_log_event(
                    LogLevel.WARNING,
                    "⚠️ No tools started, exiting",
                    {"domain": self.domain or "all"},
                )
                return

            emit_log_event(
                LogLevel.INFO,
                f"🎉 All tools running! Monitoring {len(self.running_tools)} services...",
                {"tools": list(self.running_tools.keys())},
            )

            # Monitor and keep running
            while not self.stop_requested:
                await asyncio.sleep(1)

                # Health check (could be expanded)
                if len(self.running_tools) == 0:
                    emit_log_event(
                        LogLevel.ERROR,
                        "❌ All tools have stopped, exiting",
                        {},
                    )
                    break

        except KeyboardInterrupt:
            emit_log_event(LogLevel.INFO, "⌨️ Keyboard interrupt received", {})
            self.stop_requested = True

        finally:
            await self._shutdown_all_tools()

    async def _setup_introspection_handler(self) -> None:
        """Set up introspection request handler for the manifest runner."""

        emit_log_event(
            LogLevel.INFO,
            f"📡 Setting up introspection handler for {len(self.running_tools)} tools",
            {"running_tools": list(self.running_tools.keys())},
        )

        # Log detailed info about each running tool
        for tool_name, tool_info in self.running_tools.items():
            if isinstance(tool_info, dict) and "node" in tool_info:
                node = tool_info["node"]
                emit_log_event(
                    LogLevel.INFO,
                    f"🔍 Tool {tool_name} introspection status",
                    {
                        "tool_name": tool_name,
                        "node_id": getattr(node, "_node_id", "unknown"),
                        "node_name": getattr(node, "node_name", "unknown"),
                        "has_introspection_setup": hasattr(
                            node,
                            "_setup_request_response_introspection",
                        ),
                        "has_handle_introspection": hasattr(
                            node,
                            "_handle_introspection_request",
                        ),
                        "event_bus_connected": hasattr(node, "_event_bus")
                        and node._event_bus is not None,
                        "mixins": [base.__name__ for base in node.__class__.__bases__],
                    },
                )
            else:
                emit_log_event(
                    LogLevel.WARNING,
                    f"⚠️ Tool {tool_name} has invalid tool_info structure",
                    {
                        "tool_name": tool_name,
                        "tool_info_type": type(tool_info).__name__,
                    },
                )

    async def _shutdown_all_tools(self) -> None:
        """Gracefully shutdown all running tools."""
        emit_log_event(
            LogLevel.INFO,
            f"🛑 Shutting down {len(self.running_tools)} tools",
            {"tools": list(self.running_tools.keys())},
        )

        for tool_name, tool_info in self.running_tools.items():
            try:
                if isinstance(tool_info, dict) and "node" in tool_info:
                    node = tool_info["node"]
                    if hasattr(node, "stop_event_listener"):
                        node.stop_event_listener()

                    emit_log_event(
                        LogLevel.INFO,
                        f"✅ Stopped {tool_name}",
                        {"tool_name": tool_name},
                    )
                else:
                    emit_log_event(
                        LogLevel.WARNING,
                        f"⚠️ Cannot stop {tool_name}: invalid tool_info structure",
                        {"tool_name": tool_name},
                    )

            except Exception as e:
                emit_log_event(
                    LogLevel.ERROR,
                    f"❌ Error stopping {tool_name}: {e!s}",
                    {"tool_name": tool_name, "error": str(e)},
                )

        self.running_tools.clear()


async def main() -> None:
    """Main entry point for manifest service runner."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Run ONEX tools using manifest discovery",
    )
    parser.add_argument("--domain", help="Domain to run tools for (e.g., 'generation')")
    parser.add_argument("--base-path", help="Base path for tool discovery")
    parser.add_argument(
        "--list-only",
        action="store_true",
        help="Just list discovered tools",
    )

    args = parser.parse_args()

    try:
        base_path = Path(args.base_path) if args.base_path else None
        runner = ManifestServiceRunner(args.domain, base_path)

        if args.list_only:
            # Just show what would be started
            active_tools = runner.discovery.get_active_tools(args.domain)
            for tool in active_tools:
                tool.versions[tool.current_version]
        else:
            # Run the tools
            await runner.run_forever()

    except Exception as e:
        emit_log_event(LogLevel.ERROR, f"❌ Service runner failed: {e!s}")
        sys.exit(SERVICE_ERROR_EXIT_CODE)


if __name__ == "__main__":
    asyncio.run(main())
