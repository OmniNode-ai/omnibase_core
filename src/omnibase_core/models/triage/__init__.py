# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Triage models for node_full_triage_orchestrator (OMN-9322)."""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.enums.enum_triage_blast_radius import EnumTriageBlastRadius
    from omnibase_core.enums.enum_triage_freshness import EnumTriageFreshness
    from omnibase_core.enums.enum_triage_probe_status import EnumProbeStatus
    from omnibase_core.enums.enum_triage_severity import EnumTriageSeverity
    from omnibase_core.models.triage.model_triage_finding import ModelTriageFinding
    from omnibase_core.models.triage.model_triage_probe_result import (
        ModelTriageProbeResult,
    )
    from omnibase_core.models.triage.model_triage_report import (
        ModelTriageReport,
        rank_findings,
    )

__all__ = [
    "EnumProbeStatus",
    "EnumTriageBlastRadius",
    "EnumTriageFreshness",
    "EnumTriageSeverity",
    "ModelTriageFinding",
    "ModelTriageProbeResult",
    "ModelTriageReport",
    "rank_findings",
]


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "EnumTriageBlastRadius": (
        "omnibase_core.enums.enum_triage_blast_radius",
        "EnumTriageBlastRadius",
    ),
    "EnumTriageFreshness": (
        "omnibase_core.enums.enum_triage_freshness",
        "EnumTriageFreshness",
    ),
    "EnumProbeStatus": (
        "omnibase_core.enums.enum_triage_probe_status",
        "EnumProbeStatus",
    ),
    "EnumTriageSeverity": (
        "omnibase_core.enums.enum_triage_severity",
        "EnumTriageSeverity",
    ),
    "ModelTriageFinding": (
        "omnibase_core.models.triage.model_triage_finding",
        "ModelTriageFinding",
    ),
    "ModelTriageProbeResult": (
        "omnibase_core.models.triage.model_triage_probe_result",
        "ModelTriageProbeResult",
    ),
    "ModelTriageReport": (
        "omnibase_core.models.triage.model_triage_report",
        "ModelTriageReport",
    ),
    "rank_findings": (
        "omnibase_core.models.triage.model_triage_report",
        "rank_findings",
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
