#!/usr/bin/env python3
"""
Consul-based Service Discovery implementation with fallback.

Implements ProtocolServiceDiscovery using Consul with graceful fallback
to in-memory implementation when Consul is unavailable.
"""

import logging
from typing import Any, Dict, List, Optional

from omnibase_core.core.common_types import ModelScalarValue
from omnibase_core.model.service.model_service_health import ModelServiceHealth
from omnibase_core.protocol.protocol_service_discovery import ProtocolServiceDiscovery


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
        self._fallback_service = None
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
        health_check_url: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, ModelScalarValue]] = None,
    ) -> bool:
        """Register service with Consul or fallback."""
        try:
            if self._is_using_fallback:
                return await self._fallback_service.register_service(
                    service_name,
                    service_id,
                    host,
                    port,
                    health_check_url,
                    tags,
                    metadata,
                )

            consul_client = await self._get_consul_client()

            check = None
            if health_check_url:
                check = consul.Check.http(health_check_url, interval="30s")

            return consul_client.agent.service.register(
                name=service_name,
                service_id=service_id,
                address=host,
                port=port,
                tags=tags or [],
                check=check,
                meta=metadata or {},
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
                    health_check_url,
                    tags,
                    metadata,
                )
            return False

    async def deregister_service(self, service_id: str) -> bool:
        """Deregister service from Consul or fallback."""
        try:
            if self._is_using_fallback:
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
        self, service_name: str, healthy_only: bool = True
    ) -> List[Dict[str, Any]]:
        """Discover services from Consul or fallback."""
        try:
            if self._is_using_fallback:
                return await self._fallback_service.discover_services(
                    service_name, healthy_only
                )

            consul_client = await self._get_consul_client()
            _, services = consul_client.health.service(
                service_name, passing=healthy_only
            )

            return [
                {
                    "service_id": service["Service"]["ID"],
                    "service_name": service["Service"]["Service"],
                    "host": service["Service"]["Address"],
                    "port": service["Service"]["Port"],
                    "tags": service["Service"]["Tags"],
                    "metadata": service["Service"]["Meta"],
                    "health_status": "healthy" if healthy_only else "unknown",
                }
                for service in services
            ]

        except Exception as e:
            self.logger.error(f"Service discovery failed: {e}")
            if self.enable_fallback and not self._is_using_fallback:
                await self._initialize_fallback()
                return await self.discover_services(service_name, healthy_only)
            return []

    async def get_service_health(self, service_id: str) -> ModelServiceHealth:
        """Get service health from Consul or fallback."""
        try:
            if self._is_using_fallback:
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
            if self._is_using_fallback:
                return await self._fallback_service.set_key_value(key, value)

            consul_client = await self._get_consul_client()
            return consul_client.kv.put(key, value)

        except Exception as e:
            self.logger.error(f"Key-value set failed: {e}")
            if self.enable_fallback and not self._is_using_fallback:
                await self._initialize_fallback()
                return await self.set_key_value(key, value)
            return False

    async def get_key_value(self, key: str) -> Optional[str]:
        """Get key-value from Consul or fallback."""
        try:
            if self._is_using_fallback:
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
            if self._is_using_fallback:
                return await self._fallback_service.delete_key(key)

            consul_client = await self._get_consul_client()
            return consul_client.kv.delete(key)

        except Exception as e:
            self.logger.error(f"Key deletion failed: {e}")
            if self.enable_fallback and not self._is_using_fallback:
                await self._initialize_fallback()
                return await self.delete_key(key)
            return False

    async def list_keys(self, prefix: str = "") -> List[str]:
        """List keys from Consul or fallback."""
        try:
            if self._is_using_fallback:
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
            if self._is_using_fallback:
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
