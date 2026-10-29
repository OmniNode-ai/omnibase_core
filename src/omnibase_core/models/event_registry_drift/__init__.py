# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Event-registry drift check models (OMN-21416).

The check returns the canonical OMN-2362 generic validator report
(:mod:`omnibase_core.models.validation.model_validation_report`), not a
per-node fork.
"""

from __future__ import annotations

import importlib.util
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.models.event_registry_drift.model_event_registration import (
        ModelEventRegistration,
    )
    from omnibase_core.models.event_registry_drift.model_event_registry_drift_baseline import (
        ModelEventRegistryDriftBaseline,
    )
    from omnibase_core.models.event_registry_drift.model_event_registry_drift_check_input import (
        ModelEventRegistryDriftCheckInput,
    )

__all__ = [
    "ModelEventRegistration",
    "ModelEventRegistryDriftBaseline",
    "ModelEventRegistryDriftCheckInput",
]

# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "ModelEventRegistration": (
        "omnibase_core.models.event_registry_drift.model_event_registration",
        "ModelEventRegistration",
    ),
    "ModelEventRegistryDriftBaseline": (
        "omnibase_core.models.event_registry_drift.model_event_registry_drift_baseline",
        "ModelEventRegistryDriftBaseline",
    ),
    "ModelEventRegistryDriftCheckInput": (
        "omnibase_core.models.event_registry_drift.model_event_registry_drift_check_input",
        "ModelEventRegistryDriftCheckInput",
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
