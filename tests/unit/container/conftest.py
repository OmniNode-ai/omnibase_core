"""
Shared fixtures for container test suite.

This module provides reusable pytest fixtures for testing ServiceRegistry
and related container components. Consolidates duplicate registry fixtures
that were previously defined in multiple test files.

Fixture Categories:
    - Registry fixtures: registry (ServiceRegistry instance)
    - Barrier fixtures: barrier_10, barrier_20 (threading barriers)

Usage Pattern:
    Fixtures are auto-discovered by pytest. Use them as function parameters::

        async def test_example(registry):
            await registry.register_instance(...)

Note:
    This conftest.py consolidates registry fixtures that were duplicated in:
    - test_service_registry.py
    - test_service_registry_memory.py
    - test_service_registry_performance.py
    - test_service_registry_stress.py

Related:
    - tests/unit/container/test_service_registry.py: ServiceRegistry core tests
    - tests/unit/container/test_service_registry_stress.py: Concurrency tests
    - tests/unit/container/test_service_registry_performance.py: Performance tests
    - tests/unit/container/test_service_registry_memory.py: Memory leak tests
"""

import threading

import pytest

from omnibase_core.container.service_registry import ServiceRegistry
from omnibase_core.models.container.model_registry_config import (
    create_default_registry_config,
)


@pytest.fixture
def registry() -> ServiceRegistry:
    """
    Create a test ServiceRegistry instance with default configuration.

    Returns:
        ServiceRegistry: A fresh registry instance for testing.

    Note:
        This fixture creates a new registry for each test, ensuring
        test isolation. The registry uses default configuration from
        create_default_registry_config().
    """
    config = create_default_registry_config()
    return ServiceRegistry(config)


@pytest.fixture
def barrier_10() -> threading.Barrier:
    """
    Create a threading barrier for synchronizing 10 threads.

    Returns:
        threading.Barrier: A barrier configured for 10 parties.

    Usage:
        Used in concurrent stress tests to ensure all threads
        start their operations simultaneously.
    """
    return threading.Barrier(10)


@pytest.fixture
def barrier_20() -> threading.Barrier:
    """
    Create a threading barrier for synchronizing 20 threads.

    Returns:
        threading.Barrier: A barrier configured for 20 parties.

    Usage:
        Used in high-contention stress tests to synchronize
        20 concurrent operations.
    """
    return threading.Barrier(20)
