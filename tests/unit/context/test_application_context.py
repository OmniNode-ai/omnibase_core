"""Tests for ApplicationContext and context-based container management.

This module tests the contextvars-based container management system
that provides thread-safe and async-safe container isolation.
"""

from __future__ import annotations

import asyncio
import contextvars
import threading
from unittest.mock import MagicMock

import pytest

from omnibase_core.context.context_application import (
    ApplicationContext,
    get_current_container,
    reset_container,
    run_with_container,
    run_with_container_sync,
    set_current_container,
)


@pytest.mark.unit
class TestGetCurrentContainer:
    """Tests for get_current_container function."""

    def test_returns_none_when_no_container_set(self) -> None:
        """Test that get_current_container returns None when no container is set."""
        # Create a fresh context to ensure no container is set
        ctx = contextvars.copy_context()
        result = ctx.run(get_current_container)
        assert result is None

    def test_returns_container_after_set(self) -> None:
        """Test that get_current_container returns the set container."""
        mock_container = MagicMock()

        def run_test() -> None:
            token = set_current_container(mock_container)
            try:
                result = get_current_container()
                assert result is mock_container
            finally:
                reset_container(token)

        ctx = contextvars.copy_context()
        ctx.run(run_test)


@pytest.mark.unit
class TestSetCurrentContainer:
    """Tests for set_current_container function."""

    def test_returns_token(self) -> None:
        """Test that set_current_container returns a token."""
        mock_container = MagicMock()

        def run_test() -> None:
            token = set_current_container(mock_container)
            assert token is not None
            assert isinstance(token, contextvars.Token)
            reset_container(token)

        ctx = contextvars.copy_context()
        ctx.run(run_test)

    def test_set_changes_current_container(self) -> None:
        """Test that set_current_container changes the current container."""
        mock_container1 = MagicMock(name="container1")
        mock_container2 = MagicMock(name="container2")

        def run_test() -> None:
            token1 = set_current_container(mock_container1)
            assert get_current_container() is mock_container1

            token2 = set_current_container(mock_container2)
            assert get_current_container() is mock_container2

            reset_container(token2)
            reset_container(token1)

        ctx = contextvars.copy_context()
        ctx.run(run_test)


@pytest.mark.unit
class TestResetContainer:
    """Tests for reset_container function."""

    def test_resets_to_previous_value(self) -> None:
        """Test that reset_container restores the previous value."""
        mock_container1 = MagicMock(name="container1")
        mock_container2 = MagicMock(name="container2")

        def run_test() -> None:
            token1 = set_current_container(mock_container1)
            assert get_current_container() is mock_container1

            token2 = set_current_container(mock_container2)
            assert get_current_container() is mock_container2

            # Reset to container1
            reset_container(token2)
            assert get_current_container() is mock_container1

            # Reset to None
            reset_container(token1)
            assert get_current_container() is None

        ctx = contextvars.copy_context()
        ctx.run(run_test)


@pytest.mark.unit
class TestApplicationContextSync:
    """Tests for ApplicationContext sync context manager."""

    def test_context_manager_sets_container(self) -> None:
        """Test that ApplicationContext sets the container in context."""
        mock_container = MagicMock()

        def run_test() -> None:
            with ApplicationContext(mock_container):
                assert get_current_container() is mock_container

        ctx = contextvars.copy_context()
        ctx.run(run_test)

    def test_context_manager_resets_on_exit(self) -> None:
        """Test that ApplicationContext resets the container on exit."""
        mock_container = MagicMock()

        def run_test() -> None:
            original = get_current_container()

            with ApplicationContext(mock_container):
                assert get_current_container() is mock_container

            assert get_current_container() is original

        ctx = contextvars.copy_context()
        ctx.run(run_test)

    def test_context_manager_resets_on_exception(self) -> None:
        """Test that ApplicationContext resets even when exception occurs."""
        mock_container = MagicMock()

        def run_test() -> None:
            original = get_current_container()

            with pytest.raises(ValueError, match="test error"):
                with ApplicationContext(mock_container):
                    assert get_current_container() is mock_container
                    raise ValueError("test error")

            assert get_current_container() is original

        ctx = contextvars.copy_context()
        ctx.run(run_test)

    def test_nested_context_managers(self) -> None:
        """Test that nested ApplicationContext works correctly."""
        mock_container1 = MagicMock(name="container1")
        mock_container2 = MagicMock(name="container2")

        def run_test() -> None:
            assert get_current_container() is None

            with ApplicationContext(mock_container1):
                assert get_current_container() is mock_container1

                with ApplicationContext(mock_container2):
                    assert get_current_container() is mock_container2

                assert get_current_container() is mock_container1

            assert get_current_container() is None

        ctx = contextvars.copy_context()
        ctx.run(run_test)

    def test_sync_class_method(self) -> None:
        """Test that ApplicationContext.sync() returns the context manager."""
        mock_container = MagicMock()
        ctx_mgr = ApplicationContext.sync(mock_container)
        assert isinstance(ctx_mgr, ApplicationContext)
        assert ctx_mgr.container is mock_container


