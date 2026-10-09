# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OmniGate typed contract models."""

from __future__ import annotations

import importlib.util
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.enums.enum_omnigate import (
        EnumGateEnforcementAction,
        EnumGateResponse,
        EnumOmniGateCheckType,
    )
    from omnibase_core.models.gate.model_omnigate_check import ModelOmniGateCheck
    from omnibase_core.models.gate.model_omnigate_check_result import (
        ModelOmniGateCheckResult,
    )
    from omnibase_core.models.gate.model_omnigate_config import ModelOmniGateConfig
    from omnibase_core.models.gate.model_omnigate_gate_decision import (
        ModelOmniGateGateDecision,
    )
    from omnibase_core.models.gate.model_omnigate_gate_policy import (
        ModelOmniGateGatePolicy,
    )
    from omnibase_core.models.gate.model_omnigate_identity_policy import (
        ModelOmniGateIdentityPolicy,
    )
    from omnibase_core.models.gate.model_omnigate_receipt import ModelOmniGateReceipt
    from omnibase_core.models.gate.model_omnigate_receipt_policy import (
        ModelOmniGateReceiptPolicy,
    )
    from omnibase_core.models.gate.model_omnigate_validator_ref import (
        ModelOmniGateValidatorRef,
    )

__all__ = [
    "EnumGateEnforcementAction",
    "EnumGateResponse",
    "EnumOmniGateCheckType",
    "ModelOmniGateCheck",
    "ModelOmniGateCheckResult",
    "ModelOmniGateConfig",
    "ModelOmniGateGateDecision",
    "ModelOmniGateGatePolicy",
    "ModelOmniGateIdentityPolicy",
    "ModelOmniGateReceipt",
    "ModelOmniGateReceiptPolicy",
    "ModelOmniGateValidatorRef",
]


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "EnumGateEnforcementAction": (
        "omnibase_core.enums.enum_omnigate",
        "EnumGateEnforcementAction",
    ),
    "EnumGateResponse": ("omnibase_core.enums.enum_omnigate", "EnumGateResponse"),
    "EnumOmniGateCheckType": (
        "omnibase_core.enums.enum_omnigate",
        "EnumOmniGateCheckType",
    ),
    "ModelOmniGateCheck": (
        "omnibase_core.models.gate.model_omnigate_check",
        "ModelOmniGateCheck",
    ),
    "ModelOmniGateCheckResult": (
        "omnibase_core.models.gate.model_omnigate_check_result",
        "ModelOmniGateCheckResult",
    ),
    "ModelOmniGateConfig": (
        "omnibase_core.models.gate.model_omnigate_config",
        "ModelOmniGateConfig",
    ),
    "ModelOmniGateGateDecision": (
        "omnibase_core.models.gate.model_omnigate_gate_decision",
        "ModelOmniGateGateDecision",
    ),
    "ModelOmniGateGatePolicy": (
        "omnibase_core.models.gate.model_omnigate_gate_policy",
        "ModelOmniGateGatePolicy",
    ),
    "ModelOmniGateIdentityPolicy": (
        "omnibase_core.models.gate.model_omnigate_identity_policy",
        "ModelOmniGateIdentityPolicy",
    ),
    "ModelOmniGateReceipt": (
        "omnibase_core.models.gate.model_omnigate_receipt",
        "ModelOmniGateReceipt",
    ),
    "ModelOmniGateReceiptPolicy": (
        "omnibase_core.models.gate.model_omnigate_receipt_policy",
        "ModelOmniGateReceiptPolicy",
    ),
    "ModelOmniGateValidatorRef": (
        "omnibase_core.models.gate.model_omnigate_validator_ref",
        "ModelOmniGateValidatorRef",
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
