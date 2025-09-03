#!/usr/bin/env python3
"""
In-memory Service Discovery implementation.

Provides a fallback implementation of ProtocolServiceDiscovery
using in-memory storage when external service discovery is unavailable.
"""

import asyncio
import time
from typing import Any, Dict, List, Optional
from uuid import uuid4

from omnibase_core.model.service.model_service_health import ModelServiceHealth
from omnibase_core.protocol.protocol_service_discovery import ProtocolServiceDiscovery


class InMemoryServiceDiscovery(ProtocolServiceDiscovery):
    """
    In-memory service discovery fallback implementation.

    Stores all service information in memory. Not suitable for distributed
    deployments but provides a working fallback when external systems
    are unavailable.
    """

    def __init__(self):
        self._services: Dict[str, Dict[str, Any]] = {}
        self._kv_store: Dict[str, str] = {}
        self._service_health: Dict[str, ModelServiceHealth] = {}
        self._lock = asyncio.Lock()

    async def register_service(
        self,
        service_name: str,
        service_id: str,
        host: str,
        port: int,
        health_check_url: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Register a service in memory."""
        async with self._lock:
            self._services[service_id] = {
                "service_name": service_name,
                "service_id": service_id,
                "host": host,
                "port": port,
                "health_check_url": health_check_url,
                "tags": tags or [],
                "metadata": metadata or {},
                "registered_at": time.time(),
            }

            # Initialize health as healthy
            self._service_health[service_id] = ModelServiceHealth(
                service_id=service_id,
                status="healthy",
                last_check=time.time(),
                error_message=None,
            )

        return True

    async def deregister_service(self, service_id: str) -> bool:
        """Deregister a service from memory."""
        async with self._lock:
            if service_id in self._services:
                del self._services[service_id]

            if service_id in self._service_health:
                del self._service_health[service_id]

        return True

    async def discover_services(
        self, service_name: str, healthy_only: bool = True
    ) -> List[Dict[str, Any]]:
        """Discover services from memory."""
        async with self._lock:
            matching_services = []

            for service_id, service_info in self._services.items():
                if service_info["service_name"] == service_name:
                    # Check health status if requested
                    if healthy_only:
                        health = self._service_health.get(service_id)
                        if not health or health.status != "healthy":
                            continue

                    service_data = service_info.copy()
                    service_data["health_status"] = self._service_health.get(
                        service_id, {}
                    ).get("status", "unknown")
                    matching_services.append(service_data)

            return matching_services

    async def get_service_health(self, service_id: str) -> ModelServiceHealth:
        """Get service health from memory."""
        async with self._lock:
            if service_id not in self._services:
                return ModelServiceHealth(
                    service_id=service_id,
                    status="critical",
                    error_message="Service not registered",
                )

            return self._service_health.get(
                service_id,
                ModelServiceHealth(
                    service_id=service_id,
                    status="unknown",
                    error_message="Health status not available",
                ),
            )

    async def set_key_value(self, key: str, value: str) -> bool:
        """Set key-value in memory."""
        async with self._lock:
            self._kv_store[key] = value
        return True

    async def get_key_value(self, key: str) -> Optional[str]:
        """Get key-value from memory."""
        async with self._lock:
            return self._kv_store.get(key)

    async def delete_key(self, key: str) -> bool:
        """Delete key from memory."""
        async with self._lock:
            if key in self._kv_store:
                del self._kv_store[key]
                return True
            return False

    async def list_keys(self, prefix: str = "") -> List[str]:
        """List keys from memory with optional prefix."""
        async with self._lock:
            if not prefix:
                return list(self._kv_store.keys())

            return [key for key in self._kv_store.keys() if key.startswith(prefix)]

    async def health_check(self) -> bool:
        """Check health of in-memory service discovery (always healthy)."""
        return True

    async def close(self) -> None:
        """Clean up resources (nothing to clean for in-memory)."""
        async with self._lock:
            self._services.clear()
            self._kv_store.clear()
            self._service_health.clear()

    # Additional methods for testing and management

    async def update_service_health(
        self, service_id: str, status: str, error_message: Optional[str] = None
    ) -> None:
        """Update service health status (for testing/simulation)."""
        async with self._lock:
            if service_id in self._services:
                self._service_health[service_id] = ModelServiceHealth(
                    service_id=service_id,
                    status=status,
                    last_check=time.time(),
                    error_message=error_message,
                )

    async def get_all_services(self) -> Dict[str, Dict[str, Any]]:
        """Get all registered services (for debugging/monitoring)."""
        async with self._lock:
            return self._services.copy()

    async def get_stats(self) -> Dict[str, Any]:
        """Get service discovery statistics."""
        async with self._lock:
            return {
                "total_services": len(self._services),
                "total_kv_pairs": len(self._kv_store),
                "healthy_services": len(
                    [s for s in self._service_health.values() if s.status == "healthy"]
                ),
                "service_names": list(
                    set(s["service_name"] for s in self._services.values())
                ),
            }
