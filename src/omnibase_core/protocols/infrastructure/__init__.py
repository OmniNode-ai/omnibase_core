# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Infrastructure protocols for database and service discovery.

Protocols for infrastructure-level concerns:
- Database connections with async lifecycle and transaction support
- Service discovery for distributed deployments

Design Principles:
- Use typing.Protocol with @runtime_checkable for duck typing support
- Keep interfaces minimal - only define what ONEX Core actually needs
- Provide complete type hints for mypy strict mode compliance
- Support async operations for production deployments

Usage:
    from omnibase_core.protocols.infrastructure import (
        ProtocolDatabaseConnection,
        ProtocolServiceDiscovery,
    )
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.protocols.infrastructure.protocol_database_connection import (
        ProtocolDatabaseConnection,
    )
    from omnibase_core.protocols.infrastructure.protocol_service_discovery import (
        ProtocolServiceDiscovery,
    )

__all__ = [
    "ProtocolDatabaseConnection",
    "ProtocolServiceDiscovery",
]


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "ProtocolDatabaseConnection": (
        "omnibase_core.protocols.infrastructure.protocol_database_connection",
        "ProtocolDatabaseConnection",
    ),
    "ProtocolServiceDiscovery": (
        "omnibase_core.protocols.infrastructure.protocol_service_discovery",
        "ProtocolServiceDiscovery",
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
