# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Corpus classification + per-family normalization layer (OMN-9757).

Pre-validation pipeline that buckets contract YAML files (``corpus_classifier``)
and applies per-family normalization functions (``contract_normalizer``) before
strict Pydantic ``model_validate()`` runs against the canonical contract models.

Each normalization function is pure dict->dict and targets a single documented
migration family. Functions are migration scaffolding only; semantic
preservation of dropped/rewritten content is the caller's responsibility.
"""

from __future__ import annotations

from omnibase_core.normalization.contract_normalizer import (
    is_omnimarket_v0,
    normalize_event_bus,
    normalize_handler_routing,
    normalize_io_model_ref,
    normalize_omnimarket_v0_contract,
    strip_legacy_metadata,
)
from omnibase_core.normalization.corpus_classifier import classify_contract_path

__all__ = [
    "classify_contract_path",
    "is_omnimarket_v0",
    "normalize_event_bus",
    "normalize_handler_routing",
    "normalize_io_model_ref",
    "normalize_omnimarket_v0_contract",
    "strip_legacy_metadata",
]
