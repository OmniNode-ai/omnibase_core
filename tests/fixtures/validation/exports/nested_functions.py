"""Module with nested functions - nested ones should NOT be detected as module-level."""

__all__ = ["outer_function", "outer_async_function"]


def outer_function() -> int:
    """This is a module-level function."""

    def inner_function() -> int:
        """This is nested - should NOT be detected as module-level."""
        return 42

    return inner_function()


async def outer_async_function() -> int:
    """This is a module-level async function."""

    async def inner_async() -> int:
        """Nested async function."""
        return 1

    return await inner_async()
