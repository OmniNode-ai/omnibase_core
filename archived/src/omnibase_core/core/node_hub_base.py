"""
NodeHubBase - Universal Hub Implementation for ONEX Contract-Driven Hubs.

This module provides the NodeHubBase class that eliminates code duplication
across all ONEX hubs (AI, Generation, Quality, etc.) by providing a single
contract-driven hub implementation. All hubs should inherit from this class
and be thin wrappers that only specify their contract path.

Key features:
- Contract-driven configuration (domain, port, managed tools)
- Automatic service registry with domain filtering
- Event bus integration with introspection handling
- FastAPI HTTP server with health endpoints
- Tool loading and management from contract
- Standardized hub architecture

Author: ONEX Framework Team
"""

import logging
import os
import sys
import time
from pathlib import Path
from uuid import uuid4

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from omnibase_core.constants.contract_constants import CONTRACT_FILENAME
from omnibase_core.core.onex_container import ModelONEXContainer
from omnibase_core.decorators import standard_error_handling
from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.enums.enum_onex_status import EnumOnexStatus
from omnibase_core.infrastructure.node_base import ModelNodeBase
from omnibase_core.logging.structured import emit_log_event_sync as emit_log_event
from omnibase_core.mixin.mixin_debug_discovery_logging import MixinDebugDiscoveryLogging
from omnibase_core.mixin.mixin_service_registry import MixinServiceRegistry
from omnibase_core.models.core.model_hub_contract_config import ModelUnifiedHubContract

logger = logging.getLogger(__name__)


