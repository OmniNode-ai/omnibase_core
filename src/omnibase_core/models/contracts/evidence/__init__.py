# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed contract evidence storage models."""

from __future__ import annotations

import importlib.util
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.enums.enum_stable_proof_kind import EnumStableProofKind
    from omnibase_core.models.contracts.evidence.model_contract_evidence_proof import (
        ModelContractEvidenceProof,
    )
    from omnibase_core.models.contracts.evidence.model_contract_evidence_spec import (
        ModelContractEvidenceSpec,
    )
    from omnibase_core.models.contracts.evidence.model_evidence_provenance import (
        ModelEvidenceProvenance,
    )

__all__: list[str] = [
    "EnumStableProofKind",
    "ModelContractEvidenceProof",
    "ModelContractEvidenceSpec",
    "ModelEvidenceProvenance",
]


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "EnumStableProofKind": (
        "omnibase_core.enums.enum_stable_proof_kind",
        "EnumStableProofKind",
    ),
    "ModelContractEvidenceProof": (
        "omnibase_core.models.contracts.evidence.model_contract_evidence_proof",
        "ModelContractEvidenceProof",
    ),
    "ModelContractEvidenceSpec": (
        "omnibase_core.models.contracts.evidence.model_contract_evidence_spec",
        "ModelContractEvidenceSpec",
    ),
    "ModelEvidenceProvenance": (
        "omnibase_core.models.contracts.evidence.model_evidence_provenance",
        "ModelEvidenceProvenance",
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
