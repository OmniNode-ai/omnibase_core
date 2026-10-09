# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Schema protocols package.

This package provides protocol definitions for schema loading and validation.
These are Core-native equivalents of the SPI schema protocols.

Design Principles:
- Protocol-first: Use typing.Protocol for interface definitions
- Minimal interfaces: Only define what Core actually needs
- Runtime checkable: Use @runtime_checkable for duck typing support
- Complete type hints: Full mypy strict mode compliance
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.protocols.schema.protocol_schema_loader import (
        ProtocolSchemaLoader,
    )
    from omnibase_core.protocols.schema.protocol_schema_model import ProtocolSchemaModel

__all__ = [
    "ProtocolSchemaLoader",
    "ProtocolSchemaModel",
]


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "ProtocolSchemaLoader": (
        "omnibase_core.protocols.schema.protocol_schema_loader",
        "ProtocolSchemaLoader",
    ),
    "ProtocolSchemaModel": (
        "omnibase_core.protocols.schema.protocol_schema_model",
        "ProtocolSchemaModel",
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
