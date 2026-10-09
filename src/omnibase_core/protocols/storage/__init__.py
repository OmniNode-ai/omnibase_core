# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Storage protocol definitions.

Protocols for pluggable storage backends.
Currently supports:

- ProtocolDiffStore: Interface for contract diff storage backends

Example:
    >>> from omnibase_core.protocols.storage import ProtocolDiffStore
    >>> from omnibase_core.services.diff.service_diff_in_memory_store import ServiceDiffInMemoryStore
    >>>
    >>> # ServiceDiffInMemoryStore implements ProtocolDiffStore
    >>> store: ProtocolDiffStore = ServiceDiffInMemoryStore()

See Also:
    - :class:`~omnibase_core.services.diff.service_diff_in_memory_store.ServiceDiffInMemoryStore`:
      In-memory implementation
    - :class:`~omnibase_core.models.contracts.diff.ModelContractDiff`:
      The diff model being stored

.. versionadded:: 0.6.0
    Added as part of Diff Storage Infrastructure (OMN-1149)
"""

from __future__ import annotations

import importlib.util
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.errors.error_state_corruption import StateCorruptionError
    from omnibase_core.models.state.model_state_envelope import ModelStateEnvelope
    from omnibase_core.protocols.storage.protocol_diff_store import ProtocolDiffStore
    from omnibase_core.protocols.storage.protocol_state_store import ProtocolStateStore
    from omnibase_core.protocols.storage.protocol_trace_store import ProtocolTraceStore

__all__ = [
    "ModelStateEnvelope",
    "ProtocolDiffStore",
    "ProtocolStateStore",
    "ProtocolTraceStore",
    "StateCorruptionError",
]


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "StateCorruptionError": (
        "omnibase_core.errors.error_state_corruption",
        "StateCorruptionError",
    ),
    "ModelStateEnvelope": (
        "omnibase_core.models.state.model_state_envelope",
        "ModelStateEnvelope",
    ),
    "ProtocolDiffStore": (
        "omnibase_core.protocols.storage.protocol_diff_store",
        "ProtocolDiffStore",
    ),
    "ProtocolStateStore": (
        "omnibase_core.protocols.storage.protocol_state_store",
        "ProtocolStateStore",
    ),
    "ProtocolTraceStore": (
        "omnibase_core.protocols.storage.protocol_trace_store",
        "ProtocolTraceStore",
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
