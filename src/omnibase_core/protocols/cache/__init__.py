# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Cache protocols for distributed caching backend abstraction.

Protocol definitions for cache backends that can be used
with MixinCaching for L2 (distributed) caching support.

Protocols:
    - ProtocolCacheBackend: Async cache backend interface for L2 distributed caches

Usage:
    from omnibase_core.protocols.cache import ProtocolCacheBackend

    class MyCustomBackend:
        async def get(self, key: str) -> Any | None:
            ...

        async def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
            ...

        async def delete(self, key: str) -> None:
            ...

        async def clear(self) -> None:
            ...

        async def exists(self, key: str) -> bool:
            ...

.. versionadded:: 0.5.0
"""

from __future__ import annotations

import importlib.util
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.protocols.cache.protocol_cache_backend import (
        ProtocolCacheBackend,
    )

__all__ = ["ProtocolCacheBackend"]


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "ProtocolCacheBackend": (
        "omnibase_core.protocols.cache.protocol_cache_backend",
        "ProtocolCacheBackend",
    ),
}


def __getattr__(name: str) -> object:
    target = _LAZY_IMPORTS.get(name)
    if target is None:
        # A submodule that the old eager __init__ loaded as a side effect
        # stays reachable as ``package.submodule``: import it on first access.
        if (
            name.isidentifier()
            and not name.startswith("__")
            and importlib.util.find_spec(f"{__name__}.{name}") is not None
        ):
            return importlib.import_module(f"{__name__}.{name}")
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = importlib.import_module(target[0])
    value = module if target[1] is None else getattr(module, target[1])
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted({*globals(), *_LAZY_IMPORTS})
