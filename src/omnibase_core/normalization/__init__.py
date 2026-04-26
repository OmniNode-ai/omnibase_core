# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Corpus classification + per-family normalization layer (OMN-9757).

Pre-validation pipeline that buckets contract YAML files (``corpus_classifier``)
and applies per-family normalization functions (``contract_normalizer``) before
strict Pydantic ``model_validate()`` runs against the canonical contract models.

These transforms are migration scaffolding, not semantic preservation — see the
per-function docstrings for what is dropped or rewritten.
"""

from __future__ import annotations

from omnibase_core.normalization.contract_normalizer import strip_legacy_metadata
from omnibase_core.normalization.corpus_classifier import classify_contract_path

__all__ = ["classify_contract_path", "strip_legacy_metadata"]
