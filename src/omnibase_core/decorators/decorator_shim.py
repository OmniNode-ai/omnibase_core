# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""@shim decorator for annotating temporary compatibility shims.

Marks functions or methods as shims that must be removed by a deadline.
The scanner (node_shim_scanner in omnimarket) reads these annotations via
AST to report expired or expiring shims.
"""

from __future__ import annotations

import datetime
from collections.abc import Callable
from functools import wraps
from typing import ParamSpec, TypeVar

from omnibase_core.models.decorators.model_shim_metadata import ModelShimMetadata

__all__ = [
    "SHIM_ATTR",
    "ModelShimMetadata",
    "get_shim_metadata",
    "has_shim",
    "shim",
]

P = ParamSpec("P")
R = TypeVar("R")

SHIM_ATTR = "_shim_metadata"


def shim(
    ticket_id: str,
    expires_on: datetime.date,
    reason: str,
    replacement: str,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Mark a function or method as a temporary compatibility shim.

    Attaches ModelShimMetadata for introspection by node_shim_scanner.
    Does NOT alter runtime behavior — the decorated callable executes unchanged.

    Args:
        ticket_id: Linear ticket tracking removal (e.g. "OMN-1234").
        expires_on: Date by which the shim must be removed.
        reason: Why the shim exists.
        replacement: The canonical path or function to migrate to.

    Example:
        @shim(
            ticket_id="OMN-9999",
            expires_on=datetime.date(2026, 6, 1),
            reason="Legacy wire DTO compatibility until OCC migration lands",
            replacement="omnibase_compat.dtos.ModelFooDto",
        )
        def legacy_transform(data: dict) -> ModelFoo:
            ...
    """
    metadata = ModelShimMetadata(
        ticket_id=ticket_id,
        expires_on=expires_on,
        reason=reason,
        replacement=replacement,
    )

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            return func(*args, **kwargs)

        setattr(wrapper, SHIM_ATTR, metadata)
        return wrapper

    return decorator


def get_shim_metadata(func: object) -> ModelShimMetadata | None:
    """Return the ModelShimMetadata attached to a @shim-decorated callable."""
    return getattr(func, SHIM_ATTR, None)


def has_shim(func: object) -> bool:
    """Return True if the callable was decorated with @shim."""
    return hasattr(func, SHIM_ATTR)
