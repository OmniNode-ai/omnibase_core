# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Context pack schema models for the context pack pipeline (OMN-11678)."""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.enums.enum_context_factor import EnumContextFactor
    from omnibase_core.enums.enum_context_pack_failure import EnumContextPackFailure
    from omnibase_core.enums.enum_context_pack_provenance import (
        EnumContextPackProvenance,
    )
    from omnibase_core.models.pack.model_context_chunk import ModelContextChunk
    from omnibase_core.models.pack.model_context_pack import ModelContextPack
    from omnibase_core.utils.util_context_pack import compute_chunk_id

__all__ = [
    "EnumContextFactor",
    "EnumContextPackFailure",
    "EnumContextPackProvenance",
    "ModelContextChunk",
    "ModelContextPack",
    "compute_chunk_id",
]


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "EnumContextFactor": (
        "omnibase_core.enums.enum_context_factor",
        "EnumContextFactor",
    ),
    "EnumContextPackFailure": (
        "omnibase_core.enums.enum_context_pack_failure",
        "EnumContextPackFailure",
    ),
    "EnumContextPackProvenance": (
        "omnibase_core.enums.enum_context_pack_provenance",
        "EnumContextPackProvenance",
    ),
    "ModelContextChunk": (
        "omnibase_core.models.pack.model_context_chunk",
        "ModelContextChunk",
    ),
    "ModelContextPack": (
        "omnibase_core.models.pack.model_context_pack",
        "ModelContextPack",
    ),
    "compute_chunk_id": ("omnibase_core.utils.util_context_pack", "compute_chunk_id"),
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
