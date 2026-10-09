# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Canonical runtime-deployment wire DTOs (graduated from omnibase_compat, OMN-13209).

OCC owns the schema source of truth
(``onex_change_control/src/onex_change_control/wire_schemas/``); core owns the
shared Python authority for the lane enum and deployment-proof DTO that the
deployment/OCC nodes import. ``EnumRuntimeLane`` is canonically defined in
``omnibase_core.enums.enum_runtime_lane`` and re-exported here for the wire API.
"""

from __future__ import annotations

import importlib.util
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.enums.enum_runtime_lane import EnumRuntimeLane
    from omnibase_core.models.runtime_deployment.wire.model_runtime_deployment_proof import (
        DeploymentProofStatus,
        ModelRuntimeDeploymentProof,
        ProbeStatus,
    )

__all__: list[str] = [
    "DeploymentProofStatus",
    "EnumRuntimeLane",
    "ModelRuntimeDeploymentProof",
    "ProbeStatus",
]


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "EnumRuntimeLane": ("omnibase_core.enums.enum_runtime_lane", "EnumRuntimeLane"),
    "DeploymentProofStatus": (
        "omnibase_core.models.runtime_deployment.wire.model_runtime_deployment_proof",
        "DeploymentProofStatus",
    ),
    "ModelRuntimeDeploymentProof": (
        "omnibase_core.models.runtime_deployment.wire.model_runtime_deployment_proof",
        "ModelRuntimeDeploymentProof",
    ),
    "ProbeStatus": (
        "omnibase_core.models.runtime_deployment.wire.model_runtime_deployment_proof",
        "ProbeStatus",
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
