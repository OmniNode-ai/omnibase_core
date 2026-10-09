# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Standard evidence bundle models for ONEX workflow proof artifacts."""

from __future__ import annotations

import importlib.util
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.models.evidence_bundle.model_artifact_entry import (
        ModelArtifactEntry,
    )
    from omnibase_core.models.evidence_bundle.model_artifact_manifest import (
        ModelArtifactManifest,
    )
    from omnibase_core.models.evidence_bundle.model_contract_snapshot import (
        ModelContractSnapshot,
    )
    from omnibase_core.models.evidence_bundle.model_evidence_verifier_check import (
        ModelEvidenceVerifierCheck,
    )
    from omnibase_core.models.evidence_bundle.model_evidence_verifier_result import (
        ModelEvidenceVerifierResult,
    )
    from omnibase_core.models.evidence_bundle.model_standard_evidence_bundle import (
        ModelStandardEvidenceBundle,
    )
    from omnibase_core.models.evidence_bundle.model_standard_run_manifest import (
        ModelStandardRunManifest,
    )

__all__ = [
    "ModelArtifactEntry",
    "ModelArtifactManifest",
    "ModelContractSnapshot",
    "ModelEvidenceVerifierCheck",
    "ModelEvidenceVerifierResult",
    "ModelStandardEvidenceBundle",
    "ModelStandardRunManifest",
]


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "ModelArtifactEntry": (
        "omnibase_core.models.evidence_bundle.model_artifact_entry",
        "ModelArtifactEntry",
    ),
    "ModelArtifactManifest": (
        "omnibase_core.models.evidence_bundle.model_artifact_manifest",
        "ModelArtifactManifest",
    ),
    "ModelContractSnapshot": (
        "omnibase_core.models.evidence_bundle.model_contract_snapshot",
        "ModelContractSnapshot",
    ),
    "ModelEvidenceVerifierCheck": (
        "omnibase_core.models.evidence_bundle.model_evidence_verifier_check",
        "ModelEvidenceVerifierCheck",
    ),
    "ModelEvidenceVerifierResult": (
        "omnibase_core.models.evidence_bundle.model_evidence_verifier_result",
        "ModelEvidenceVerifierResult",
    ),
    "ModelStandardEvidenceBundle": (
        "omnibase_core.models.evidence_bundle.model_standard_evidence_bundle",
        "ModelStandardEvidenceBundle",
    ),
    "ModelStandardRunManifest": (
        "omnibase_core.models.evidence_bundle.model_standard_run_manifest",
        "ModelStandardRunManifest",
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
