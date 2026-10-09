# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Connection & Networking Models

Models for connection management, metrics, and properties.
"""

from __future__ import annotations

import importlib.util
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .model_connection_info import ModelConnectionInfo
    from .model_connection_metrics import ModelConnectionMetrics
    from .model_custom_connection_properties import ModelCustomConnectionProperties

__all__ = [
    "ModelConnectionInfo",
    "ModelConnectionMetrics",
    "ModelCustomConnectionProperties",
]


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "ModelConnectionInfo": (
        "omnibase_core.models.connections.model_connection_info",
        "ModelConnectionInfo",
    ),
    "ModelConnectionMetrics": (
        "omnibase_core.models.connections.model_connection_metrics",
        "ModelConnectionMetrics",
    ),
    "ModelCustomConnectionProperties": (
        "omnibase_core.models.connections.model_custom_connection_properties",
        "ModelCustomConnectionProperties",
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
