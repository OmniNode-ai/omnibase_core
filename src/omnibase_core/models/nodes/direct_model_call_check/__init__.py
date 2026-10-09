# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Models of the direct-model-call gate (OMN-20295): one COMPUTE node judges,
one EFFECT node reads and writes."""

from __future__ import annotations

import importlib.util
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.models.nodes.direct_model_call_check.model_direct_model_call_baseline import (
        ModelDirectModelCallBaseline,
    )
    from omnibase_core.models.nodes.direct_model_call_check.model_direct_model_call_baseline_entry import (
        ModelDirectModelCallBaselineEntry,
    )
    from omnibase_core.models.nodes.direct_model_call_check.model_direct_model_call_check_input import (
        ModelDirectModelCallCheckInput,
    )
    from omnibase_core.models.nodes.direct_model_call_check.model_direct_model_call_check_output import (
        ModelDirectModelCallCheckOutput,
    )
    from omnibase_core.models.nodes.direct_model_call_check.model_direct_model_call_check_request import (
        ModelDirectModelCallCheckRequest,
    )
    from omnibase_core.models.nodes.direct_model_call_check.model_direct_model_call_comparison import (
        ModelDirectModelCallComparison,
    )
    from omnibase_core.models.nodes.direct_model_call_check.model_direct_model_call_finding import (
        ModelDirectModelCallFinding,
    )
    from omnibase_core.models.nodes.direct_model_call_check.model_direct_model_call_policy import (
        ModelDirectModelCallPolicy,
    )
    from omnibase_core.models.nodes.direct_model_call_check.model_direct_model_call_scan_input import (
        ModelDirectModelCallScanInput,
    )
    from omnibase_core.models.nodes.direct_model_call_check.model_direct_model_call_source_file import (
        ModelDirectModelCallSourceFile,
    )

__all__ = [
    "ModelDirectModelCallBaselineEntry",
    "ModelDirectModelCallBaseline",
    "ModelDirectModelCallCheckInput",
    "ModelDirectModelCallCheckOutput",
    "ModelDirectModelCallCheckRequest",
    "ModelDirectModelCallComparison",
    "ModelDirectModelCallFinding",
    "ModelDirectModelCallPolicy",
    "ModelDirectModelCallScanInput",
    "ModelDirectModelCallSourceFile",
]


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "ModelDirectModelCallBaseline": (
        "omnibase_core.models.nodes.direct_model_call_check.model_direct_model_call_baseline",
        "ModelDirectModelCallBaseline",
    ),
    "ModelDirectModelCallBaselineEntry": (
        "omnibase_core.models.nodes.direct_model_call_check.model_direct_model_call_baseline_entry",
        "ModelDirectModelCallBaselineEntry",
    ),
    "ModelDirectModelCallCheckInput": (
        "omnibase_core.models.nodes.direct_model_call_check.model_direct_model_call_check_input",
        "ModelDirectModelCallCheckInput",
    ),
    "ModelDirectModelCallCheckOutput": (
        "omnibase_core.models.nodes.direct_model_call_check.model_direct_model_call_check_output",
        "ModelDirectModelCallCheckOutput",
    ),
    "ModelDirectModelCallCheckRequest": (
        "omnibase_core.models.nodes.direct_model_call_check.model_direct_model_call_check_request",
        "ModelDirectModelCallCheckRequest",
    ),
    "ModelDirectModelCallComparison": (
        "omnibase_core.models.nodes.direct_model_call_check.model_direct_model_call_comparison",
        "ModelDirectModelCallComparison",
    ),
    "ModelDirectModelCallFinding": (
        "omnibase_core.models.nodes.direct_model_call_check.model_direct_model_call_finding",
        "ModelDirectModelCallFinding",
    ),
    "ModelDirectModelCallPolicy": (
        "omnibase_core.models.nodes.direct_model_call_check.model_direct_model_call_policy",
        "ModelDirectModelCallPolicy",
    ),
    "ModelDirectModelCallScanInput": (
        "omnibase_core.models.nodes.direct_model_call_check.model_direct_model_call_scan_input",
        "ModelDirectModelCallScanInput",
    ),
    "ModelDirectModelCallSourceFile": (
        "omnibase_core.models.nodes.direct_model_call_check.model_direct_model_call_source_file",
        "ModelDirectModelCallSourceFile",
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
