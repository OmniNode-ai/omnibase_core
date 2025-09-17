"""
Consul-based Service Discovery implementation with fallback.

Implements ProtocolServiceDiscovery using Consul with graceful fallback
to in-memory implementation when Consul is unavailable.
"""

import logging
from typing import TYPE_CHECKING

from omnibase_core.core.common_types import ModelScalarValue
from omnibase_core.models.service.model_service_health import ModelServiceHealth
from omnibase_core.protocol.protocol_service_discovery import ProtocolServiceDiscovery

if TYPE_CHECKING:
    from omnibase_core.services.memory_service_discovery import InMemoryServiceDiscovery


class ConsulServiceDiscovery(ProtocolServiceDiscovery):
    """
    Consul-based service discovery with automatic fallback.

    Falls back to InMemoryServiceDiscovery when Consul is unavailable.
    """

    def __init__(
        self,
        consul_host: str = "localhost",
        consul_port: int = 8500,
        datacenter: str = "dc1",
        enable_fallback: bool = True,
    ):
        self.consul_host = consul_host
        self.consul_port = consul_port
        self.datacenter = datacenter
        self.enable_fallback = enable_fallback
        self.logger = logging.getLogger(self.__class__.__name__)

        self._consul_client = None
        self._fallback_service: InMemoryServiceDiscovery | None = None
        self._is_using_fallback = False

    async def _get_consul_client(self):
        """Get Consul client with lazy initialization and fallback."""
        if self._consul_client is None:
            try:
                # Try to import and initialize consul
                import consul

                self._consul_client = consul.Consul(
                    host=self.consul_host,
                    port=self.consul_port,
                    dc=self.datacenter,
                )

                # Test connection
                await self._test_consul_connection()
                self.logger.info("Successfully connected to Consul")

            except ImportError:
                self.logger.warning("Consul library not available, using fallback")
                await self._initialize_fallback()
            except Exception as e:
                self.logger.warning(f"Failed to connect to Consul: {e}")
                if self.enable_fallback:
                    await self._initialize_fallback()
                else:
                    raise

        return self._consul_client

    async def _test_consul_connection(self):
        """Test Consul connection."""
        if self._consul_client:
            # Test with a simple agent self call
            try:
                self._consul_client.agent.self()
            except Exception as e:
                raise ConnectionError(f"Consul connection test failed: {e}")

    async def _initialize_fallback(self):
        """Initialize in-memory fallback service."""
        if self._fallback_service is None:
            from omnibase_core.services.memory_service_discovery import (
                InMemoryServiceDiscovery,
            )

            self._fallback_service = InMemoryServiceDiscovery()
            self._is_using_fallback = True
            self.logger.warning("Using in-memory service discovery fallback")

    async def register_service(
        self,
        service_name: str,
        service_id: str,
        host: str,
        port: int,
        metadata: dict[str, ModelScalarValue],
        health_check_url: str | None = None,
        tags: list[str] | None = None,
    ) -> bool:
        """Register service with Consul or fallback."""
        try:
            if self._is_using_fallback and self._fallback_service:
                return await self._fallback_service.register_service(
                    service_name,
                    service_id,
                    host,
                    port,
                    metadata,
                    health_check_url,
                    tags,
                )

            consul_client = await self._get_consul_client()

            # Import consul here to handle case where it's not available
            check = None
            if health_check_url:
                try:
                    import consul

                    check = consul.Check.http(health_check_url, interval="30s")
                except ImportError:
                    # If consul is not available, skip health check
                    check = None

            # Convert ModelScalarValue metadata to string format for Consul
            consul_metadata = {}
            for key, model_value in metadata.items():
                if model_value.string_value is not None:
                    consul_metadata[key] = model_value.string_value
                elif model_value.int_value is not None:
                    consul_metadata[key] = str(model_value.int_value)
                elif model_value.float_value is not None:
                    consul_metadata[key] = str(model_value.float_value)
                elif model_value.bool_value is not None:
                    consul_metadata[key] = str(model_value.bool_value)

            return consul_client.agent.service.register(
                name=service_name,
                service_id=service_id,
                address=host,
                port=port,
                tags=tags or [],
                check=check,
                meta=consul_metadata,
            )

        except Exception as e:
            self.logger.error(f"Service registration failed: {e}")
            if self.enable_fallback and not self._is_using_fallback:
                await self._initialize_fallback()
                return await self.register_service(
                    service_name,
                    service_id,
                    host,
                    port,
                    metadata,
                    health_check_url,
                    tags,
                )
            return False

    async def deregister_service(self, service_id: str) -> bool:
        """Deregister service from Consul or fallback."""
        try:
            if self._is_using_fallback and self._fallback_service:
                return await self._fallback_service.deregister_service(service_id)

            consul_client = await self._get_consul_client()
            return consul_client.agent.service.deregister(service_id)

        except Exception as e:
            self.logger.error(f"Service deregistration failed: {e}")
            if self.enable_fallback and not self._is_using_fallback:
                await self._initialize_fallback()
                return await self.deregister_service(service_id)
            return False

    async def discover_services(
        self,
        service_name: str,
        healthy_only: bool = True,
    ) -> list[dict[str, ModelScalarValue]]:
        """Discover services from Consul or fallback."""
        try:
            if self._is_using_fallback and self._fallback_service:
                return await self._fallback_service.discover_services(
                    service_name,
                    healthy_only,
                )

            consul_client = await self._get_consul_client()
            _, services = consul_client.health.service(
                service_name,
                passing=healthy_only,
            )

            result = []
            for service in services:
                service_data: dict[str, ModelScalarValue] = {
                    "service_id": ModelScalarValue.create_string(
                        service["Service"]["ID"],
                    ),
                    "service_name": ModelScalarValue.create_string(
                        service["Service"]["Service"],
                    ),
                    "host": ModelScalarValue.create_string(
                        service["Service"]["Address"],
                    ),
                    "port": ModelScalarValue.create_int(service["Service"]["Port"]),
                    "health_status": ModelScalarValue.create_string(
                        "healthy" if healthy_only else "unknown",
                    ),
                }

                # Convert Consul metadata to ModelScalarValue format
                consul_meta = service["Service"].get("Meta", {})
                for key, value in consul_meta.items():
                    # Consul metadata comes as strings, convert back to appropriate types
                    # Try to detect original type based on string representation
                    str_value = str(value)
                    if str_value.lower() in ("true", "false"):
                        service_data[f"meta_{key}"] = ModelScalarValue.create_bool(
                            str_value.lower() == "true",
                        )
                    elif str_value.replace(".", "").replace("-", "").isdigit():
                        if "." in str_value:
                            service_data[f"meta_{key}"] = ModelScalarValue.create_float(
                                float(str_value),
                            )
                        else:
                            service_data[f"meta_{key}"] = ModelScalarValue.create_int(
                                int(str_value),
                            )
                    else:
                        service_data[f"meta_{key}"] = ModelScalarValue.create_string(
                            str_value,
                        )

                result.append(service_data)

            return result

        except Exception as e:
            self.logger.error(f"Service discovery failed: {e}")
            if self.enable_fallback and not self._is_using_fallback:
                await self._initialize_fallback()
                return await self.discover_services(service_name, healthy_only)
            return []

    async def get_service_health(self, service_id: str) -> ModelServiceHealth:
        """Get service health from Consul or fallback."""
        try:
            if self._is_using_fallback and self._fallback_service:
                return await self._fallback_service.get_service_health(service_id)

            consul_client = await self._get_consul_client()
            _, checks = consul_client.health.checks(service=service_id)

            # Determine overall health
            if not checks:
                status = "unknown"
            elif all(check["Status"] == "passing" for check in checks):
                status = "healthy"
            elif any(check["Status"] == "critical" for check in checks):
                status = "critical"
            else:
                status = "warning"

            return ModelServiceHealth(
                service_id=service_id,
                status=status,
                last_check=None,  # Consul manages this
                error_message=None if status == "healthy" else "Health check failed",
            )

        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            if self.enable_fallback and not self._is_using_fallback:
                await self._initialize_fallback()
                return await self.get_service_health(service_id)

            return ModelServiceHealth(
                service_id=service_id,
                status="critical",
                error_message=f"Health check error: {e}",
            )

    async def set_key_value(self, key: str, value: str) -> bool:
        """Set key-value in Consul or fallback."""
        try:
            if self._is_using_fallback and self._fallback_service:
                return await self._fallback_service.set_key_value(key, value)

            consul_client = await self._get_consul_client()
            return consul_client.kv.put(key, value)

        except Exception as e:
            self.logger.error(f"Key-value set failed: {e}")
            if self.enable_fallback and not self._is_using_fallback:
                await self._initialize_fallback()
                return await self.set_key_value(key, value)
            return False

    async def get_key_value(self, key: str) -> str | None:
        """Get key-value from Consul or fallback."""
        try:
            if self._is_using_fallback and self._fallback_service:
                return await self._fallback_service.get_key_value(key)

            consul_client = await self._get_consul_client()
            _, data = consul_client.kv.get(key)

            return data["Value"].decode("utf-8") if data else None

        except Exception as e:
            self.logger.error(f"Key-value get failed: {e}")
            if self.enable_fallback and not self._is_using_fallback:
                await self._initialize_fallback()
                return await self.get_key_value(key)
            return None

    async def delete_key(self, key: str) -> bool:
        """Delete key from Consul or fallback."""
        try:
            if self._is_using_fallback and self._fallback_service:
                return await self._fallback_service.delete_key(key)

            consul_client = await self._get_consul_client()
            return consul_client.kv.delete(key)

        except Exception as e:
            self.logger.error(f"Key deletion failed: {e}")
            if self.enable_fallback and not self._is_using_fallback:
                await self._initialize_fallback()
                return await self.delete_key(key)
            return False

    async def list_keys(self, prefix: str = "") -> list[str]:
        """List keys from Consul or fallback."""
        try:
            if self._is_using_fallback and self._fallback_service:
                return await self._fallback_service.list_keys(prefix)

            consul_client = await self._get_consul_client()
            _, keys = consul_client.kv.get(prefix, keys=True)

            return keys or []

        except Exception as e:
            self.logger.error(f"Key listing failed: {e}")
            if self.enable_fallback and not self._is_using_fallback:
                await self._initialize_fallback()
                return await self.list_keys(prefix)
            return []

    async def health_check(self) -> bool:
        """Check health of service discovery system."""
        try:
            if self._is_using_fallback and self._fallback_service:
                return await self._fallback_service.health_check()

            consul_client = await self._get_consul_client()
            consul_client.agent.self()
            return True

        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return False

    async def close(self) -> None:
        """Clean up resources."""
        if self._fallback_service:
            await self._fallback_service.close()

        # Consul client doesn't need explicit cleanup
        self._consul_client = None
