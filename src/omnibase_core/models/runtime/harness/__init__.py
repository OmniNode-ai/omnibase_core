# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Models for the core-resident infra-free local runtime harness (OMN-13420)."""

from __future__ import annotations

import importlib.util
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.models.runtime.harness.model_harness_command import (
        ModelHarnessCommand,
    )
    from omnibase_core.models.runtime.harness.model_harness_infer_requested import (
        ModelHarnessInferRequested,
    )
    from omnibase_core.models.runtime.harness.model_harness_result import (
        ModelHarnessResult,
    )
    from omnibase_core.models.runtime.harness.model_harness_terminal import (
        ModelHarnessTerminal,
    )
    from omnibase_core.models.runtime.harness.model_inference_request import (
        ModelInferenceRequest,
    )
    from omnibase_core.models.runtime.harness.model_inference_result import (
        ModelInferenceResult,
    )
    from omnibase_core.models.runtime.harness.model_projection_row import (
        ModelProjectionRow,
    )

__all__ = [
    "ModelHarnessCommand",
    "ModelHarnessInferRequested",
    "ModelHarnessResult",
    "ModelHarnessTerminal",
    "ModelInferenceRequest",
    "ModelInferenceResult",
    "ModelProjectionRow",
]


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "ModelHarnessCommand": (
        "omnibase_core.models.runtime.harness.model_harness_command",
        "ModelHarnessCommand",
    ),
    "ModelHarnessInferRequested": (
        "omnibase_core.models.runtime.harness.model_harness_infer_requested",
        "ModelHarnessInferRequested",
    ),
    "ModelHarnessResult": (
        "omnibase_core.models.runtime.harness.model_harness_result",
        "ModelHarnessResult",
    ),
    "ModelHarnessTerminal": (
        "omnibase_core.models.runtime.harness.model_harness_terminal",
        "ModelHarnessTerminal",
    ),
    "ModelInferenceRequest": (
        "omnibase_core.models.runtime.harness.model_inference_request",
        "ModelInferenceRequest",
    ),
    "ModelInferenceResult": (
        "omnibase_core.models.runtime.harness.model_inference_result",
        "ModelInferenceResult",
    ),
    "ModelProjectionRow": (
        "omnibase_core.models.runtime.harness.model_projection_row",
        "ModelProjectionRow",
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
