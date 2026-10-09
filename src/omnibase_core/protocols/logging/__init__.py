# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Logging protocols for ONEX logging infrastructure.

Protocol definitions for logging formatters and output handlers
used by the ONEX logging system.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.protocols.logging.protocol_minimal_logger import (
        ProtocolMinimalLogger,
    )
    from omnibase_core.protocols.logging.protocol_registry_node import (
        ProtocolRegistryNode,
    )
    from omnibase_core.protocols.logging.protocol_smart_log_formatter import (
        ProtocolSmartLogFormatter,
    )
    from omnibase_core.protocols.protocol_context_aware_output_handler import (
        ProtocolContextAwareOutputHandler,
    )

__all__ = [
    "ProtocolContextAwareOutputHandler",
    "ProtocolMinimalLogger",
    "ProtocolRegistryNode",
    "ProtocolSmartLogFormatter",
]


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "ProtocolMinimalLogger": (
        "omnibase_core.protocols.logging.protocol_minimal_logger",
        "ProtocolMinimalLogger",
    ),
    "ProtocolRegistryNode": (
        "omnibase_core.protocols.logging.protocol_registry_node",
        "ProtocolRegistryNode",
    ),
    "ProtocolSmartLogFormatter": (
        "omnibase_core.protocols.logging.protocol_smart_log_formatter",
        "ProtocolSmartLogFormatter",
    ),
    "ProtocolContextAwareOutputHandler": (
        "omnibase_core.protocols.protocol_context_aware_output_handler",
        "ProtocolContextAwareOutputHandler",
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
