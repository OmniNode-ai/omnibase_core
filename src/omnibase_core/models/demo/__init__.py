# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Demo models for ONEX examples and validation scenarios."""

from __future__ import annotations

import importlib.util
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.enums.enum_demo_recommendation import EnumDemoRecommendation
    from omnibase_core.enums.enum_demo_verdict import EnumDemoVerdict
    from omnibase_core.models.demo.model_demo_config import ModelDemoConfig
    from omnibase_core.models.demo.model_demo_invariant_result import (
        ModelInvariantResult,
    )
    from omnibase_core.models.demo.model_demo_summary import ModelDemoSummary
    from omnibase_core.models.demo.model_demo_validation_report import (
        DEMO_REPORT_SCHEMA_VERSION,
        ModelDemoValidationReport,
    )
    from omnibase_core.models.demo.model_failure_detail import ModelFailureDetail
    from omnibase_core.models.demo.model_sample_result import ModelSampleResult
    from omnibase_core.models.demo.model_validate import (
        ModelSupportClassificationResult,
        ModelSupportTicket,
    )

__all__ = [
    "DEMO_REPORT_SCHEMA_VERSION",
    "EnumDemoRecommendation",
    "EnumDemoVerdict",
    "ModelDemoConfig",
    "ModelDemoSummary",
    "ModelDemoValidationReport",
    "ModelFailureDetail",
    "ModelInvariantResult",
    "ModelSampleResult",
    "ModelSupportClassificationResult",
    "ModelSupportTicket",
]


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "EnumDemoRecommendation": (
        "omnibase_core.enums.enum_demo_recommendation",
        "EnumDemoRecommendation",
    ),
    "EnumDemoVerdict": ("omnibase_core.enums.enum_demo_verdict", "EnumDemoVerdict"),
    "ModelDemoConfig": (
        "omnibase_core.models.demo.model_demo_config",
        "ModelDemoConfig",
    ),
    "ModelInvariantResult": (
        "omnibase_core.models.demo.model_demo_invariant_result",
        "ModelInvariantResult",
    ),
    "ModelDemoSummary": (
        "omnibase_core.models.demo.model_demo_summary",
        "ModelDemoSummary",
    ),
    "DEMO_REPORT_SCHEMA_VERSION": (
        "omnibase_core.models.demo.model_demo_validation_report",
        "DEMO_REPORT_SCHEMA_VERSION",
    ),
    "ModelDemoValidationReport": (
        "omnibase_core.models.demo.model_demo_validation_report",
        "ModelDemoValidationReport",
    ),
    "ModelFailureDetail": (
        "omnibase_core.models.demo.model_failure_detail",
        "ModelFailureDetail",
    ),
    "ModelSampleResult": (
        "omnibase_core.models.demo.model_sample_result",
        "ModelSampleResult",
    ),
    "ModelSupportClassificationResult": (
        "omnibase_core.models.demo.model_validate",
        "ModelSupportClassificationResult",
    ),
    "ModelSupportTicket": (
        "omnibase_core.models.demo.model_validate",
        "ModelSupportTicket",
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
