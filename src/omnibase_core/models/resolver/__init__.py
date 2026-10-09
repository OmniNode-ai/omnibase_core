# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Resolver models module.

Frozen Pydantic models supporting the HandlerResolver precedence chain
introduced by OMN-9195 (HandlerResolver Architecture Phase 1). See
`docs/plans/2026-04-18-handler-resolver-architecture.md` for the full spec.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.models.resolver.model_handler_resolution import (
        ModelHandlerResolution,
    )
    from omnibase_core.models.resolver.model_handler_resolver_context import (
        ModelHandlerResolverContext,
    )

__all__ = [
    "ModelHandlerResolution",
    "ModelHandlerResolverContext",
]


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "ModelHandlerResolution": (
        "omnibase_core.models.resolver.model_handler_resolution",
        "ModelHandlerResolution",
    ),
    "ModelHandlerResolverContext": (
        "omnibase_core.models.resolver.model_handler_resolver_context",
        "ModelHandlerResolverContext",
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
