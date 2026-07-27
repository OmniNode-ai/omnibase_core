# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
conftest.py for tests/unit.

Provides :func:`isolated_sys_modules`, a context manager used by tests that
need to force a fresh import of ``omnibase_core`` (or a submodule) by
evicting matching entries from ``sys.modules``.

Restoring the evicted entries on exit is mandatory. Several tests
historically did ``del sys.modules[mod]`` in a bare loop with no restore,
which permanently evicted the matched ``omnibase_core.*`` entries from the
interpreter's module cache for the rest of that pytest worker process. Any
later test in the same process that performed a local/deferred import of an
evicted module forced a fresh re-execution of that module (and everything
it transitively imports), minting NEW class objects (enums, exceptions,
Pydantic models) distinct from the ones already bound at collection time
elsewhere in the process. That produced identity-based failures
(``EnumExecutionMode.CONDITIONAL not in {...}`` even though both sides
print identically) and Pydantic forward-ref resolution breaks
(``RegistryNode is not fully defined``) in tests that have nothing to do
with the actual purge. See OMN-14944.
"""

from __future__ import annotations

import sys
from collections.abc import Callable, Iterator
from contextlib import contextmanager


@contextmanager
def isolated_sys_modules(predicate: Callable[[str], bool]) -> Iterator[None]:
    """Temporarily evict ``sys.modules`` entries whose key matches ``predicate``.

    All evicted entries are restored (the exact same module objects put
    back) when the context exits -- including when the block raises -- so
    no test can permanently leak a module-cache eviction into later tests
    running in the same process. Entries newly imported *during* the block
    are left in place on exit (that is ordinary caching behavior, not a
    leak); only entries that existed before the block and were evicted by
    it are restored.
    """
    removed = {key: mod for key, mod in sys.modules.items() if predicate(key)}
    for key in removed:
        del sys.modules[key]
    try:
        yield
    finally:
        sys.modules.update(removed)