@pytest.mark.unit
class TestApplicationContextAsync:
    """Tests for ApplicationContext async context manager."""

    @pytest.mark.asyncio
    async def test_async_context_manager_sets_container(self) -> None:
        """Test that ApplicationContext sets the container in async context."""
        mock_container = MagicMock()

        async with ApplicationContext(mock_container):
            assert get_current_container() is mock_container

    @pytest.mark.asyncio
    async def test_async_context_manager_resets_on_exit(self) -> None:
        """Test that ApplicationContext resets the container on async exit."""
        mock_container = MagicMock()
        original = get_current_container()

        async with ApplicationContext(mock_container):
            assert get_current_container() is mock_container

        assert get_current_container() is original

    @pytest.mark.asyncio
    async def test_async_context_manager_resets_on_exception(self) -> None:
        """Test that ApplicationContext resets even when async exception occurs."""
        mock_container = MagicMock()
        original = get_current_container()

        with pytest.raises(ValueError, match="test error"):
            async with ApplicationContext(mock_container):
                assert get_current_container() is mock_container
                raise ValueError("test error")

        assert get_current_container() is original

    @pytest.mark.asyncio
    async def test_nested_async_context_managers(self) -> None:
        """Test that nested async ApplicationContext works correctly."""
        mock_container1 = MagicMock(name="container1")
        mock_container2 = MagicMock(name="container2")

        original = get_current_container()

        async with ApplicationContext(mock_container1):
            assert get_current_container() is mock_container1

            async with ApplicationContext(mock_container2):
                assert get_current_container() is mock_container2

            assert get_current_container() is mock_container1

        assert get_current_container() is original


@pytest.mark.unit
class TestRunWithContainer:
    """Tests for run_with_container async context manager."""

    @pytest.mark.asyncio
    async def test_yields_container(self) -> None:
        """Test that run_with_container yields the container."""
        mock_container = MagicMock()

        async with run_with_container(mock_container) as container:
            assert container is mock_container
            assert get_current_container() is mock_container

    @pytest.mark.asyncio
    async def test_resets_on_exit(self) -> None:
        """Test that run_with_container resets the container on exit."""
        mock_container = MagicMock()
        original = get_current_container()

        async with run_with_container(mock_container):
            assert get_current_container() is mock_container

        assert get_current_container() is original

    @pytest.mark.asyncio
    async def test_resets_on_exception(self) -> None:
        """Test that run_with_container resets even when exception occurs."""
        mock_container = MagicMock()
        original = get_current_container()

        with pytest.raises(ValueError, match="test error"):
            async with run_with_container(mock_container):
                raise ValueError("test error")

        assert get_current_container() is original


@pytest.mark.unit
class TestRunWithContainerSync:
    """Tests for run_with_container_sync context manager."""

    def test_yields_container(self) -> None:
        """Test that run_with_container_sync yields the container."""
        mock_container = MagicMock()

        def run_test() -> None:
            with run_with_container_sync(mock_container) as container:
                assert container is mock_container
                assert get_current_container() is mock_container

        ctx = contextvars.copy_context()
        ctx.run(run_test)

    def test_resets_on_exit(self) -> None:
        """Test that run_with_container_sync resets the container on exit."""
        mock_container = MagicMock()

        def run_test() -> None:
            original = get_current_container()

            with run_with_container_sync(mock_container):
                assert get_current_container() is mock_container

            assert get_current_container() is original

        ctx = contextvars.copy_context()
        ctx.run(run_test)


@pytest.mark.unit
class TestThreadIsolation:
    """Tests for thread isolation of context variables."""

    def test_separate_threads_have_separate_contexts(self) -> None:
        """Test that different threads have separate container contexts."""
        mock_container1 = MagicMock(name="container1")
        mock_container2 = MagicMock(name="container2")
        results: dict[str, object] = {}
        barrier = threading.Barrier(2)

        def thread1_func() -> None:
            token = set_current_container(mock_container1)
            barrier.wait()  # Wait for thread2 to also set its container
            results["thread1_sees"] = get_current_container()
            barrier.wait()  # Wait for thread2 to check
            reset_container(token)

        def thread2_func() -> None:
            token = set_current_container(mock_container2)
            barrier.wait()  # Wait for thread1 to also set its container
            results["thread2_sees"] = get_current_container()
            barrier.wait()  # Wait for thread1 to check
            reset_container(token)

        t1 = threading.Thread(target=thread1_func)
        t2 = threading.Thread(target=thread2_func)

        t1.start()
        t2.start()
        t1.join()
        t2.join()

        # Each thread should see its own container
        assert results["thread1_sees"] is mock_container1
        assert results["thread2_sees"] is mock_container2


@pytest.mark.unit
class TestAsyncTaskIsolation:
    """Tests for async task isolation of context variables."""

    @pytest.mark.asyncio
    async def test_child_task_inherits_context(self) -> None:
        """Test that child async tasks inherit the container context."""
        mock_container = MagicMock()
        result: dict[str, object] = {}

        async def child_task() -> None:
            result["child_sees"] = get_current_container()

        async with ApplicationContext(mock_container):
            await asyncio.create_task(child_task())

        assert result["child_sees"] is mock_container

    @pytest.mark.asyncio
    async def test_child_task_changes_dont_affect_parent(self) -> None:
        """Test that changes in child tasks don't affect parent context."""
        mock_container1 = MagicMock(name="container1")
        mock_container2 = MagicMock(name="container2")

        async def child_task() -> None:
            # Child sets its own container
            token = set_current_container(mock_container2)
            await asyncio.sleep(0)  # Yield to event loop
            reset_container(token)

        async with ApplicationContext(mock_container1):
            task = asyncio.create_task(child_task())
            await task
            # Parent should still see its original container
            assert get_current_container() is mock_container1


@pytest.mark.unit
class TestApplicationContextProperties:
    """Tests for ApplicationContext properties."""

    def test_container_property(self) -> None:
        """Test that container property returns the container."""
        mock_container = MagicMock()
        ctx = ApplicationContext(mock_container)
        assert ctx.container is mock_container
