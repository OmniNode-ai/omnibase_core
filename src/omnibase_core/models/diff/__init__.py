# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Diff storage models.

Pydantic models for diff storage operations including
query filters and storage configuration.

Key Model Components:
    ModelDiffQuery:
        Query filters for diff retrieval including contract names, time range,
        change types, and pagination.

    ModelDiffStorageConfiguration:
        Configuration for diff storage backends including backend type selection,
        retention policies, and connection parameters.

Example:
    >>> from omnibase_core.models.diff import (
    ...     ModelDiffQuery,
    ...     ModelDiffStorageConfiguration,
    ... )
    >>> from datetime import datetime, UTC, timedelta
    >>>
    >>> # Create a query for recent diffs with changes
    >>> query = ModelDiffQuery(
    ...     has_changes=True,
    ...     computed_after=datetime.now(UTC) - timedelta(days=7),
    ...     limit=50,
    ... )
    >>>
    >>> # Create storage configuration
    >>> config = ModelDiffStorageConfiguration(
    ...     retention_days=30,
    ...     max_diffs=10000,
    ... )

See Also:
    - :class:`~omnibase_core.protocols.storage.protocol_diff_store.ProtocolDiffStore`:
      Protocol using these models
    - :class:`~omnibase_core.services.diff.service_diff_in_memory_store.ServiceDiffInMemoryStore`:
      In-memory storage implementation

.. versionadded:: 0.6.0
    Added as part of Diff Storage Infrastructure (OMN-1149)
"""

from __future__ import annotations

import importlib.util
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.models.diff.model_diff_query import ModelDiffQuery
    from omnibase_core.models.diff.model_diff_storage_configuration import (
        ModelDiffStorageConfiguration,
    )

__all__ = [
    "ModelDiffQuery",
    "ModelDiffStorageConfiguration",
]


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "ModelDiffQuery": ("omnibase_core.models.diff.model_diff_query", "ModelDiffQuery"),
    "ModelDiffStorageConfiguration": (
        "omnibase_core.models.diff.model_diff_storage_configuration",
        "ModelDiffStorageConfiguration",
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
