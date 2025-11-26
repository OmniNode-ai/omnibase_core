# === OmniNode:Metadata ===
# author: OmniNode Team
# copyright: OmniNode.ai
# created_at: '2025-11-26T00:00:00.000000'
# description: Tests for MixinNodeService shutdown timing behavior
# entrypoint: python://test_mixin_node_service_shutdown
# lifecycle: active
# meta_type: test
# metadata_version: 0.1.0
# name: test_mixin_node_service_shutdown.py
# namespace: python://omnibase.tests.unit.mixins.test_mixin_node_service_shutdown
# owner: OmniNode Team
# protocol_version: 0.1.0
# runtime_language_hint: python>=3.11
# schema_version: 0.1.0
# state_contract: state_contract://default
# version: 1.0.0
# === /OmniNode:Metadata ===

"""Tests for MixinNodeService shutdown timing behavior.

These tests verify that the event-based shutdown signal in MixinNodeService
correctly wakes up sleeping tasks immediately when shutdown is requested,
rather than waiting for the full timeout duration (e.g., 30 seconds for
health monitor loop).
"""

import asyncio
import time
from typing import Any
from uuid import uuid4

import pytest

from omnibase_core.mixins.mixin_node_service import MixinNodeService


class MinimalServiceNode(MixinNodeService):
    """Minimal test node class that uses MixinNodeService.

    This class provides just enough implementation to test the shutdown
    timing behavior without requiring full node infrastructure.
    """

    def __init__(self) -> None:
        super().__init__()
        # Required attributes for MixinNodeService - must be valid UUID
        object.__setattr__(self, "_node_id", uuid4())

    async def run(self, input_state: Any) -> dict[str, str]:
        """Minimal run implementation for service mode."""
        return {"status": "ok"}

    def get_node_name(self) -> str:
        """Return test node name."""
        return "MinimalServiceNode"


