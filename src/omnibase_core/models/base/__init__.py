# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Base Model Classes.

Abstract base classes for typed collections, factories, and processors
following ONEX one-model-per-file architecture.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .model_collection import ModelBaseCollection
    from .model_factory import ModelBaseFactory
    from .model_processor import ModelServiceBaseProcessor

__all__ = [
    "ModelBaseCollection",
    "ModelBaseFactory",
    "ModelServiceBaseProcessor",
]


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "ModelBaseCollection": (
        "omnibase_core.models.base.model_collection",
        "ModelBaseCollection",
    ),
    "ModelBaseFactory": ("omnibase_core.models.base.model_factory", "ModelBaseFactory"),
    "ModelServiceBaseProcessor": (
        "omnibase_core.models.base.model_processor",
        "ModelServiceBaseProcessor",
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
