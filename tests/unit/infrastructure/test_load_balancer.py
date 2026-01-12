"""
Tests for LoadBalancer class.

Validates load balancing functionality for workflow operation distribution.
"""

import uuid

import pytest

from omnibase_core.infrastructure.infra_load_balancer import LoadBalancer

pytestmark = pytest.mark.unit


def test_load_balancer_initialization():
    """Test that LoadBalancer initializes with correct defaults."""
    lb = LoadBalancer()

    assert lb.max_concurrent_operations == 10
    assert len(lb.active_operations) == 0
    assert len(lb.operation_counts) == 0
    assert lb.semaphore._value == 10  # Semaphore should have 10 available slots


def test_load_balancer_custom_max_operations():
    """Test LoadBalancer initialization with custom max_concurrent_operations."""
    lb = LoadBalancer(max_concurrent_operations=5)

    assert lb.max_concurrent_operations == 5
    assert lb.semaphore._value == 5


def test_get_least_loaded_target_empty_list():
    """Test get_least_loaded_target with empty target list."""
    lb = LoadBalancer()

    result = lb.get_least_loaded_target([])

    assert result == ""


def test_get_least_loaded_target_single_target():
    """Test get_least_loaded_target with single target."""
    lb = LoadBalancer()

    result = lb.get_least_loaded_target(["target1"])

    assert result == "target1"


def test_get_stats_initial_state():
    """Test get_stats returns correct initial statistics."""
    lb = LoadBalancer(max_concurrent_operations=10)

    stats = lb.get_stats()

    assert stats.active_operations == 0
    assert stats.max_concurrent == 10
    assert stats.utilization == 0.0
    assert stats.total_operations == 0


@pytest.mark.asyncio
async def test_acquire_and_release():
    """Test acquire and release operations."""
    lb = LoadBalancer(max_concurrent_operations=2)
    operation_id = uuid.uuid4()

    # Acquire slot
    result = await lb.acquire(operation_id)

    assert result is True
    assert str(operation_id) in lb.active_operations
    assert lb.operation_counts[str(operation_id)] == 1

    # Release slot
    lb.release(operation_id)

    assert str(operation_id) not in lb.active_operations
    assert lb.operation_counts[str(operation_id)] == 1  # Count persists
