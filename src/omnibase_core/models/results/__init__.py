# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Results module - ONEX result models and related structures
"""

from __future__ import annotations

import importlib.util
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.models.core.model_protocol_metadata import ModelGenericMetadata

    from .model_onex_message import ModelOnexMessage
    from .model_onex_message_context import ModelOnexMessageContext
    from .model_onex_result import ModelOnexResult
    from .model_orchestrator_metrics import ModelOrchestratorMetrics
    from .model_unified_summary import ModelUnifiedSummary
    from .model_unified_summary_details import ModelUnifiedSummaryDetails
    from .model_unified_version import ModelUnifiedVersion

__all__ = [
    "ModelGenericMetadata",
    "ModelOnexMessage",
    "ModelOnexMessageContext",
    "ModelOnexResult",
    "ModelOrchestratorMetrics",
    "ModelUnifiedSummary",
    "ModelUnifiedSummaryDetails",
    "ModelUnifiedVersion",
]


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "ModelGenericMetadata": (
        "omnibase_core.models.core.model_protocol_metadata",
        "ModelGenericMetadata",
    ),
    "ModelOnexMessage": (
        "omnibase_core.models.results.model_onex_message",
        "ModelOnexMessage",
    ),
    "ModelOnexMessageContext": (
        "omnibase_core.models.results.model_onex_message_context",
        "ModelOnexMessageContext",
    ),
    "ModelOnexResult": (
        "omnibase_core.models.results.model_onex_result",
        "ModelOnexResult",
    ),
    "ModelOrchestratorMetrics": (
        "omnibase_core.models.results.model_orchestrator_metrics",
        "ModelOrchestratorMetrics",
    ),
    "ModelUnifiedSummary": (
        "omnibase_core.models.results.model_unified_summary",
        "ModelUnifiedSummary",
    ),
    "ModelUnifiedSummaryDetails": (
        "omnibase_core.models.results.model_unified_summary_details",
        "ModelUnifiedSummaryDetails",
    ),
    "ModelUnifiedVersion": (
        "omnibase_core.models.results.model_unified_version",
        "ModelUnifiedVersion",
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
