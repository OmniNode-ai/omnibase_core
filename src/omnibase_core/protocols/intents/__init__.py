# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Intent-related protocols for the ONEX framework.

Protocol definitions for intent-related contracts,
including registration records used with PostgreSQL upsert intents.

Protocols:
    ProtocolRegistrationRecord: Contract for registration records that can
        be persisted via ModelPostgresUpsertRegistrationIntent.

Usage:
    >>> from omnibase_core.protocols.intents import ProtocolRegistrationRecord
    >>> from pydantic import BaseModel
    >>>
    >>> class NodeRegistrationRecord(BaseModel):
    ...     '''Custom registration record implementing the protocol.'''
    ...     node_id: str
    ...     node_type: str
    ...     status: str
    ...
    ...     def to_persistence_dict(self) -> dict[str, object]:
    ...         return self.model_dump(mode="json")
    >>>
    >>> # Type checker validates protocol compliance
    >>> record: ProtocolRegistrationRecord = NodeRegistrationRecord(
    ...     node_id="compute-123",
    ...     node_type="compute",
    ...     status="active",
    ... )
"""

from __future__ import annotations

import importlib.util
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.protocols.intents.protocol_registration_record import (
        ProtocolRegistrationRecord,
    )

__all__ = [
    "ProtocolRegistrationRecord",
]


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "ProtocolRegistrationRecord": (
        "omnibase_core.protocols.intents.protocol_registration_record",
        "ProtocolRegistrationRecord",
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
