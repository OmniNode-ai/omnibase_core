#!/usr/bin/env python3
"""
Infrastructure Reducer - State Aggregation and Service Host.

Aggregates results from infrastructure adapters and hosts the HTTP service
for the infrastructure tool group following modern 4-node architecture.
"""

import asyncio
import time
from importlib import import_module
from pathlib import Path
from uuid import UUID, uuid4

import yaml

from omnibase_core.constants.contract_constants import CONTRACT_FILENAME
from omnibase_core.core.errors.core_errors import CoreErrorCode, OnexError
from omnibase_core.core.infrastructure_service_bases import NodeReducerService
from omnibase_core.core.onex_container import ModelONEXContainer
from omnibase_core.enums.node import EnumHealthStatus
from omnibase_core.model.core.model_health_status import ModelHealthStatus
from omnibase_core.model.core.model_onex_event import OnexEvent
from omnibase_core.model.registry.model_registry_event import (
    ModelRegistryRequestEvent,
    ModelRegistryResponseEvent,
    RegistryOperations,
    get_operation_for_endpoint,
)


class ToolInfrastructureReducer(NodeReducerService):
    """
    Infrastructure Reducer implementation following modern 4-node architecture.

    Responsibilities:
    - Aggregate results from consul, vault, and kafka adapters
    - Host HTTP service with health endpoint
    - Manage state across infrastructure operations
    - Coordinate final responses for infrastructure workflows
    """

    def __init__(self, container: ModelONEXContainer):
        """Initialize infrastructure reducer with container injection."""
        super().__init__(container)

        self.domain = "infrastructure"

        # Infrastructure-specific attributes
        self.loaded_adapters = {}
        self.specialized_components = {}
        self._pending_registry_requests: dict[str, asyncio.Future] = {}
        self._event_bus_active = False

        # Initialize all infrastructure adapters placeholders
        self._consul_adapter: object | None = None
        self._vault_adapter: object | None = None
        self._kafka_adapter: object | None = None

        # Load infrastructure components
        self._load_infrastructure_adapters()
        self._load_specialized_components()

        # Use logger after super().__init__() completes
        if hasattr(self, "logger") and self.logger:
            self.logger.info("✅ Infrastructure Reducer initialized")
            self.logger.info(
                f"   📦 Loaded Adapters: {list(self.loaded_adapters.keys())}",
            )
            self.logger.info(
                f"   🔧 Specialized Components: {list(self.specialized_components.keys())}",
            )
        else:
            pass

    def get_introspection_data(self) -> dict:
        """
        Override introspection data to include information about loaded infrastructure tools.

        This method provides tool discovery information when the CLI runs 'onex tools'.
        """
        try:
            # Get basic introspection data from parent mixin
            base_data = {}
            if hasattr(self, "_gather_introspection_data"):
                try:
                    introspection_obj = self._gather_introspection_data()
                    # Convert NodeIntrospectionData to dict if needed
                    if hasattr(introspection_obj, "node_name"):
                        base_data = {
                            "node_name": introspection_obj.node_name,
                            "version": str(introspection_obj.version),
                            "actions": introspection_obj.capabilities.actions,
                            "protocols": introspection_obj.capabilities.protocols,
                            "metadata": introspection_obj.capabilities.metadata,
                            "tags": introspection_obj.tags,
                        }
                    else:
                        base_data = introspection_obj
                except Exception:
                    # Fall back to basic data
                    pass

            # Default introspection data
            if not base_data:
                base_data = {
                    "node_name": "tool_infrastructure_reducer",
                    "version": "v1_0_0",
                    "actions": ["health_check", "aggregate_health_status"],
                    "protocols": ["event_bus", "http"],
                    "metadata": {
                        "description": "Infrastructure reducer with adapter orchestration",
                    },
                    "tags": ["infrastructure", "reducer", "service"],
                }

            # Add infrastructure-specific information
            adapter_info = []
            for adapter_name, adapter_instance in self.loaded_adapters.items():
                adapter_info.append(
                    {
                        "name": adapter_name,
                        "type": "infrastructure_adapter",
                        "class": adapter_instance.__class__.__name__,
                        "status": "loaded",
                    },
                )

            component_info = []
            for component_name, component_data in self.specialized_components.items():
                component_info.append(
                    {
                        "name": component_name,
                        "type": component_data.get(
                            "component_type",
                            "specialized_component",
                        ),
                        "class": component_data["instance"].__class__.__name__,
                        "status": "loaded",
                    },
                )

            # Enhanced introspection data with infrastructure details
            enhanced_data = base_data.copy()
            enhanced_data.update(
                {
                    "infrastructure_tools": {
                        "adapters": adapter_info,
                        "components": component_info,
                        "total_tools": len(adapter_info) + len(component_info),
                    },
                    "service_info": {
                        "service_type": "infrastructure_reducer",
                        "capabilities": [
                            "tool_orchestration",
                            "health_aggregation",
                            "service_discovery",
                        ],
                    },
                },
            )

            return enhanced_data

        except Exception as e:
            # Fallback introspection data if anything fails
            return {
                "node_name": "tool_infrastructure_reducer",
                "version": "v1_0_0",
                "actions": ["health_check"],
                "protocols": ["event_bus"],
                "metadata": {
                    "description": f"Infrastructure reducer (introspection error: {e})",
                },
                "tags": ["infrastructure", "reducer", "error"],
                "infrastructure_tools": {
                    "adapters": (
                        list(self.loaded_adapters.keys())
                        if hasattr(self, "loaded_adapters")
                        else []
                    ),
                    "components": (
                        list(self.specialized_components.keys())
                        if hasattr(self, "specialized_components")
                        else []
                    ),
                    "total_tools": len(getattr(self, "loaded_adapters", {}))
                    + len(getattr(self, "specialized_components", {})),
                },
            }

    async def start_service_mode(self) -> None:
        """
        Override to create EventBusClient and set up infrastructure introspection.

        This method creates the EventBusClient deferred from __init__ and then sets up
        the infrastructure introspection handlers after proper async initialization.
        """

        if self._service_running:
            self._log_warning("Service already running, ignoring start request")
            return

        try:
            # Initialize service state and start service mode
            self._service_running = True
            self._start_time = time.time()
            self._event_bus_active = True

            # Subscribe to tool invocation events
            await self._subscribe_to_tool_invocations()

            # Set up infrastructure introspection handlers after event bus is connected
            try:
                self._setup_infrastructure_introspection()
                self._log_info(
                    "Infrastructure introspection handlers registered successfully",
                )
            except Exception as e:
                self._log_error(f"Failed to set up infrastructure introspection: {e}")

            # Start health monitoring
            self._health_task = asyncio.create_task(self._health_monitor_loop())

            # Register shutdown signal handlers
            self._register_signal_handlers()

            self._log_info(
                "Service started successfully - with EventBusClient created in async context",
            )

            # Main service event loop
            await self._service_event_loop()

        except Exception as e:
            self._log_error(f"Failed to start service: {e}")
            await self.stop_service_mode()
            raise OnexError(
                message=f"Infrastructure service startup failed: {e}",
                error_code=CoreErrorCode.INITIALIZATION_FAILED,
            ) from e

    def _setup_request_response_introspection(self) -> None:
        """
        Override the mixin method to prevent 'bool' object is not callable error.

        The original MixinRequestResponseIntrospection has a bug with is_connected
        being a bool property that it tries to call as a method. We bypass this
        by implementing our own introspection in _setup_infrastructure_introspection.
        """
        # Skip the problematic mixin setup - we handle introspection manually

    def _setup_infrastructure_introspection(self) -> None:
        """
        Set up introspection handlers for infrastructure tool discovery.

        This manually implements what MixinRequestResponseIntrospection does,
        but without the 'bool' callable error on is_connected.
        """
        from omnibase_core.constants.event_types import CoreEventTypes

        if not hasattr(self, "_event_bus") or self._event_bus is None:
            return

        try:
            # Subscribe to node introspection events (the ones we see in the logs)
            # Event type: "core.discovery.node_introspection"
            self._event_bus.subscribe(
                self._handle_infrastructure_introspection_request,
                CoreEventTypes.NODE_INTROSPECTION_EVENT,
            )

            # CRITICAL FIX: Also subscribe to realtime_request events from CLI
            # The CLI sends "core.discovery.realtime_request" events for tool discovery
            self._event_bus.subscribe(
                self._handle_infrastructure_introspection_request,
                CoreEventTypes.REQUEST_REAL_TIME_INTROSPECTION,
            )

        except Exception:
            pass

    def _handle_infrastructure_introspection_request(self, event) -> None:
        """
        Handle introspection requests for infrastructure tools.

        When 'onex tools' runs, this responds with information about loaded infrastructure adapters.
        """
        try:
            from uuid import uuid4

            from omnibase_core.model.discovery.enum_node_current_status import (
                NodeCurrentStatusEnum,
            )
            from omnibase_core.model.discovery.model_current_tool_availability import (
                ModelCurrentToolAvailability,
            )
            from omnibase_core.model.discovery.model_introspection_response_event import (
                ModelIntrospectionResponseEvent,
            )

            # Get introspection data for our infrastructure tools
            introspection_data = self.get_introspection_data()

            # Create tool availability entries for each adapter and component
            tool_availabilities = []

            # Add infrastructure adapters as tools
            for adapter_info in introspection_data.get("infrastructure_tools", {}).get(
                "adapters",
                [],
            ):
                tool_availabilities.append(
                    ModelCurrentToolAvailability(
                        tool_name=adapter_info["name"],
                        node_id=self._node_id,
                        current_status=NodeCurrentStatusEnum.READY,
                        capabilities=["adapter", "infrastructure"],
                        last_seen=int(__import__("time").time()),
                        performance_metrics=None,
                        resource_usage=None,
                    ),
                )

            # Add specialized components as tools
            for component_info in introspection_data.get(
                "infrastructure_tools",
                {},
            ).get("components", []):
                tool_availabilities.append(
                    ModelCurrentToolAvailability(
                        tool_name=component_info["name"],
                        node_id=self._node_id,
                        current_status=NodeCurrentStatusEnum.READY,
                        capabilities=["component", "infrastructure"],
                        last_seen=int(__import__("time").time()),
                        performance_metrics=None,
                        resource_usage=None,
                    ),
                )

            # Create and publish introspection response
            response_event = ModelIntrospectionResponseEvent(
                correlation_id=getattr(event, "correlation_id", uuid4()),
                responding_node_id=self._node_id,
                node_name=introspection_data.get("node_name", "infrastructure_reducer"),
                current_status=NodeCurrentStatusEnum.READY,
                tool_availabilities=tool_availabilities,
                capabilities=introspection_data.get("actions", []),
                performance_metrics=None,
                resource_usage=None,
                additional_info=None,
                filters_applied=None,
            )

            # Publish the response via event bus
            if hasattr(self, "_event_bus") and self._event_bus:
                self._event_bus.publish(
                    "core.discovery.realtime_response",
                    response_event.model_dump(),
                )
            else:
                pass

        except Exception:
            import traceback

            traceback.print_exc()

    def _load_infrastructure_adapters(self) -> None:
        """
        Load infrastructure adapters from tool.manifest.yaml metadata.

        Implements the normalized ONEX pattern: service loads adapters as modules.
        """
        try:
            # Get adapter configuration from contract
            contract_path = Path(__file__).parent / CONTRACT_FILENAME
            with open(contract_path) as f:
                contract = yaml.safe_load(f)

            loaded_adapters_config = contract.get("infrastructure_services", {}).get(
                "loaded_adapters",
                [],
            )

            for adapter_config in loaded_adapters_config:
                adapter_name = adapter_config["name"]
                onex_metadata_path = adapter_config["onex_node_metadata"]
                version_strategy = adapter_config["version_strategy"]

                try:
                    # Load adapter using metadata-driven discovery
                    adapter_instance = self._load_adapter_from_metadata(
                        adapter_name,
                        onex_metadata_path,
                        version_strategy,
                    )
                    self.loaded_adapters[adapter_name] = adapter_instance
                    if hasattr(self, "logger") and self.logger:
                        self.logger.info(f"   ✅ Loaded {adapter_name}")
                    else:
                        pass

                except Exception as e:
                    if hasattr(self, "logger") and self.logger:
                        self.logger.exception(
                            f"   ❌ Failed to load {adapter_name}: {e}",
                        )
                    else:
                        pass

        except Exception as e:
            if hasattr(self, "logger") and self.logger:
                self.logger.exception(f"Failed to load infrastructure adapters: {e}")
            else:
                pass

    def _load_adapter_from_metadata(
        self,
        adapter_name: str,
        metadata_path: str,
        version_strategy: str,
    ):
        """
        Load a single adapter using tool.manifest.yaml metadata.

        Args:
            adapter_name: Name of the adapter
            metadata_path: Path to tool.manifest.yaml metadata
            version_strategy: Version resolution strategy (current_stable, etc.)

        Returns:
            Loaded adapter instance
        """
        # Convert metadata path to actual file path
        # e.g., "omnibase.tools.infrastructure.tool_infrastructure_consul_adapter_effect.tool.manifest"
        # -> "src/omnibase/tools/infrastructure/tool_infrastructure_consul_adapter_effect/tool.manifest.yaml"
        base_path = metadata_path.replace(".tool.manifest", "")
        path_parts = base_path.split(".")
        # Build path from current location - we're at src/omnibase/tools/infrastructure/tool_infrastructure_reducer/v1_0_0/
        # Go up 2 levels to get to src/omnibase/tools/infrastructure/
        infrastructure_root = Path(
            __file__,
        ).parent.parent.parent  # Go up to infrastructure/
        # path_parts = ['omnibase', 'tools', 'infrastructure', 'tool_infrastructure_consul_adapter_effect']
        # We need the last part (tool_infrastructure_consul_adapter_effect) since we're already in infrastructure/
        adapter_name_part = path_parts[-1]  # Get full tool directory name
        metadata_file_path = (
            infrastructure_root / adapter_name_part / "tool.manifest.yaml"
        )

        # Load metadata
        with open(metadata_file_path) as f:
            metadata = yaml.safe_load(f)

        # Resolve version using strategy
        version_info = metadata["x_extensions"]["version_management"]
        if version_strategy == "current_stable":
            target_version = version_info["current_stable"]
        elif version_strategy == "current_development":
            target_version = (
                version_info.get("current_development")
                or version_info["current_stable"]
            )
        else:
            target_version = version_info["current_stable"]  # Default fallback

        # Build module path
        discovery_info = version_info["discovery"]
        version_dir = discovery_info["version_directory_pattern"].format(
            major=target_version.split(".")[0],
            minor=target_version.split(".")[1],
            patch=target_version.split(".")[2],
        )

        module_path = f"{metadata['namespace']}.{version_dir}.node"
        class_name = discovery_info["main_class_name"]

        # Import and instantiate
        module = import_module(module_path)
        adapter_class = getattr(module, class_name)
        return adapter_class(self.container)

    def _load_specialized_components(self) -> None:
        """
        Load specialized components for hierarchical delegation pattern.

        Implements component loading for registry catalog aggregator and other
        specialized components that provide delegated functionality.
        """
        try:
            # Get specialized components configuration from contract
            contract_path = Path(__file__).parent / CONTRACT_FILENAME
            with open(contract_path) as f:
                contract = yaml.safe_load(f)

            specialized_components_config = contract.get(
                "infrastructure_services",
                {},
            ).get("specialized_components", [])

            for component_config in specialized_components_config:
                component_name = component_config["name"]
                onex_metadata_path = component_config["onex_node_metadata"]
                version_strategy = component_config["version_strategy"]
                component_type = component_config.get(
                    "component_type",
                    "delegated_reducer",
                )
                readiness_check = component_config.get(
                    "delegation_readiness_check",
                    "infrastructure_ready",
                )

                try:
                    # Load component using metadata-driven discovery
                    component_instance = self._load_adapter_from_metadata(
                        component_name,
                        onex_metadata_path,
                        version_strategy,
                    )

                    # Store component with metadata
                    self.specialized_components[component_name] = {
                        "instance": component_instance,
                        "component_type": component_type,
                        "readiness_check": readiness_check,
                        "description": component_config.get("description", ""),
                    }

                    if hasattr(self, "logger") and self.logger:
                        self.logger.info(
                            f"   ✅ Loaded specialized component {component_name} ({component_type})",
                        )
                    else:
                        pass

                except Exception as e:
                    if hasattr(self, "logger") and self.logger:
                        self.logger.exception(
                            f"   ❌ Failed to load specialized component {component_name}: {e}",
                        )
                    else:
                        pass

        except Exception as e:
            if hasattr(self, "logger") and self.logger:
                self.logger.exception(f"Failed to load specialized components: {e}")
            else:
                pass

    async def aggregate_health_status(
        self,
        adapter_health_statuses: dict[str, object],
    ) -> dict[str, object]:
        """
        Legacy health aggregation method - replaced by modernized health_check().

        Maintained for backward compatibility with existing code that calls this method.

        Args:
            adapter_health_statuses: Health status from consul, vault, kafka adapters

        Returns:
            dict: Aggregated infrastructure health and ready state
        """
        # Use the modernized health check and convert to legacy format
        health_status = self.health_check()

        # Convert to legacy dict format expected by callers
        if health_status.status == EnumHealthStatus.HEALTHY:
            overall_status = "ready"
        elif health_status.status == EnumHealthStatus.DEGRADED:
            overall_status = "degraded"
        else:
            overall_status = "unavailable"

        # Extract ready services based on actual adapter health
        ready_services = []
        degraded_services = []
        failed_services = []

        for adapter_name, health_data in adapter_health_statuses.items():
            if isinstance(health_data, dict):
                status = health_data.get("status", "unknown")
                if status in ["healthy", "success"]:
                    ready_services.append(adapter_name)
                elif status in ["degraded", "warning"]:
                    degraded_services.append(adapter_name)
                else:
                    failed_services.append(adapter_name)

        return {
            "infrastructure_status": overall_status,
            "ready_services": ready_services,
            "degraded_services": degraded_services,
            "failed_services": failed_services,
            "ready_count": len(ready_services),
            "total_services": len(adapter_health_statuses),
            "external_access": {
                "consul_available": "consul_adapter" in ready_services,
                "vault_available": "vault_adapter" in ready_services,
                "kafka_available": "kafka_wrapper" in ready_services,
            },
        }

    def health_check(self) -> ModelHealthStatus:
        """Single comprehensive health check for Infrastructure Reducer."""
        try:
            # Check if core infrastructure components are loaded
            if not self.loaded_adapters and not self.specialized_components:
                return ModelHealthStatus(
                    status=EnumHealthStatus.UNHEALTHY,
                    message="No infrastructure adapters or specialized components loaded",
                )

            # Check individual adapter health
            unhealthy_adapters = []
            degraded_adapters = []
            healthy_adapters = []

            for adapter_name, adapter_instance in self.loaded_adapters.items():
                try:
                    if hasattr(adapter_instance, "health_check"):
                        # For adapters with health_check method, call it
                        health_result = adapter_instance.health_check()
                        if hasattr(health_result, "status"):
                            # New ModelHealthStatus format
                            if health_result.status == EnumHealthStatus.HEALTHY:
                                healthy_adapters.append(adapter_name)
                            elif health_result.status == EnumHealthStatus.DEGRADED:
                                degraded_adapters.append(adapter_name)
                            else:
                                unhealthy_adapters.append(adapter_name)
                        elif isinstance(health_result, dict):
                            # Legacy dict format
                            status = health_result.get("status", "unknown")
                            if status in ["healthy", "success"]:
                                healthy_adapters.append(adapter_name)
                            elif status in ["degraded", "warning"]:
                                degraded_adapters.append(adapter_name)
                            else:
                                unhealthy_adapters.append(adapter_name)
                        else:
                            # Unknown format, assume healthy if no exception
                            healthy_adapters.append(adapter_name)
                    else:
                        # No health check method, assume available if loaded
                        healthy_adapters.append(adapter_name)
                except Exception:
                    # Health check failed, mark as unhealthy
                    unhealthy_adapters.append(adapter_name)

            # Check specialized components
            unhealthy_components = []
            healthy_components = []

            for component_name, component_data in self.specialized_components.items():
                try:
                    component_instance = component_data["instance"]
                    if hasattr(component_instance, "health_check"):
                        health_result = component_instance.health_check()
                        if (
                            hasattr(health_result, "status")
                            and health_result.status != EnumHealthStatus.HEALTHY
                        ):
                            unhealthy_components.append(component_name)
                        else:
                            healthy_components.append(component_name)
                    else:
                        # No health check method, assume healthy if loaded
                        healthy_components.append(component_name)
                except Exception:
                    unhealthy_components.append(component_name)

            # Determine overall health status
            total_adapters = len(self.loaded_adapters)
            total_components = len(self.specialized_components)
            total_healthy = len(healthy_adapters) + len(healthy_components)
            total_degraded = len(degraded_adapters)
            total_unhealthy = len(unhealthy_adapters) + len(unhealthy_components)

            if total_unhealthy > 0:
                if total_healthy == 0:
                    status = EnumHealthStatus.UNHEALTHY
                    message = f"Infrastructure critical failure - {total_unhealthy} components failed, none healthy"
                else:
                    status = EnumHealthStatus.DEGRADED
                    message = f"Infrastructure partially degraded - {total_unhealthy} failed, {total_healthy} healthy, {total_degraded} degraded"
            elif total_degraded > 0:
                status = EnumHealthStatus.DEGRADED
                message = f"Infrastructure degraded - {total_degraded} components degraded, {total_healthy} healthy"
            else:
                status = EnumHealthStatus.HEALTHY
                message = f"Infrastructure healthy - {total_adapters} adapters, {total_components} components operational"

            return ModelHealthStatus(
                status=status,
                message=message,
            )

        except Exception as e:
            self.logger.exception(f"Infrastructure health check failed: {e}")
            return ModelHealthStatus(
                status=EnumHealthStatus.UNHEALTHY,
                message=f"Health check system failure: {e!s}",
            )

    async def get_infrastructure_status(self) -> dict[str, object]:
        """
        Get current infrastructure aggregation and readiness status.

        Returns:
            dict: Infrastructure status, adapter health, and readiness state
        """
        # Check adapter health status
        adapter_health = {}
        for adapter_name, adapter_instance in self.loaded_adapters.items():
            try:
                if hasattr(adapter_instance, "health_check"):
                    health_status = await adapter_instance.health_check()
                    adapter_health[adapter_name] = health_status
                else:
                    adapter_health[adapter_name] = {
                        "status": "unknown",
                        "message": "No health_check method",
                    }
            except Exception as e:
                adapter_health[adapter_name] = {"status": "error", "message": str(e)}

        # Aggregate infrastructure status
        aggregated_status = await self.aggregate_health_status(adapter_health)

        # Determine readiness state for delegation
        infrastructure_ready = aggregated_status.get("infrastructure_status") in [
            "ready",
            "degraded",
        ]

        return {
            "infrastructure_status": aggregated_status,
            "adapter_health": adapter_health,
            "readiness_state": {
                "infrastructure_ready": infrastructure_ready,
                "delegation_enabled": infrastructure_ready,
                "ready_adapters": aggregated_status.get("ready_services", []),
                "total_adapters": len(self.loaded_adapters),
            },
            "specialized_components": {
                name: {
                    "component_type": comp["component_type"],
                    "readiness_check": comp["readiness_check"],
                    "description": comp["description"],
                }
                for name, comp in self.specialized_components.items()
            },
        }

    async def list_loaded_adapters(self) -> dict[str, object]:
        """
        List all loaded infrastructure adapters and specialized components.

        Returns:
            dict: Information about loaded adapters and specialized components
        """
        return {
            "loaded_adapters": {
                name: {
                    "type": "infrastructure_adapter",
                    "class_name": adapter.__class__.__name__,
                    "module": adapter.__class__.__module__,
                }
                for name, adapter in self.loaded_adapters.items()
            },
            "specialized_components": {
                name: {
                    "type": comp["component_type"],
                    "readiness_check": comp["readiness_check"],
                    "description": comp["description"],
                    "class_name": comp["instance"].__class__.__name__,
                    "module": comp["instance"].__class__.__module__,
                }
                for name, comp in self.specialized_components.items()
            },
        }

    async def delegate_registry_request(
        self,
        registry_request: dict[str, object],
        endpoint_path: str,
        http_method: str,
    ) -> dict[str, object]:
        """
        Delegate registry requests via event-driven communication with registry catalog aggregator.

        Args:
            registry_request: The registry request data
            endpoint_path: The endpoint path for the registry request
            http_method: HTTP method (GET, POST, etc.)

        Returns:
            dict: Registry response or error if infrastructure not ready
        """
        try:
            # Check infrastructure readiness for delegation
            infrastructure_status = await self.get_infrastructure_status()
            if not infrastructure_status["readiness_state"]["delegation_enabled"]:
                return {
                    "status": "error",
                    "message": "Infrastructure not ready for registry delegation",
                    "infrastructure_status": infrastructure_status[
                        "infrastructure_status"
                    ]["infrastructure_status"],
                    "required_readiness": "infrastructure_ready",
                }

            # Check if event bus is available and active
            if not self._event_bus_active or not hasattr(self, "event_bus"):
                return await self._fallback_to_direct_calls(
                    registry_request,
                    endpoint_path,
                    http_method,
                )

            # Get operation name for the endpoint
            operation = get_operation_for_endpoint(endpoint_path, http_method)
            if not operation:
                return {
                    "status": "error",
                    "message": f"Unsupported registry endpoint: {http_method} {endpoint_path}",
                    "supported_endpoints": [
                        "GET /registry/tools",
                        "GET /registry/catalog",
                        "GET /registry/metrics",
                        "POST /registry/bootstrap",
                        "POST /registry/hello-coordinate",
                        "POST /registry/consul-sync",
                    ],
                }

            # Use event-driven communication
            return await self._send_registry_event_request(
                operation,
                endpoint_path,
                http_method,
                registry_request,
            )

        except Exception as e:
            if hasattr(self, "logger") and self.logger:
                self.logger.exception(f"Registry delegation error: {e}")
            return {
                "status": "error",
                "message": f"Registry delegation failed: {e!s}",
                "error_type": "delegation_error",
            }

    async def _send_registry_event_request(
        self,
        operation: str,
        endpoint_path: str,
        http_method: str,
        registry_request: dict[str, object],
        timeout_ms: int = 30000,
    ) -> dict[str, object]:
        """
        Send registry request via event bus and wait for response.

        Args:
            operation: Registry operation name
            endpoint_path: HTTP endpoint path
            http_method: HTTP method
            registry_request: Request parameters
            timeout_ms: Request timeout in milliseconds

        Returns:
            dict: Registry response data
        """
        try:
            # Create correlation ID for request-response matching
            correlation_id = uuid4()

            # Create registry request event
            request_event_data = ModelRegistryRequestEvent(
                correlation_id=correlation_id,
                operation=operation,
                endpoint_path=endpoint_path,
                http_method=http_method,
                params=registry_request,
                source_node_id=self.node_id,
                timeout_ms=timeout_ms,
            )

            # Create OnexEvent wrapper
            registry_request_event = OnexEvent.create_core_event(
                event_type=RegistryOperations.REGISTRY_REQUEST_EVENT,
                node_id=self.node_id,
                correlation_id=correlation_id,
                data=request_event_data.model_dump(),
            )

            # Track pending request
            self._pending_registry_requests[str(correlation_id)] = {
                "operation": operation,
                "start_time": asyncio.get_event_loop().time(),
                "timeout_ms": timeout_ms,
                "event": request_event_data,
            }

            # Set up response listener before sending request
            response_future = asyncio.Future()
            self._setup_registry_response_listener(correlation_id, response_future)

            # Send request event via event bus
            await self.event_bus.publish_async(registry_request_event)

            if hasattr(self, "logger") and self.logger:
                self.logger.info(
                    f"Sent registry request event: {operation}",
                    extra={
                        "correlation_id": str(correlation_id),
                        "operation": operation,
                        "endpoint": f"{http_method} {endpoint_path}",
                    },
                )

            # Wait for response with timeout
            try:
                return await asyncio.wait_for(
                    response_future,
                    timeout=timeout_ms / 1000.0,
                )

            except TimeoutError:
                # Clean up pending request
                self._pending_registry_requests.pop(str(correlation_id), None)

                return {
                    "status": "error",
                    "message": f"Registry request timeout after {timeout_ms}ms",
                    "error_type": "timeout_error",
                    "operation": operation,
                    "correlation_id": str(correlation_id),
                }

        except Exception as e:
            # Clean up pending request
            self._pending_registry_requests.pop(str(correlation_id), None)

            msg = f"Registry event request failed: {e!s}"
            raise OnexError(
                msg,
                error_code=CoreErrorCode.OPERATION_FAILED,
                correlation_id=correlation_id,
            ) from e

    def _setup_registry_response_listener(
        self,
        correlation_id: UUID,
        response_future: asyncio.Future,
    ) -> None:
        """
        Set up event listener for registry response with the given correlation ID.

        Args:
            correlation_id: Correlation ID to match responses
            response_future: Future to resolve when response arrives
        """

        async def response_handler(event: OnexEvent) -> None:
            try:
                # Check if this is a registry response event
                if event.event_type == RegistryOperations.REGISTRY_RESPONSE_EVENT:
                    # Check correlation ID match
                    if event.correlation_id == correlation_id:
                        # Parse response data
                        response_data = ModelRegistryResponseEvent(**event.data)

                        # Clean up pending request
                        self._pending_registry_requests.pop(str(correlation_id), None)

                        # Resolve future with response
                        if not response_future.done():
                            if response_data.status == "success":
                                response_future.set_result(response_data.result or {})
                            else:
                                response_future.set_result(
                                    {
                                        "status": "error",
                                        "message": response_data.error_message,
                                        "error_code": response_data.error_code,
                                        "correlation_id": str(correlation_id),
                                    },
                                )

                        # Unsubscribe after handling
                        await self.event_bus.unsubscribe_async(response_handler)

            except Exception as e:
                if hasattr(self, "logger") and self.logger:
                    self.logger.exception(f"Error handling registry response: {e}")

                if not response_future.done():
                    response_future.set_exception(e)

        # Subscribe to registry response events
        asyncio.create_task(self.event_bus.subscribe_async(response_handler))

    async def _fallback_to_direct_calls(
        self,
        registry_request: dict[str, object],
        endpoint_path: str,
        http_method: str,
    ) -> dict[str, object]:
        """
        Fallback to direct method calls when event bus is not available.

        Args:
            registry_request: The registry request data
            endpoint_path: The endpoint path for the registry request
            http_method: HTTP method (GET, POST, etc.)

        Returns:
            dict: Registry response from direct method calls
        """
        try:
            # Get registry catalog aggregator component
            registry_component = self.specialized_components.get(
                "registry_catalog_aggregator",
            )
            if not registry_component:
                return {
                    "status": "error",
                    "message": "Registry catalog aggregator component not loaded",
                    "available_components": list(self.specialized_components.keys()),
                }

            registry_instance = registry_component["instance"]

            # Delegate based on endpoint path and method (original logic)
            if endpoint_path == "/registry/tools" and http_method == "GET":
                if hasattr(registry_instance, "list_registry_tools"):
                    return await registry_instance.list_registry_tools()
                return {
                    "status": "error",
                    "message": "list_registry_tools method not available",
                }

            if endpoint_path == "/registry/catalog" and http_method == "GET":
                if hasattr(registry_instance, "get_aggregated_catalog"):
                    return await registry_instance.get_aggregated_catalog()
                return {
                    "status": "error",
                    "message": "get_aggregated_catalog method not available",
                }

            if endpoint_path == "/registry/metrics" and http_method == "GET":
                if hasattr(registry_instance, "get_aggregation_metrics"):
                    return await registry_instance.get_aggregation_metrics()
                return {
                    "status": "error",
                    "message": "get_aggregation_metrics method not available",
                }

            if endpoint_path == "/registry/bootstrap" and http_method == "POST":
                if hasattr(registry_instance, "trigger_bootstrap_workflow"):
                    return await registry_instance.trigger_bootstrap_workflow(
                        registry_request,
                    )
                return {
                    "status": "error",
                    "message": "trigger_bootstrap_workflow method not available",
                }

            if endpoint_path == "/registry/hello-coordinate" and http_method == "POST":
                if hasattr(registry_instance, "trigger_hello_coordination"):
                    return await registry_instance.trigger_hello_coordination(
                        registry_request,
                    )
                return {
                    "status": "error",
                    "message": "trigger_hello_coordination method not available",
                }

            if endpoint_path == "/registry/consul-sync" and http_method == "POST":
                if hasattr(registry_instance, "trigger_consul_sync"):
                    return await registry_instance.trigger_consul_sync(registry_request)
                return {
                    "status": "error",
                    "message": "trigger_consul_sync method not available",
                }

            return {
                "status": "error",
                "message": f"Unsupported registry endpoint: {http_method} {endpoint_path}",
                "supported_endpoints": [
                    "GET /registry/tools",
                    "GET /registry/catalog",
                    "GET /registry/metrics",
                    "POST /registry/bootstrap",
                    "POST /registry/hello-coordinate",
                    "POST /registry/consul-sync",
                ],
            }

        except Exception as e:
            if hasattr(self, "logger") and self.logger:
                self.logger.exception(f"Direct registry call fallback error: {e}")
            return {
                "status": "error",
                "message": f"Registry direct call failed: {e!s}",
                "error_type": "fallback_error",
            }


def main():
    """Main entry point for Infrastructure Reducer - returns node instance with infrastructure container"""
    from omnibase_core.tools.infrastructure.container import (
        create_infrastructure_container,
    )

    container = create_infrastructure_container()
    return ToolInfrastructureReducer(container)


if __name__ == "__main__":
    main()