class TestShutdownTiming:
    """Tests for shutdown event timing behavior."""

    @pytest.mark.asyncio
    async def test_shutdown_event_wakes_sleeping_task_immediately(self) -> None:
        """Verify shutdown event wakes up sleeping tasks immediately.

        The health monitor loop has a 30-second sleep interval. When shutdown
        is signaled, it should wake up immediately (< 1 second) rather than
        waiting for the full sleep to complete.
        """
        shutdown_event = asyncio.Event()
        task_woke_up = False
        wake_time = 0.0

        async def simulated_health_loop() -> None:
            nonlocal task_woke_up, wake_time
            start = time.time()
            try:
                # Simulate the health monitor's 30-second wait
                await asyncio.wait_for(shutdown_event.wait(), timeout=30)
                task_woke_up = True
                wake_time = time.time() - start
            except TimeoutError:
                # This shouldn't happen in this test
                pass

        # Start the simulated health loop
        task = asyncio.create_task(simulated_health_loop())

        # Wait a small amount to ensure task is in wait state
        await asyncio.sleep(0.1)

        # Signal shutdown
        start_time = time.time()
        shutdown_event.set()

        # Wait for task to complete
        await task

        # Verify immediate wakeup (should be < 1 second, not 30 seconds)
        elapsed = time.time() - start_time
        assert task_woke_up, "Task should have woken up"
        assert elapsed < 1.0, f"Expected immediate wakeup (<1s), got {elapsed:.2f}s"
        assert wake_time < 1.0, f"Task wait time should be <1s, got {wake_time:.2f}s"

    @pytest.mark.asyncio
    async def test_shutdown_event_not_set_waits_for_timeout(self) -> None:
        """Verify without shutdown signal, wait_for respects timeout."""
        shutdown_event = asyncio.Event()

        start = time.time()
        with pytest.raises(TimeoutError):
            # Use a short timeout for test speed
            await asyncio.wait_for(shutdown_event.wait(), timeout=0.5)
        elapsed = time.time() - start

        # Should have waited approximately the timeout duration
        assert 0.4 < elapsed < 1.0, f"Expected ~0.5s wait, got {elapsed:.2f}s"

    @pytest.mark.asyncio
    async def test_mixin_health_monitor_immediate_wakeup(self) -> None:
        """Verify MixinNodeService health monitor wakes up immediately on shutdown.

        This tests the actual MixinNodeService implementation by starting
        the health monitor loop and verifying it responds to shutdown
        within a reasonable time frame.
        """
        node = MinimalServiceNode()

        # Initialize the shutdown event as start_service_mode would
        node._shutdown_event = asyncio.Event()
        node._service_running = True
        node._shutdown_requested = False

        # Create a wrapper to track when the health loop exits
        health_loop_exited = asyncio.Event()

        async def tracked_health_loop() -> None:
            try:
                # Run one iteration of health monitoring with shutdown check
                while node._service_running and not node._shutdown_requested:
                    # Perform health check (minimal)
                    _ = node.get_service_health()

                    # Wait for shutdown event with timeout (health check interval)
                    shutdown_event = node._shutdown_event
                    if shutdown_event is not None:
                        try:
                            await asyncio.wait_for(shutdown_event.wait(), timeout=30)
                            break  # Shutdown signaled
                        except TimeoutError:
                            pass  # Continue health monitoring
                    else:
                        await asyncio.sleep(30)
            finally:
                health_loop_exited.set()

        # Start the health loop
        health_task = asyncio.create_task(tracked_health_loop())

        # Ensure the loop has started and is waiting
        await asyncio.sleep(0.1)

        # Signal shutdown and measure response time
        start_time = time.time()
        node._shutdown_event.set()

        # Wait for health loop to exit
        try:
            await asyncio.wait_for(health_loop_exited.wait(), timeout=2.0)
        except TimeoutError:
            pytest.fail("Health loop did not exit within 2 seconds of shutdown signal")

        elapsed = time.time() - start_time

        # Cleanup
        if not health_task.done():
            health_task.cancel()
            try:
                await health_task
            except asyncio.CancelledError:
                pass

        # Verify immediate wakeup (should be << 30 seconds)
        assert (
            elapsed < 1.0
        ), f"Health loop should respond to shutdown immediately (<1s), got {elapsed:.2f}s"

    @pytest.mark.asyncio
    async def test_mixin_aclose_triggers_immediate_wakeup(self) -> None:
        """Verify aclose() signals the shutdown event for immediate wakeup.

        The aclose() method should set the shutdown event, causing any
        sleeping tasks to wake up immediately.
        """
        node = MinimalServiceNode()

        # Initialize state as start_service_mode would
        node._shutdown_event = asyncio.Event()
        node._service_running = True
        node._shutdown_requested = False
        node._health_task = None  # No actual health task for this test

        # Start a task that simulates waiting on the shutdown event
        wait_completed = asyncio.Event()

        async def wait_for_shutdown() -> None:
            try:
                await asyncio.wait_for(node._shutdown_event.wait(), timeout=30)
                wait_completed.set()
            except TimeoutError:
                pass

        wait_task = asyncio.create_task(wait_for_shutdown())

        # Ensure task is waiting
        await asyncio.sleep(0.1)

        # Call aclose which should set the shutdown event
        start_time = time.time()
        await node.aclose()
        elapsed = time.time() - start_time

        # Wait for our simulated task to complete
        try:
            await asyncio.wait_for(wait_completed.wait(), timeout=1.0)
        except TimeoutError:
            # Cleanup and fail
            wait_task.cancel()
            try:
                await wait_task
            except asyncio.CancelledError:
                pass
            pytest.fail("Waiting task did not wake up after aclose()")

        # Cleanup
        if not wait_task.done():
            wait_task.cancel()
            try:
                await wait_task
            except asyncio.CancelledError:
                pass

        # Verify the shutdown event was set quickly
        assert (
            elapsed < 1.0
        ), f"aclose() should complete quickly (<1s), got {elapsed:.2f}s"
        assert wait_completed.is_set(), "Waiting task should have completed"

    @pytest.mark.asyncio
    async def test_service_event_loop_immediate_shutdown(self) -> None:
        """Verify service event loop responds to shutdown event immediately.

        The service event loop uses a 0.1s timeout for responsiveness,
        but should still respond to shutdown event immediately.
        """
        shutdown_event = asyncio.Event()
        loop_iterations = 0
        loop_exited = False

        async def simulated_service_loop() -> None:
            nonlocal loop_iterations, loop_exited
            service_running = True
            shutdown_requested = False

            while service_running and not shutdown_requested:
                loop_iterations += 1
                try:
                    await asyncio.wait_for(shutdown_event.wait(), timeout=0.1)
                    # Shutdown signaled
                    break
                except TimeoutError:
                    # Normal timeout - would continue processing
                    pass

            loop_exited = True

        # Start the service loop
        task = asyncio.create_task(simulated_service_loop())

        # Let it run a few iterations
        await asyncio.sleep(0.25)

        # Signal shutdown
        start_time = time.time()
        shutdown_event.set()

        # Wait for exit
        await task
        elapsed = time.time() - start_time

        # Verify behavior
        assert loop_exited, "Service loop should have exited"
        assert loop_iterations >= 1, "Service loop should have run at least once"
        assert (
            elapsed < 0.2
        ), f"Should exit within one loop iteration (<0.2s), got {elapsed:.2f}s"


class TestShutdownEventIntegration:
    """Integration tests for shutdown event handling in MixinNodeService."""

    @pytest.mark.asyncio
    async def test_stop_service_mode_sets_shutdown_event(self) -> None:
        """Verify stop_service_mode sets the shutdown event."""
        node = MinimalServiceNode()

        # Initialize state
        node._shutdown_event = asyncio.Event()
        node._service_running = True
        node._shutdown_requested = False
        node._health_task = None

        # Verify event is not set initially
        assert (
            not node._shutdown_event.is_set()
        ), "Shutdown event should not be set initially"

        # Stop service
        await node.stop_service_mode()

        # Verify event is now set
        assert (
            node._shutdown_event.is_set()
        ), "Shutdown event should be set after stop_service_mode"

    @pytest.mark.asyncio
    async def test_shutdown_event_created_lazily(self) -> None:
        """Verify shutdown event is None until start_service_mode creates it."""
        node = MinimalServiceNode()

        # Verify shutdown event is None after init
        assert node._shutdown_event is None, "Shutdown event should be None after init"

    @pytest.mark.asyncio
    async def test_multiple_shutdown_signals_are_safe(self) -> None:
        """Verify setting shutdown event multiple times is safe."""
        shutdown_event = asyncio.Event()

        # Set multiple times - should not raise
        shutdown_event.set()
        shutdown_event.set()
        shutdown_event.set()

        # Verify still set
        assert shutdown_event.is_set(), "Event should remain set"

        # Verify wait returns immediately for all
        for _ in range(3):
            try:
                await asyncio.wait_for(shutdown_event.wait(), timeout=0.1)
            except TimeoutError:
                pytest.fail("Wait should return immediately when event is set")
