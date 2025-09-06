"""
In-memory Service Discovery implementation.

Provides a fallback implementation of ProtocolServiceDiscovery
using in-memory storage when external service discovery is unavailable.
"""

import asyncio
import time
from typing import Any

from omnibase_core.core.common_types import ModelScalarValue
from omnibase_core.protocol.protocol_service_discovery import ProtocolServiceDiscovery

# Import ModelServiceHealth but handle the complex model gracefully
try:
    from omnibase_core.model.service.model_service_health import ModelServiceHealth

    USE_COMPLEX_MODEL = True
except Exception:
    USE_COMPLEX_MODEL = False
    ModelServiceHealth = None


class SimpleServiceHealth:
    """Simple internal service health tracking for in-memory service discovery."""

    def __init__(
        self,
        service_id: str,
        status: str,
        last_check: float | None = None,
        error_message: str | None = None,
    ):
        self.service_id = service_id
        self.status = status
        self.last_check = last_check
        self.error_message = error_message


class MinimalServiceHealth:
    """Minimal ModelServiceHealth-compatible class for service discovery tests."""

    def __init__(
        self,
        service_id: str,
        status: str,
        last_check: float | None = None,
        error_message: str | None = None,
    ):
        self.service_id = service_id
        self.status = status
        self.last_check = last_check
        self.error_message = error_message


# Type alias for return type compatibility
ServiceHealthReturn = ModelServiceHealth if USE_COMPLEX_MODEL else MinimalServiceHealth


class InMemoryServiceDiscovery(ProtocolServiceDiscovery):
    """
    In-memory service discovery fallback implementation.

    Stores all service information in memory. Not suitable for distributed
    deployments but provides a working fallback when external systems
    are unavailable.
    """

    def __init__(self):
        self._services: dict[str, dict[str, Any]] = {}
        self._kv_store: dict[str, str] = {}
        self._service_health: dict[str, SimpleServiceHealth] = {}
        self._lock = asyncio.Lock()

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
        """Register a service in memory."""
        async with self._lock:
            self._services[service_id] = {
                "service_name": service_name,
                "service_id": service_id,
                "host": host,
                "port": port,
                "health_check_url": health_check_url,
                "tags": tags or [],
                "metadata": metadata,
                "registered_at": time.time(),
            }

            # Initialize health as healthy
            self._service_health[service_id] = SimpleServiceHealth(
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
        self,
        service_name: str,
        healthy_only: bool = True,
    ) -> list[dict[str, ModelScalarValue]]:
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

                    # Build service data with required ModelScalarValue objects
                    service_data: dict[str, ModelScalarValue] = {
                        "service_name": ModelScalarValue.create_string(
                            service_info["service_name"],
                        ),
                        "service_id": ModelScalarValue.create_string(
                            service_info["service_id"],
                        ),
                        "host": ModelScalarValue.create_string(service_info["host"]),
                        "port": ModelScalarValue.create_int(service_info["port"]),
                        "registered_at": ModelScalarValue.create_float(
                            service_info["registered_at"],
                        ),
                    }

                    # Add optional fields
                    if service_info["health_check_url"]:
                        service_data["health_check_url"] = (
                            ModelScalarValue.create_string(
                                service_info["health_check_url"],
                            )
                        )

                    # Add health status
                    health_obj = self._service_health.get(service_id)
                    health_status = health_obj.status if health_obj else "unknown"
                    service_data["health_status"] = ModelScalarValue.create_string(
                        health_status,
                    )

                    # Add metadata (already ModelScalarValue format)
                    service_data.update(service_info["metadata"])

                    matching_services.append(service_data)

            return matching_services

    async def get_service_health(self, service_id: str) -> ServiceHealthReturn:
        """Get service health from memory."""
        async with self._lock:
            if service_id not in self._services:
                return MinimalServiceHealth(
                    service_id=service_id,
                    status="critical",
                    error_message="Service not registered",
                )

            internal_health = self._service_health.get(service_id)
            if not internal_health:
                return MinimalServiceHealth(
                    service_id=service_id,
                    status="unknown",
                    error_message="Health status not available",
                )

            # Convert internal health to MinimalServiceHealth
            return MinimalServiceHealth(
                service_id=service_id,
                status=internal_health.status,
                last_check=internal_health.last_check,
                error_message=internal_health.error_message,
            )

    async def set_key_value(self, key: str, value: str) -> bool:
        """Set key-value in memory."""
        async with self._lock:
            self._kv_store[key] = value
        return True

    async def get_key_value(self, key: str) -> str | None:
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

    async def list_keys(self, prefix: str = "") -> list[str]:
        """List keys from memory with optional prefix."""
        async with self._lock:
            if not prefix:
                return list(self._kv_store.keys())

            return [key for key in self._kv_store if key.startswith(prefix)]

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
        self,
        service_id: str,
        status: str,
        error_message: str | None = None,
    ) -> None:
        """Update service health status (for testing/simulation)."""
        async with self._lock:
            if service_id in self._services:
                self._service_health[service_id] = SimpleServiceHealth(
                    service_id=service_id,
                    status=status,
                    last_check=time.time(),
                    error_message=error_message,
                )

    async def get_all_services(self) -> dict[str, dict[str, Any]]:
        """Get all registered services (for debugging/monitoring)."""
        async with self._lock:
            return self._services.copy()

    async def get_stats(self) -> dict[str, Any]:
        """Get service discovery statistics."""
        async with self._lock:
            return {
                "total_services": len(self._services),
                "total_kv_pairs": len(self._kv_store),
                "healthy_services": len(
                    [s for s in self._service_health.values() if s.status == "healthy"],
                ),
                "service_names": list(
                    {s["service_name"] for s in self._services.values()},
                ),
            }
