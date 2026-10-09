# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Progress Models Package.

Focused progress tracking components following ONEX one-model-per-file architecture.
"""

from __future__ import annotations

import importlib.util
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .model_progress_core import ModelProgressCore
    from .model_progress_metrics import ModelProgressMetrics
    from .model_progress_milestones import ModelProgressMilestones
    from .model_progress_timing import ModelProgressTiming

__all__ = [
    "ModelProgressCore",
    "ModelProgressMetrics",
    "ModelProgressMilestones",
    "ModelProgressTiming",
]


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "ModelProgressCore": (
        "omnibase_core.models.infrastructure.progress.model_progress_core",
        "ModelProgressCore",
    ),
    "ModelProgressMetrics": (
        "omnibase_core.models.infrastructure.progress.model_progress_metrics",
        "ModelProgressMetrics",
    ),
    "ModelProgressMilestones": (
        "omnibase_core.models.infrastructure.progress.model_progress_milestones",
        "ModelProgressMilestones",
    ),
    "ModelProgressTiming": (
        "omnibase_core.models.infrastructure.progress.model_progress_timing",
        "ModelProgressTiming",
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
