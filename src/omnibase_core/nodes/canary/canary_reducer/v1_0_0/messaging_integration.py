"""
ONEX Messaging Architecture v0.2 - Infrastructure Reducer Integration

Integration layer for Infrastructure Reducer with the new messaging architecture.
Provides backward compatibility while enabling modern messaging patterns.
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional

import aiohttp
from omnibase.core.base_error import OnexError
from omnibase.messaging import (
    CommandRequest,
    GroupGateway,
    HeartbeatEvent,
    LocalToolRegistry,
    ToolMetadata,
)
from pydantic import BaseModel, Field


class ModelInfrastructureMetadata(BaseModel):
    """Model for infrastructure reducer metadata."""

    architecture: str = Field(..., description="Architecture pattern identifier")
    messaging_version: str = Field(..., description="Messaging architecture version")
    role: str = Field(..., description="Infrastructure role identifier")


class ModelHeartbeatData(BaseModel):
    """Model for heartbeat data."""

    timestamp: str = Field(..., description="Heartbeat timestamp")
    loaded_adapters: int = Field(..., description="Number of loaded adapters")
    pending_requests: int = Field(..., description="Number of pending requests")
    memory_usage_mb: float = Field(..., description="Memory usage in megabytes")


class ModelCommandParameters(BaseModel):
    """Model for command parameters."""

    registry_request: Optional[Dict[str, str]] = Field(
        default=None, description="Registry request data"
    )
    endpoint_path: Optional[str] = Field(default=None, description="API endpoint path")
    http_method: Optional[str] = Field(default=None, description="HTTP method")
    source: Optional[str] = Field(default=None, description="Request source identifier")


class ModelCommandResponse(BaseModel):
    """Model for command response."""

    status: str = Field(..., description="Command execution status")
    correlation_id: str = Field(..., description="Correlation identifier")
    result: Dict[str, str] = Field(
        default_factory=dict, description="Command result data"
    )
    error: Optional[str] = Field(default=None, description="Error message if failed")
    timestamp: str = Field(..., description="Response timestamp")


class ModelRegistryRequest(BaseModel):
    """Model for registry request data."""

    operation_type: str = Field(..., description="Type of registry operation")
    parameters: Dict[str, str] = Field(
        default_factory=dict, description="Operation parameters"
    )
    timeout_ms: Optional[int] = Field(
        default=5000, description="Request timeout in milliseconds"
    )


class ModelRegistryResponse(BaseModel):
    """Model for registry response data."""

    status: str = Field(..., description="Operation status")
    data: Dict[str, str] = Field(default_factory=dict, description="Response data")
    error_message: Optional[str] = Field(
        default=None, description="Error message if failed"
    )
    endpoint_path: str = Field(..., description="API endpoint path")
    http_method: str = Field(..., description="HTTP method used")


class MessagingIntegration:
    """
    Integration layer between Infrastructure Reducer and ONEX Messaging Architecture v0.2

    Provides:
    - Command routing through Group Gateway
    - Tool registration with Local Tool Registry
    - Backward compatibility with existing registry patterns
    - Health tracking and heartbeat management
    """

    def __init__(
        self,
        group_gateway_url: str = "http://localhost:18090",
        local_registry_url: str = "http://localhost:18091",
        tool_id: str = "infrastructure-reducer",
        environment: str = "staging",
        group: str = "infrastructure",
    ):
        self.group_gateway_url = group_gateway_url
        self.local_registry_url = local_registry_url
        self.tool_id = tool_id
        self.environment = environment
        self.group = group

        # HTTP session for API calls
        self.session: Optional[aiohttp.ClientSession] = None

        # Tool metadata for registry
        # Create metadata using proper model
        metadata_dict = ModelInfrastructureMetadata(
            architecture="4-node-pattern",
            messaging_version="0.2.0",
            role="infrastructure_coordinator",
        )

        self.tool_metadata = ToolMetadata(
            tool_id=tool_id,
            tool_name="Infrastructure Reducer",
            environment=environment,
            tool_group=group,
            capabilities=[
                "consul_operations",
                "vault_operations",
                "kafka_operations",
                "infrastructure_coordination",
                "registry_management",
            ],
            tool_type="reducer",
            version="1.0.0",
            health_status="healthy",
            metadata=metadata_dict.dict(),
            tags=["infrastructure", "reducer", "coordinator"],
        )

        # Heartbeat tracking
        self.heartbeat_interval = 30  # seconds
        self.heartbeat_task: Optional[asyncio.Task] = None
        self.start_time = datetime.utcnow()

    async def initialize(self) -> None:
        """Initialize messaging integration"""
        try:
            # Create HTTP session
            self.session = aiohttp.ClientSession()

            # Register with Local Tool Registry
            await self.register_tool()

            # Start heartbeat
            await self.start_heartbeat()

            logging.info(f"Messaging integration initialized for {self.tool_id}")

        except Exception as e:
            logging.error(f"Failed to initialize messaging integration: {e}")
            raise OnexError(
                f"Messaging integration initialization failed: {str(e)}"
            ) from e

    async def register_tool(self) -> None:
        """Register this tool with the Local Tool Registry"""
        try:
            self.tool_metadata.last_heartbeat = datetime.utcnow()
            self.tool_metadata.uptime_seconds = int(
                (datetime.utcnow() - self.start_time).total_seconds()
            )

            async with self.session.post(
                f"{self.local_registry_url}/v0/tools",
                json=self.tool_metadata.dict(),
                headers={"Content-Type": "application/json"},
            ) as response:
                if response.status in (200, 201):
                    result = await response.json()
                    logging.info(f"Successfully registered tool: {result}")
                else:
                    error_text = await response.text()
                    raise OnexError(
                        f"Tool registration failed: {response.status} - {error_text}"
                    )

        except Exception as e:
            logging.error(f"Failed to register tool: {e}")
            raise OnexError(f"Tool registration failed: {str(e)}") from e

    async def start_heartbeat(self) -> None:
        """Start heartbeat task"""
        self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())

    async def _heartbeat_loop(self) -> None:
        """Periodic heartbeat loop"""
        while True:
            try:
                await asyncio.sleep(self.heartbeat_interval)
                await self.send_heartbeat()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logging.error(f"Heartbeat error: {e}")

    async def send_heartbeat(self) -> None:
        """Send heartbeat to Local Tool Registry"""
        try:
            uptime_seconds = int((datetime.utcnow() - self.start_time).total_seconds())

            heartbeat = HeartbeatEvent(
                tool_id=self.tool_id,
                environment=self.environment,
                tool_group=self.group,
                health_status="healthy",  # Could be dynamic based on health checks
                uptime_seconds=uptime_seconds,
                heartbeat_data=ModelHeartbeatData(
                    timestamp=datetime.utcnow().isoformat(),
                    loaded_adapters=len(getattr(self, "loaded_adapters", {})),
                    pending_requests=len(
                        getattr(self, "_pending_registry_requests", {})
                    ),
                    memory_usage_mb=self._get_memory_usage(),
                ).dict(),
            )

            async with self.session.post(
                f"{self.local_registry_url}/v0/heartbeat",
                json=heartbeat.dict(),
                headers={"Content-Type": "application/json"},
            ) as response:
                if response.status == 200:
                    logging.debug("Heartbeat sent successfully")
                else:
                    error_text = await response.text()
                    logging.warning(
                        f"Heartbeat failed: {response.status} - {error_text}"
                    )

        except Exception as e:
            logging.error(f"Failed to send heartbeat: {e}")

    async def submit_command(
        self,
        command: str,
        parameters: ModelCommandParameters,
        scope: str = "group",
        timeout_ms: int = 5000,
    ) -> ModelCommandResponse:
        """
        Submit a command through the Group Gateway

        Args:
            command: Command to execute
            parameters: Command parameters
            scope: Command scope (tool|group|environment)
            timeout_ms: Response timeout

        Returns:
            Command response or error
        """
        try:
            request = CommandRequest(
                command=command,
                parameters=parameters.dict(),
                scope=scope,
                timeout_ms=timeout_ms,
            )

            # Submit command
            async with self.session.post(
                f"{self.group_gateway_url}/v0/commands/{command}",
                json=request.dict(),
                headers={"Content-Type": "application/json"},
            ) as response:
                if response.status == 202:
                    submission_result = await response.json()
                    correlation_id = submission_result["correlation_id"]

                    # Wait for completion
                    completion_response = await self._wait_for_command_completion(
                        correlation_id, timeout_ms
                    )
                    return ModelCommandResponse(
                        status=completion_response.get("status", "unknown"),
                        correlation_id=completion_response.get(
                            "correlation_id", correlation_id
                        ),
                        result=completion_response.get("result", {}),
                        error=completion_response.get("error"),
                        timestamp=datetime.utcnow().isoformat(),
                    )
                else:
                    error_text = await response.text()
                    raise OnexError(
                        f"Command submission failed: {response.status} - {error_text}"
                    )

        except Exception as e:
            logging.error(f"Failed to submit command {command}: {e}")
            raise OnexError(f"Command submission failed: {str(e)}") from e

    async def _wait_for_command_completion(
        self, correlation_id: str, timeout_ms: int
    ) -> Dict[str, str]:
        """Wait for command completion and return aggregated response"""
        try:
            # Poll for completion
            start_time = datetime.utcnow()
            timeout_seconds = timeout_ms / 1000.0

            while True:
                async with self.session.get(
                    f"{self.group_gateway_url}/v0/status/{correlation_id}"
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result
                    elif response.status == 404:
                        # Still processing, wait
                        elapsed = (datetime.utcnow() - start_time).total_seconds()
                        if elapsed >= timeout_seconds:
                            return {
                                "status": "timeout",
                                "correlation_id": correlation_id,
                                "error": "Command execution timed out",
                            }

                        await asyncio.sleep(0.5)  # Poll every 500ms
                    else:
                        error_text = await response.text()
                        raise OnexError(
                            f"Status check failed: {response.status} - {error_text}"
                        )

        except Exception as e:
            logging.error(f"Failed to wait for command completion: {e}")
            return {
                "status": "error",
                "correlation_id": correlation_id,
                "error": str(e),
            }

    async def delegate_registry_request_via_messaging(
        self,
        registry_request: ModelRegistryRequest,
        endpoint_path: str,
        http_method: str,
    ) -> ModelRegistryResponse:
        """
        Delegate registry request through the messaging architecture

        This provides backward compatibility for existing registry operations
        while routing through the new messaging infrastructure.
        """
        try:
            # Convert registry request to command format
            command = self._map_registry_request_to_command(endpoint_path, http_method)

            # Submit through Group Gateway
            command_params = ModelCommandParameters(
                registry_request=registry_request.dict(),
                endpoint_path=endpoint_path,
                http_method=http_method,
                source="infrastructure_reducer",
            )

            result = await self.submit_command(
                command=command,
                parameters=command_params,
                scope="group",
                timeout_ms=10000,
            )

            return ModelRegistryResponse(
                status=result.status,
                data=result.result,
                error_message=result.error,
                endpoint_path=endpoint_path,
                http_method=http_method,
            )

        except Exception as e:
            logging.error(f"Failed to delegate registry request: {e}")
            raise OnexError(f"Registry request delegation failed: {str(e)}") from e

    def _map_registry_request_to_command(
        self, endpoint_path: str, http_method: str
    ) -> str:
        """Map registry endpoint to messaging command"""
        # Map common registry operations to commands
        mapping = {
            ("/consul/services", "GET"): "consul_list_services",
            ("/consul/health", "GET"): "consul_health_check",
            ("/vault/secrets", "GET"): "vault_list_secrets",
            ("/vault/health", "GET"): "vault_health_check",
            ("/kafka/topics", "GET"): "kafka_list_topics",
            ("/kafka/health", "GET"): "kafka_health_check",
        }

        key = (endpoint_path, http_method)
        return mapping.get(key, f"registry_operation_{http_method.lower()}")

    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        try:
            import psutil

            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except ImportError:
            return 0.0

    async def update_health_status(
        self, status: str, metadata: Optional[ModelInfrastructureMetadata] = None
    ) -> None:
        """Update tool health status"""
        try:
            self.tool_metadata.health_status = status
            if metadata:
                self.tool_metadata.metadata.update(metadata.dict())

            # Force heartbeat with updated status
            await self.send_heartbeat()

        except Exception as e:
            logging.error(f"Failed to update health status: {e}")

    async def shutdown(self) -> None:
        """Shutdown messaging integration"""
        try:
            # Cancel heartbeat
            if self.heartbeat_task:
                self.heartbeat_task.cancel()

            # Update status to offline
            await self.update_health_status("offline")

            # Close HTTP session
            if self.session:
                await self.session.close()

            logging.info("Messaging integration shutdown complete")

        except Exception as e:
            logging.error(f"Error during messaging integration shutdown: {e}")


class InfrastructureReducerMessagingMixin:
    """
    Mixin to add messaging capabilities to Infrastructure Reducer

    This can be mixed into the existing ToolInfrastructureReducer class
    to enable messaging integration without breaking existing functionality.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Initialize messaging integration
        self.messaging = MessagingIntegration(
            tool_id=getattr(self, "node_id", "infrastructure-reducer"),
            environment=os.getenv("ONEX_ENVIRONMENT", "staging"),
            group="infrastructure",
        )

        # Track initialization state
        self._messaging_initialized = False

    async def initialize_messaging(self) -> None:
        """Initialize messaging integration"""
        if not self._messaging_initialized:
            # Pass adapter info to messaging
            if hasattr(self, "loaded_adapters"):
                self.messaging.tool_metadata.metadata["loaded_adapters"] = list(
                    self.loaded_adapters.keys()
                )

            await self.messaging.initialize()
            self._messaging_initialized = True

            if hasattr(self, "logger") and self.logger:
                self.logger.info("✅ Messaging integration initialized")

    async def delegate_registry_request_with_messaging(
        self,
        registry_request: ModelRegistryRequest,
        endpoint_path: str,
        http_method: str,
    ) -> ModelRegistryResponse:
        """
        Enhanced registry request delegation using messaging architecture

        Falls back to original implementation if messaging is not available.
        """
        try:
            if self._messaging_initialized:
                # Try messaging approach first
                return await self.messaging.delegate_registry_request_via_messaging(
                    registry_request, endpoint_path, http_method
                )
            else:
                # Fallback to original implementation
                if hasattr(super(), "delegate_registry_request"):
                    return await super().delegate_registry_request(
                        registry_request, endpoint_path, http_method
                    )
                else:
                    raise OnexError("No registry delegation method available")

        except Exception as e:
            # Fallback on messaging errors
            if hasattr(super(), "delegate_registry_request"):
                if hasattr(self, "logger") and self.logger:
                    self.logger.warning(
                        f"Messaging delegation failed, using fallback: {e}"
                    )
                return await super().delegate_registry_request(
                    registry_request, endpoint_path, http_method
                )
            else:
                raise OnexError(f"Registry delegation failed: {str(e)}") from e

    async def shutdown_messaging(self) -> None:
        """Shutdown messaging integration"""
        if self._messaging_initialized:
            await self.messaging.shutdown()
            self._messaging_initialized = False