class NodeHubBase(ModelNodeBase, MixinServiceRegistry, MixinDebugDiscoveryLogging):
    """
    Universal hub base class for contract-driven hub implementation.

    This class provides all common hub functionality:
    - Contract-driven configuration loading
    - Service registry with domain filtering
    - Event bus integration and introspection
    - FastAPI HTTP server with standard endpoints
    - Tool loading and management
    - Health monitoring and metrics

    Subclasses only need to provide the contract path.
    """

    def __init__(self, container: ModelONEXContainer, contract_path: Path):
        """
        Initialize hub with contract-driven configuration.

        Args:
            container: ModelONEXContainer from ModelNodeBase
            contract_path: Path to the hub contract file
        """
        # Load hub configuration from contract
        self.contract_path = contract_path
        self.unified_contract = self._load_unified_contract()
        self.hub_config = self.unified_contract.get_unified_config()

        # Extract configuration from unified contract
        self.domain = self.unified_contract.get_domain()
        self.hub_port = self.unified_contract.get_service_port()
        self.managed_tools = self.unified_contract.get_managed_tools()
        self.capabilities = self.unified_contract.get_capabilities()
        self.coordination_mode = self.unified_contract.get_coordination_mode()

        # Initialize service registry with domain filter
        MixinServiceRegistry.__init__(
            self,
            introspection_timeout=self.hub_config.introspection_timeout,
            service_ttl=self.hub_config.service_ttl,
            auto_cleanup_interval=self.hub_config.auto_cleanup_interval,
        )

        # Store container for service access
        self.container = container

        # Hub state management
        self.loaded_tools: dict[str, dict] = {}
        self.loaded_workflows: dict[str, dict] = {}
        self.is_running = False
        self.start_time = None
        self.hub_id = f"{self.domain}_hub_{uuid4().hex[:8]}"

        # Performance metrics
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.average_response_time = 0.0

        emit_log_event(
            LogLevel.INFO,
            f"{self.domain.title()} Hub initialized with contract-driven configuration",
            {
                "domain": self.domain,
                "port": self.hub_port,
                "managed_tools": len(self.managed_tools),
                "hub_id": self.hub_id,
            },
        )

        # Initialize debug discovery logging
        self.setup_discovery_debug_logging(
            f"{self.domain}_hub",
            {"domain": self.domain, "hub_id": self.hub_id},
        )

    def _load_unified_contract(self) -> ModelUnifiedHubContract:
        """Load unified hub contract from file."""
        try:
            if not self.contract_path.exists():
                msg = f"Hub contract not found: {self.contract_path}"
                raise FileNotFoundError(msg)

            # Use the unified contract model to load from YAML
            return ModelUnifiedHubContract.from_yaml_file(self.contract_path)

        except Exception as e:
            logger.exception(f"Failed to load hub contract: {e}")
            # Return minimal default configuration
            from omnibase_core.models.core.model_hub_contract_config import (
                ModelHubConfiguration,
            )

            default_config = ModelHubConfiguration(
                domain="unknown",
                service_port=8080,
                managed_tools=[],
            )
            return ModelUnifiedHubContract(hub_configuration=default_config)

    @standard_error_handling("Hub request processing")
    def process(self, input_state: dict) -> dict:
        """
        Process hub requests with standardized error handling.

        Args:
            input_state: Hub input state with action and parameters

        Returns:
            Hub processing results
        """
        start_time = time.time()
        self.total_requests += 1

        try:
            action = input_state.get("action", "health_check")

            emit_log_event(
                LogLevel.INFO,
                f"Processing {self.domain} hub action: {action}",
                {"hub_id": self.hub_id, "action": action},
            )

            # Route to appropriate handler
            if action == "start_hub":
                result = self._start_hub()
            elif action == "stop_hub":
                result = self._stop_hub()
            elif action == "health_check":
                result = self._health_check()
            elif action == "list_tools":
                result = self._list_tools()
            elif action == "reload_tools":
                result = self._reload_tools()
            else:
                msg = f"Unsupported hub action: {action}"
                raise ValueError(msg)

            # Update success metrics
            self.successful_requests += 1
            self._update_response_time_metrics(time.time() - start_time)

            return {
                "status": EnumOnexStatus.SUCCESS,
                "message": f"{self.domain.title()} hub action completed successfully: {action}",
                "hub_status": "ready",
                **result,
            }

        except Exception as e:
            self.failed_requests += 1
            self._update_response_time_metrics(time.time() - start_time)

            emit_log_event(
                LogLevel.ERROR,
                f"Error in {self.domain} hub: {e!s}",
                {"hub_id": self.hub_id, "error": str(e)},
            )

            return {
                "status": EnumOnexStatus.ERROR,
                "message": f"{self.domain.title()} hub processing error: {e!s}",
                "hub_status": "error",
            }

    def _start_hub(self) -> dict:
        """Start the hub with service registry and tool loading."""
        self.start_time = time.time()
        self.is_running = True

        # Load managed tools from contract
        self._load_managed_tools()

        # Load workflows if present
        self._load_workflows()

        emit_log_event(
            LogLevel.INFO,
            f"{self.domain.title()} Hub started successfully",
            {
                "hub_id": self.hub_id,
                "tools_loaded": len(self.loaded_tools),
                "workflows_loaded": len(self.loaded_workflows),
            },
        )

        return {
            "tools_loaded": len(self.loaded_tools),
            "workflows_loaded": len(self.loaded_workflows),
            "uptime": 0,
        }

    def _stop_hub(self) -> dict:
        """Stop the hub and clear loaded tools."""
        self.is_running = False
        self.loaded_tools.clear()
        self.loaded_workflows.clear()

        return {
            "tools_loaded": 0,
            "workflows_loaded": 0,
            "uptime": time.time() - self.start_time if self.start_time else 0,
        }

    def _health_check(self) -> dict:
        """Perform hub health check."""
        uptime = time.time() - self.start_time if self.start_time else 0

        return {
            "status": "healthy",
            "domain": self.domain,
            "uptime_seconds": uptime,
            "tools_loaded": len(self.loaded_tools),
            "workflows_loaded": len(self.loaded_workflows),
            "total_requests": self.total_requests,
            "success_rate": (self.successful_requests / max(self.total_requests, 1))
            * 100,
            "average_response_time": self.average_response_time,
        }

    def _list_tools(self) -> dict:
        """List all loaded tools."""
        return {
            "tools": list(self.loaded_tools.keys()),
            "tool_count": len(self.loaded_tools),
            "workflows": list(self.loaded_workflows.keys()),
            "workflow_count": len(self.loaded_workflows),
        }

    def _reload_tools(self) -> dict:
        """Reload tools from contract."""
        old_count = len(self.loaded_tools)
        self._load_managed_tools()
        new_count = len(self.loaded_tools)

        return {
            "tools_reloaded": new_count,
            "tools_added": max(0, new_count - old_count),
            "tools_removed": max(0, old_count - new_count),
        }

    def _load_managed_tools(self) -> dict[str, dict]:
        """Load managed tools from contract configuration."""
        try:
            loaded_tools = {}

            for tool_name in self.managed_tools:
                try:
                    # Simple tool registration - tools register themselves
                    # via service discovery when the hub starts
                    loaded_tools[tool_name] = {
                        "name": tool_name,
                        "status": "registered",
                        "domain": self.domain,
                        "loaded_at": time.time(),
                    }
                except Exception as e:
                    logger.warning(f"Failed to register tool {tool_name}: {e}")

            self.loaded_tools.update(loaded_tools)

            emit_log_event(
                LogLevel.INFO,
                f"Loaded {len(loaded_tools)} managed tools for {self.domain} domain",
                {"domain": self.domain, "tools_loaded": len(loaded_tools)},
            )

            return loaded_tools

        except Exception as e:
            logger.exception(f"Failed to load managed tools: {e}")
            return {}

    def _load_workflows(self) -> dict[str, dict]:
        """Load workflows from unified contract configuration."""
        try:
            workflows = self.unified_contract.orchestration_workflows or {}
            self.loaded_workflows.update(workflows)

            emit_log_event(
                LogLevel.INFO,
                f"Loaded {len(workflows)} workflows for {self.domain} domain",
                {"domain": self.domain, "workflows_loaded": len(workflows)},
            )

            return workflows

        except Exception as e:
            logger.exception(f"Failed to load workflows: {e}")
            return {}

    def _update_response_time_metrics(self, response_time: float):
        """Update average response time metrics."""
        if self.total_requests == 1:
            self.average_response_time = response_time
        else:
            # Moving average calculation
            self.average_response_time = (
                self.average_response_time * (self.total_requests - 1) + response_time
            ) / self.total_requests

    def create_fastapi_app(self) -> FastAPI:
        """Create FastAPI application with standardized endpoints."""
        app = FastAPI(
            title=f"{self.domain.title()} Hub",
            version="1.0.0",
            description=f"ONEX {self.domain} domain hub for tool orchestration and service discovery",
        )

        @app.get("/health")
        async def health_check():
            """Health check endpoint."""
            try:
                health_result = self._health_check()
                return JSONResponse(
                    content={
                        "status": "healthy",
                        "hub_status": "ready",
                        "message": f"{self.domain.title()} hub is running",
                        **health_result,
                    },
                )
            except Exception as e:
                logger.exception(f"Health check failed: {e}")
                raise HTTPException(
                    status_code=503,
                    detail=f"Health check failed: {e!s}",
                )

        @app.get("/tools")
        async def list_tools():
            """List all registered tools."""
            try:
                tools_result = self._list_tools()
                return JSONResponse(content=tools_result)
            except Exception as e:
                logger.exception(f"Failed to list tools: {e}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to list tools: {e!s}",
                )

        @app.get("/metrics")
        async def get_metrics():
            """Get hub performance metrics."""
            try:
                health_result = self._health_check()
                return JSONResponse(
                    content={"hub_metrics": health_result, "domain": self.domain},
                )
            except Exception as e:
                logger.exception(f"Failed to get metrics: {e}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to get metrics: {e!s}",
                )

        return app

    def run_persistent_hub(self):
        """Run the hub as a persistent service."""
        try:
            logger.info(f"🔄 Starting {self.domain} hub in persistent service mode...")

            # Initialize hub with event bus connection
            self._initialize_hub_with_event_bus()

            # Create and configure FastAPI app
            app = self.create_fastapi_app()

            # Start the hub
            result = self.process({"action": "start_hub"})
            logger.info(f"✅ {self.domain.title()} hub initialized successfully")

            if result and result.get("status") == EnumOnexStatus.SUCCESS:
                logger.info(f"Hub status: {result.get('message', 'Running')}")

        except Exception as e:
            logger.exception(f"❌ Failed to initialize {self.domain} hub: {e}")
            raise

        # Get port and host from environment or contract
        host = os.getenv("HUB_API_HOST", "0.0.0.0")
        port = int(os.getenv("HUB_API_PORT", str(self.hub_port)))

        logger.info(f"🚀 Starting {self.domain} hub HTTP server on {host}:{port}")

        # Run the server
        uvicorn.run(app, host=host, port=port, log_level="info")

    def _initialize_hub_with_event_bus(self):
        """Initialize the hub with event bus connection."""
        try:
            logger.info(f"Initializing {self.domain} hub with service registry...")

            # Get the tool instance and inject event bus
            tool_instance = getattr(self.container, "_main_tool", self)

            # Try to get event bus from container providers with enhanced error handling
            event_bus = None

            # First try event_bus_client provider with detailed diagnostics
            if hasattr(self.container, "event_bus_client"):
                try:
                    logger.info(
                        "🔍 Attempting to resolve event_bus_client provider...",
                    )

                    # Check if provider is callable
                    provider = self.container.event_bus_client
                    logger.info(f"📋 event_bus_client provider type: {type(provider)}")

                    # Attempt to resolve the provider
                    event_bus = self.container.event_bus_client()
                    logger.info("✅ Successfully resolved event_bus_client provider")
                    logger.info(f"📦 Event bus type: {type(event_bus).__name__}")

                except ImportError as e:
                    logger.exception(
                        f"❌ Import error in event_bus_client provider: {e}",
                    )
                    logger.info("🔄 Attempting manual EventBusClient import...")
                    # Fallback: Try manual import and creation
                    try:
                        import os

                        from omnibase_core.services.event_bus_client import (
                            EventBusClient,
                        )

                        event_bus_url = os.getenv(
                            "EVENT_BUS_URL",
                            "http://onex-event-bus:8080",
                        )
                        event_bus = EventBusClient(base_url=event_bus_url)
                        logger.info(
                            f"✅ Successfully created EventBusClient manually with URL: {event_bus_url}",
                        )
                    except Exception as manual_e:
                        logger.exception(
                            f"❌ Manual EventBusClient creation failed: {manual_e}",
                        )

                except Exception as e:
                    logger.exception(
                        f"❌ event_bus_client provider resolution failed: {e}",
                    )
                    logger.exception(f"📋 Exception type: {type(e).__name__}")
                    logger.exception(f"📋 Exception details: {e!s}")

                    # Try to debug container configuration
                    try:
                        config_dict = dict(self.container.config)
                        logger.info(
                            f"🔧 Container config available: {bool(config_dict)}",
                        )
                        if hasattr(self.container.config, "event_bus"):
                            event_bus_config = getattr(
                                self.container.config,
                                "event_bus",
                                None,
                            )
                            logger.info(f"🔧 Event bus config: {event_bus_config}")
                    except Exception as config_e:
                        logger.warning(f"⚠️ Cannot inspect container config: {config_e}")
            else:
                logger.warning("⚠️ Container does not have event_bus_client provider")
                logger.info(
                    f"📋 Available container attributes: {[attr for attr in dir(self.container) if not attr.startswith('_')]}",
                )

            # Fallback to legacy event_bus attribute
            if not event_bus:
                logger.info("🔄 Trying legacy event_bus attribute fallback...")
                event_bus = getattr(self.container, "event_bus", None)
                if event_bus:
                    logger.info("✅ Found legacy event_bus attribute in container")
                else:
                    logger.warning("⚠️ No legacy event_bus attribute found")

            # Final fallback: Create EventBusClient directly
            if not event_bus:
                logger.info("🔄 Final fallback: Creating EventBusClient directly...")
                try:
                    import os

                    from omnibase_core.services.event_bus_client import EventBusClient

                    event_bus_url = os.getenv(
                        "EVENT_BUS_URL",
                        "http://onex-event-bus:8080",
                    )
                    event_bus = EventBusClient(base_url=event_bus_url)
                    logger.info(
                        f"✅ Created EventBusClient as final fallback with URL: {event_bus_url}",
                    )
                except Exception as fallback_e:
                    logger.exception(
                        f"❌ Final fallback EventBusClient creation failed: {fallback_e}",
                    )

            if event_bus:
                # Inject event bus into the hub instance
                tool_instance.event_bus = event_bus
                logger.info(
                    f"✅ Event bus injected into {self.domain} hub: {type(event_bus).__name__}",
                )
            else:
                # Provide detailed error information for debugging
                error_details = {
                    "domain": self.domain,
                    "container_type": type(self.container).__name__,
                    "has_event_bus_client": hasattr(self.container, "event_bus_client"),
                    "has_event_bus": hasattr(self.container, "event_bus"),
                    "container_attributes": [
                        attr for attr in dir(self.container) if not attr.startswith("_")
                    ],
                }
                logger.error("❌ CRITICAL: Event bus resolution failed completely")
                logger.error(f"📋 Debug details: {error_details}")
                msg = f"❌ CRITICAL: Failed to inject event bus into {self.domain} hub - all resolution methods failed"
                raise RuntimeError(
                    msg,
                )

            # Start the service registry with domain filter
            if hasattr(tool_instance, "start_service_registry"):
                logger.info(f"🚀 Starting service registry for {self.domain} domain...")
                tool_instance.start_service_registry(domain_filter=self.domain)
            else:
                msg = f"❌ CRITICAL: {self.domain} hub does not have start_service_registry method!"
                raise RuntimeError(
                    msg,
                )

            logger.info(
                f"✅ {self.domain.title()} hub initialized successfully with service registry",
            )

        except Exception as e:
            logger.exception(f"❌ Failed to initialize {self.domain} hub: {e}")
            raise


def main():
    """One-line main function - ModelNodeBase handles everything."""
    return ModelNodeBase(Path(__file__).parent / CONTRACT_FILENAME)


if __name__ == "__main__":
    # This should never be called directly - subclasses should override
    logger.error(
        "NodeHubBase should not be run directly - use a specific hub implementation",
    )
    sys.exit(1)
