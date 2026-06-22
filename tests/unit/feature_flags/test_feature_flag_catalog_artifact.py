# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Drift test for the generated feature-flag catalog artifact (OMN-7776).

The committed ``feature_flag_catalog.json`` is the cross-language single source
of truth consumed by the omnidash Express ``/api/settings/feature-flags``
endpoint. It must always match ``FEATURE_FLAG_REGISTRY.static_catalog()``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from omnibase_core.feature_flags import FEATURE_FLAG_REGISTRY

_CATALOG_PATH = (
    Path(__file__).resolve().parents[3]
    / "src"
    / "omnibase_core"
    / "feature_flags"
    / "feature_flag_catalog.json"
)


@pytest.mark.unit
def test_catalog_artifact_exists() -> None:
    assert _CATALOG_PATH.exists(), f"missing catalog artifact: {_CATALOG_PATH}"


@pytest.mark.unit
def test_catalog_artifact_matches_registry() -> None:
    payload = json.loads(_CATALOG_PATH.read_text(encoding="utf-8"))
    assert payload["ticket"] == "OMN-7776"
    assert payload["flags"] == FEATURE_FLAG_REGISTRY.static_catalog(), (
        "feature_flag_catalog.json is stale — regenerate with "
        "`uv run python scripts/gen_feature_flag_catalog.py`"
    )
