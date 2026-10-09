# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Mixin-related models for ONEX framework."""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.models.mixins.model_completion_data import ModelCompletionData
    from omnibase_core.models.mixins.model_log_data import ModelLogData
    from omnibase_core.models.mixins.model_node_introspection_data import (
        ModelNodeIntrospectionData,
    )
    from omnibase_core.models.mixins.model_service_registry_entry import (
        ModelServiceRegistryEntry,
    )

__all__ = [
    "ModelCompletionData",
    "ModelLogData",
    "ModelNodeIntrospectionData",
    "ModelServiceRegistryEntry",
]


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "ModelCompletionData": (
        "omnibase_core.models.mixins.model_completion_data",
        "ModelCompletionData",
    ),
    "ModelLogData": ("omnibase_core.models.mixins.model_log_data", "ModelLogData"),
    "ModelNodeIntrospectionData": (
        "omnibase_core.models.mixins.model_node_introspection_data",
        "ModelNodeIntrospectionData",
    ),
    "ModelServiceRegistryEntry": (
        "omnibase_core.models.mixins.model_service_registry_entry",
        "ModelServiceRegistryEntry",
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
