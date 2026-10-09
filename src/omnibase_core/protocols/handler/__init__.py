# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Handler protocols for message dispatch.

This package contains protocols for handler execution context, contracts,
and related handler infrastructure.

Subpackages:
    - contracts: Handler contract protocols (ProtocolHandlerContract, etc.)
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.protocols.handler.contracts import (
        ProtocolCapabilityDependency,
        ProtocolExecutionConstrainable,
        ProtocolExecutionConstraints,
        ProtocolHandlerBehaviorDescriptor,
        ProtocolHandlerContract,
    )
    from omnibase_core.protocols.handler.protocol_handler_context import (
        ProtocolHandlerContext,
    )

__all__ = [
    # Handler Context
    "ProtocolHandlerContext",
    # Handler Contracts (OMN-1164)
    "ProtocolCapabilityDependency",
    "ProtocolExecutionConstrainable",
    "ProtocolExecutionConstraints",
    "ProtocolHandlerBehaviorDescriptor",
    "ProtocolHandlerContract",
]


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "ProtocolCapabilityDependency": (
        "omnibase_core.protocols.handler.contracts",
        "ProtocolCapabilityDependency",
    ),
    "ProtocolExecutionConstrainable": (
        "omnibase_core.protocols.handler.contracts",
        "ProtocolExecutionConstrainable",
    ),
    "ProtocolExecutionConstraints": (
        "omnibase_core.protocols.handler.contracts",
        "ProtocolExecutionConstraints",
    ),
    "ProtocolHandlerBehaviorDescriptor": (
        "omnibase_core.protocols.handler.contracts",
        "ProtocolHandlerBehaviorDescriptor",
    ),
    "ProtocolHandlerContract": (
        "omnibase_core.protocols.handler.contracts",
        "ProtocolHandlerContract",
    ),
    "ProtocolHandlerContext": (
        "omnibase_core.protocols.handler.protocol_handler_context",
        "ProtocolHandlerContext",
    ),
}


def __getattr__(name: str) -> object:
    target = _LAZY_IMPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = importlib.import_module(target[0])
    value = module if target[1] is None else getattr(module, target[1])
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted({*globals(), *_LAZY_IMPORTS})
