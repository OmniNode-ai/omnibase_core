# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Capabilities protocols for ONEX nodes.

This package provides protocol definitions for capability providers
to enable capability-based auto-discovery and registration.

Modules:
    protocol_capability_provider: Protocol for capability providers.

Usage:
    from omnibase_core.protocols.capabilities import ProtocolCapabilityProvider

    class MyNode:
        def get_capabilities(self) -> dict[str, Any]:
            return {"node_type": "COMPUTE"}

        def get_contract_capabilities(self) -> ModelContractCapabilities | None:
            return ModelContractCapabilities(...)

    # Type-safe duck typing check
    node: ProtocolCapabilityProvider = MyNode()

OMN-1124: Capabilities protocols package.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.protocols.capabilities.protocol_capability_provider import (
        ProtocolCapabilityProvider,
    )

__all__ = [
    "ProtocolCapabilityProvider",
]


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "ProtocolCapabilityProvider": (
        "omnibase_core.protocols.capabilities.protocol_capability_provider",
        "ProtocolCapabilityProvider",
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
