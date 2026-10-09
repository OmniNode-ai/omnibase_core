# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Node Info Models Package.

Focused node information components following ONEX one-model-per-file architecture.
"""

from __future__ import annotations

import importlib.util
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .model_node_categorization import ModelNodeCategorization
    from .model_node_core import ModelNodeCore
    from .model_node_performance_metrics import ModelNodePerformanceMetrics
    from .model_node_performance_summary import ModelNodePerformanceSummary
    from .model_node_quality_indicators import ModelNodeQualityIndicators
    from .model_node_quality_summary import ModelNodeQualitySummary
    from .model_node_timestamps import ModelNodeTimestamps

__all__ = [
    "ModelNodeCategorization",
    "ModelNodeCore",
    "ModelNodePerformanceMetrics",
    "ModelNodePerformanceSummary",
    "ModelNodeQualityIndicators",
    "ModelNodeQualitySummary",
    "ModelNodeTimestamps",
]


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "ModelNodeCategorization": (
        "omnibase_core.models.metadata.node_info.model_node_categorization",
        "ModelNodeCategorization",
    ),
    "ModelNodeCore": (
        "omnibase_core.models.metadata.node_info.model_node_core",
        "ModelNodeCore",
    ),
    "ModelNodePerformanceMetrics": (
        "omnibase_core.models.metadata.node_info.model_node_performance_metrics",
        "ModelNodePerformanceMetrics",
    ),
    "ModelNodePerformanceSummary": (
        "omnibase_core.models.metadata.node_info.model_node_performance_summary",
        "ModelNodePerformanceSummary",
    ),
    "ModelNodeQualityIndicators": (
        "omnibase_core.models.metadata.node_info.model_node_quality_indicators",
        "ModelNodeQualityIndicators",
    ),
    "ModelNodeQualitySummary": (
        "omnibase_core.models.metadata.node_info.model_node_quality_summary",
        "ModelNodeQualitySummary",
    ),
    "ModelNodeTimestamps": (
        "omnibase_core.models.metadata.node_info.model_node_timestamps",
        "ModelNodeTimestamps",
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
