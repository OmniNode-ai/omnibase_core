# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for ComposerMiddleware."""

from collections.abc import Awaitable, Callable

import pytest

from omnibase_core.pipeline.composer_middleware import ComposerMiddleware


@pytest.mark.unit
class TestComposerMiddlewareComposition:
    """Test onion-style middleware composition."""

    @pytest.mark.asyncio
    async def test_single_middleware_wraps_core(self) -> None:
        """Single middleware wraps the core function."""
        execution_order: list[str] = []

        async def core() -> str:
            execution_order.append("core")
            return "result"

        async def middleware(next_fn: Callable[[], Awaitable[object]]) -> object:
            execution_order.append("before")
            result = await next_fn()
            execution_order.append("after")
            return result

        composer = ComposerMiddleware()
        composer.use(middleware)
        wrapped = composer.compose(core)

        result = await wrapped()

        assert execution_order == ["before", "core", "after"]
        assert result == "result"

    @pytest.mark.asyncio
    async def test_multiple_middleware_onion_order(self) -> None:
        """Multiple middleware execute in onion order (outer first, inner last)."""
        execution_order: list[str] = []

        async def core() -> str:
            execution_order.append("core")
            return "result"

        async def outer(next_fn: Callable[[], Awaitable[object]]) -> object:
            execution_order.append("outer-before")
            result = await next_fn()
            execution_order.append("outer-after")
            return result

        async def inner(next_fn: Callable[[], Awaitable[object]]) -> object:
            execution_order.append("inner-before")
            result = await next_fn()
            execution_order.append("inner-after")
            return result

        composer = ComposerMiddleware()
        composer.use(outer)  # First added = outermost
        composer.use(inner)  # Last added = innermost
        wrapped = composer.compose(core)

        result = await wrapped()

        # Onion order: outer -> inner -> core -> inner -> outer
        assert execution_order == [
            "outer-before",
            "inner-before",
            "core",
            "inner-after",
            "outer-after",
        ]

    @pytest.mark.asyncio
    async def test_no_middleware_returns_core_directly(self) -> None:
        """No middleware means core executes directly."""
        execution_order: list[str] = []

        async def core() -> str:
            execution_order.append("core")
            return "result"

        composer = ComposerMiddleware()
        wrapped = composer.compose(core)

        result = await wrapped()

        assert execution_order == ["core"]
        assert result == "result"

    @pytest.mark.asyncio
    async def test_middleware_can_modify_result(self) -> None:
        """Middleware can transform the result."""

        async def core() -> int:
            return 10

        async def doubler(next_fn: Callable[[], Awaitable[object]]) -> object:
            result = await next_fn()
            return result * 2

        composer = ComposerMiddleware()
        composer.use(doubler)
        wrapped = composer.compose(core)

        result = await wrapped()

        assert result == 20

    @pytest.mark.asyncio
    async def test_middleware_can_short_circuit(self) -> None:
        """Middleware can short-circuit without calling next."""
        core_called: list[bool] = []

        async def core() -> str:
            core_called.append(True)
            return "should not reach"

        async def short_circuit(next_fn: Callable[[], Awaitable[object]]) -> object:
            return "short-circuited"  # Never calls next_fn

        composer = ComposerMiddleware()
        composer.use(short_circuit)
        wrapped = composer.compose(core)

        result = await wrapped()

        assert result == "short-circuited"
        assert core_called == []  # Core never called

    @pytest.mark.asyncio
    async def test_middleware_exception_propagates(self) -> None:
        """Exceptions in middleware propagate correctly."""

        async def core() -> str:
            return "result"

        async def failing_middleware(
            next_fn: Callable[[], Awaitable[object]],
        ) -> object:
            raise ValueError("Middleware failed")

        composer = ComposerMiddleware()
        composer.use(failing_middleware)
        wrapped = composer.compose(core)

        with pytest.raises(ValueError, match="Middleware failed"):
            await wrapped()

    @pytest.mark.asyncio
    async def test_middleware_can_catch_core_exception(self) -> None:
        """Middleware can catch and handle exceptions from core."""

        async def core() -> str:
            raise ValueError("Core failed")

        async def error_handler(next_fn: Callable[[], Awaitable[object]]) -> object:
            try:
                return await next_fn()
            except ValueError:
                return "handled"

        composer = ComposerMiddleware()
        composer.use(error_handler)
        wrapped = composer.compose(core)

        result = await wrapped()

        assert result == "handled"


@pytest.mark.unit
class TestComposerMiddlewareChainExecution:
    """Test middleware chain execution patterns."""

    @pytest.mark.asyncio
    async def test_three_layer_middleware(self) -> None:
        """Three layers of middleware execute correctly."""
        execution_order: list[str] = []

        async def core() -> str:
            execution_order.append("core")
            return "result"

        async def layer1(next_fn: Callable[[], Awaitable[object]]) -> object:
            execution_order.append("L1-in")
            result = await next_fn()
            execution_order.append("L1-out")
            return result

        async def layer2(next_fn: Callable[[], Awaitable[object]]) -> object:
            execution_order.append("L2-in")
            result = await next_fn()
            execution_order.append("L2-out")
            return result

        async def layer3(next_fn: Callable[[], Awaitable[object]]) -> object:
            execution_order.append("L3-in")
            result = await next_fn()
            execution_order.append("L3-out")
            return result

        composer = ComposerMiddleware()
        composer.use(layer1)
        composer.use(layer2)
        composer.use(layer3)
        wrapped = composer.compose(core)

        result = await wrapped()

        assert execution_order == [
            "L1-in",
            "L2-in",
            "L3-in",
            "core",
            "L3-out",
            "L2-out",
            "L1-out",
        ]
        assert result == "result"

    @pytest.mark.asyncio
    async def test_compose_returns_new_callable(self) -> None:
        """Compose returns a new callable, doesn't modify original."""

        async def core() -> str:
            return "original"

        composer = ComposerMiddleware()
        wrapped = composer.compose(core)

        # Original still works
        assert await core() == "original"
        # Wrapped also works
        assert await wrapped() == "original"
