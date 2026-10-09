# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""ADR extraction domain models (OMN-10691)."""

from __future__ import annotations

import importlib.util
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.models.adr.model_adr_draft import ModelADRDraft
    from omnibase_core.models.adr.model_adr_extraction_metadata import (
        ModelADRExtractionMetadata,
    )
    from omnibase_core.models.adr.model_canary_result import ModelCanaryResult
    from omnibase_core.models.adr.model_decision_extraction import (
        ModelDecisionExtraction,
    )
    from omnibase_core.models.adr.model_document_segment import ModelDocumentSegment
    from omnibase_core.models.adr.model_extraction_score import ModelExtractionScore
    from omnibase_core.models.adr.model_llm_call_evidence import ModelLLMCallEvidence

__all__ = [
    "ModelADRDraft",
    "ModelADRExtractionMetadata",
    "ModelCanaryResult",
    "ModelDecisionExtraction",
    "ModelDocumentSegment",
    "ModelExtractionScore",
    "ModelLLMCallEvidence",
]


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "ModelADRDraft": ("omnibase_core.models.adr.model_adr_draft", "ModelADRDraft"),
    "ModelADRExtractionMetadata": (
        "omnibase_core.models.adr.model_adr_extraction_metadata",
        "ModelADRExtractionMetadata",
    ),
    "ModelCanaryResult": (
        "omnibase_core.models.adr.model_canary_result",
        "ModelCanaryResult",
    ),
    "ModelDecisionExtraction": (
        "omnibase_core.models.adr.model_decision_extraction",
        "ModelDecisionExtraction",
    ),
    "ModelDocumentSegment": (
        "omnibase_core.models.adr.model_document_segment",
        "ModelDocumentSegment",
    ),
    "ModelExtractionScore": (
        "omnibase_core.models.adr.model_extraction_score",
        "ModelExtractionScore",
    ),
    "ModelLLMCallEvidence": (
        "omnibase_core.models.adr.model_llm_call_evidence",
        "ModelLLMCallEvidence",
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
