# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Unit tests for ServiceRegistry.register_factory() — lazy service loading.

Covers OMN-1716 acceptance criteria:
- register_factory() no longer raises METHOD_NOT_IMPLEMENTED
- Lazy instantiation: factory called on first resolve, not at registration time
- SINGLETON lifecycle caches instance after first creation
- TRANSIENT lifecycle creates a new instance per resolution
- Thread-safety via asyncio lock (double-checked locking for singleton)
- Existing tests continue to pass (checked in conftest / other test modules)
"""

import asyncio
from uuid import UUID

import pytest

from omnibase_core.container.container_service_registry import ServiceRegistry
from omnibase_core.enums import EnumInjectionScope, EnumServiceLifecycle
from omnibase_core.models.errors.model_onex_error import ModelOnexError

# ---------------------------------------------------------------------------
# Shared test helpers
# ---------------------------------------------------------------------------


class ITestService:
    """Minimal test service interface."""

    def execute(self) -> str:
        """Execute service logic."""


class ConcreteService(ITestService):
    """Concrete service implementation for testing."""

    _instances_created: int = 0

    def __init__(self, tag: str = "default") -> None:
        ConcreteService._instances_created += 1
        self.tag = tag
        self.instance_number = ConcreteService._instances_created

    def execute(self) -> str:
        return f"ConcreteService(tag={self.tag}, n={self.instance_number})"

    @classmethod
    def reset_counter(cls) -> None:
        cls._instances_created = 0


class MockProtocolFactory:
    """Minimal ProtocolServiceFactory-compatible implementation."""

    def __init__(self, tag: str = "factory") -> None:
        self.tag = tag
        self.create_call_count = 0

    async def create_instance(self, interface: type, context: dict) -> object:
        self.create_call_count += 1
        return ConcreteService(tag=self.tag)

    async def dispose_instance(self, instance: object) -> None:
        pass


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRegisterFactory:
    """Tests for ServiceRegistry.register_factory() — OMN-1716."""

    @pytest.fixture(autouse=True)
    def reset_counter(self) -> None:
        ConcreteService.reset_counter()

    # ------------------------------------------------------------------
    # Basic registration
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_register_factory_returns_uuid(
        self, registry: ServiceRegistry
    ) -> None:
        """register_factory() returns a valid UUID and does not raise."""
        factory = MockProtocolFactory()
        registration_id = await registry.register_factory(
            interface=ITestService,
            factory=factory,
            lifecycle=EnumServiceLifecycle.TRANSIENT,
            scope=EnumInjectionScope.GLOBAL,
        )
        assert isinstance(registration_id, UUID)

    @pytest.mark.asyncio
    async def test_register_factory_default_lifecycle_is_transient(
        self, registry: ServiceRegistry
    ) -> None:
        """Default lifecycle for register_factory is TRANSIENT."""
        factory = MockProtocolFactory()
        registration_id = await registry.register_factory(
            interface=ITestService,
            factory=factory,
        )
        registration = await registry.get_registration(registration_id)
        assert registration is not None
        assert registration.lifecycle == EnumServiceLifecycle.TRANSIENT

    @pytest.mark.asyncio
    async def test_register_factory_stores_registration(
        self, registry: ServiceRegistry
    ) -> None:
        """Registration metadata is correctly stored after register_factory."""
        factory = MockProtocolFactory()
        registration_id = await registry.register_factory(
            interface=ITestService,
            factory=factory,
            lifecycle=EnumServiceLifecycle.SINGLETON,
            scope=EnumInjectionScope.GLOBAL,
        )
        registration = await registry.get_registration(registration_id)
        assert registration is not None
        assert registration.lifecycle == EnumServiceLifecycle.SINGLETON
        assert registration.scope == EnumInjectionScope.GLOBAL
        assert "factory" in registration.service_metadata.tags

    # ------------------------------------------------------------------
    # Lazy instantiation
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_factory_not_called_at_registration_time(
        self, registry: ServiceRegistry
    ) -> None:
        """The factory is NOT invoked when register_factory() is called."""
        factory = MockProtocolFactory()
        await registry.register_factory(
            interface=ITestService,
            factory=factory,
            lifecycle=EnumServiceLifecycle.SINGLETON,
        )
        assert factory.create_call_count == 0
        assert ConcreteService._instances_created == 0

    @pytest.mark.asyncio
    async def test_factory_called_on_first_resolve(
        self, registry: ServiceRegistry
    ) -> None:
        """Factory is invoked on the first resolve_service() call."""
        factory = MockProtocolFactory()
        await registry.register_factory(
            interface=ITestService,
            factory=factory,
            lifecycle=EnumServiceLifecycle.SINGLETON,
        )

        instance = await registry.resolve_service(ITestService)

        assert factory.create_call_count == 1
        assert ConcreteService._instances_created == 1
        assert isinstance(instance, ConcreteService)

    # ------------------------------------------------------------------
    # SINGLETON lifecycle
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_singleton_factory_caches_instance(
        self, registry: ServiceRegistry
    ) -> None:
        """SINGLETON factory creates exactly one instance across multiple resolutions."""
        factory = MockProtocolFactory(tag="singleton_tag")
        await registry.register_factory(
            interface=ITestService,
            factory=factory,
            lifecycle=EnumServiceLifecycle.SINGLETON,
        )

        instance1 = await registry.resolve_service(ITestService)
        instance2 = await registry.resolve_service(ITestService)
        instance3 = await registry.resolve_service(ITestService)

        # Factory called exactly once
        assert factory.create_call_count == 1
        # All resolutions return the same object
        assert instance1 is instance2
        assert instance1 is instance3

    @pytest.mark.asyncio
    async def test_singleton_factory_instance_is_correct_type(
        self, registry: ServiceRegistry
    ) -> None:
        """SINGLETON factory returns an instance of the expected implementation."""
        factory = MockProtocolFactory(tag="typed")
        await registry.register_factory(
            interface=ITestService,
            factory=factory,
            lifecycle=EnumServiceLifecycle.SINGLETON,
        )

        instance = await registry.resolve_service(ITestService)

        assert isinstance(instance, ConcreteService)
        concrete = instance  # type: ignore[assignment]
        assert concrete.tag == "typed"  # type: ignore[union-attr]

    # ------------------------------------------------------------------
    # TRANSIENT lifecycle
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_transient_factory_creates_new_instance_each_time(
        self, registry: ServiceRegistry
    ) -> None:
        """TRANSIENT factory creates a distinct instance on every resolution."""
        factory = MockProtocolFactory(tag="transient_tag")
        await registry.register_factory(
            interface=ITestService,
            factory=factory,
            lifecycle=EnumServiceLifecycle.TRANSIENT,
        )

        instance1 = await registry.resolve_service(ITestService)
        instance2 = await registry.resolve_service(ITestService)
        instance3 = await registry.resolve_service(ITestService)

        # Factory called once per resolution
        assert factory.create_call_count == 3
        # Each resolution produces a distinct object
        assert instance1 is not instance2
        assert instance1 is not instance3
        assert instance2 is not instance3

    @pytest.mark.asyncio
    async def test_transient_factory_total_instances_created(
        self, registry: ServiceRegistry
    ) -> None:
        """TRANSIENT lifecycle creates N instances for N resolutions."""
        factory = MockProtocolFactory()
        await registry.register_factory(
            interface=ITestService,
            factory=factory,
            lifecycle=EnumServiceLifecycle.TRANSIENT,
        )

        for _ in range(5):
            await registry.resolve_service(ITestService)

        assert factory.create_call_count == 5
        assert ConcreteService._instances_created == 5

    # ------------------------------------------------------------------
    # Unsupported lifecycle guard
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_register_factory_unsupported_lifecycle_raises(
        self, registry: ServiceRegistry
    ) -> None:
        """register_factory() raises ModelOnexError for unsupported lifecycle values."""
        factory = MockProtocolFactory()
        with pytest.raises(ModelOnexError):
            # "scoped" is not yet supported for factory registration
            await registry.register_factory(
                interface=ITestService,
                factory=factory,
                lifecycle="scoped",  # type: ignore[arg-type]
            )

    # ------------------------------------------------------------------
    # Cleanup / unregister
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_unregister_removes_factory(self, registry: ServiceRegistry) -> None:
        """Unregistering a factory registration prevents future resolution."""
        factory = MockProtocolFactory()
        registration_id = await registry.register_factory(
            interface=ITestService,
            factory=factory,
            lifecycle=EnumServiceLifecycle.SINGLETON,
        )

        removed = await registry.unregister_service(registration_id)
        assert removed is True

        # Resolve should fail since registration is gone
        with pytest.raises(ModelOnexError):
            await registry.resolve_service(ITestService)

    # ------------------------------------------------------------------
    # Concurrency (SINGLETON double-checked locking)
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_singleton_factory_concurrent_resolution_creates_one_instance(
        self, registry: ServiceRegistry
    ) -> None:
        """Concurrent resolutions of a SINGLETON factory produce exactly one instance."""
        factory = MockProtocolFactory(tag="concurrent")
        await registry.register_factory(
            interface=ITestService,
            factory=factory,
            lifecycle=EnumServiceLifecycle.SINGLETON,
        )

        # Fire 20 concurrent resolve calls
        instances = await asyncio.gather(
            *[registry.resolve_service(ITestService) for _ in range(20)]
        )

        # Factory should have been called exactly once despite concurrency
        assert factory.create_call_count == 1
        assert ConcreteService._instances_created == 1

        # All resolutions return the same object
        first = instances[0]
        assert all(inst is first for inst in instances)

    @pytest.mark.asyncio
    async def test_transient_factory_concurrent_resolution_creates_many_instances(
        self, registry: ServiceRegistry
    ) -> None:
        """Concurrent resolutions of a TRANSIENT factory each get their own instance."""
        factory = MockProtocolFactory(tag="concurrent_transient")
        await registry.register_factory(
            interface=ITestService,
            factory=factory,
            lifecycle=EnumServiceLifecycle.TRANSIENT,
        )

        instances = await asyncio.gather(
            *[registry.resolve_service(ITestService) for _ in range(10)]
        )

        # Each concurrent call produces a distinct instance
        assert factory.create_call_count == 10
        assert len({id(inst) for inst in instances}) == 10
