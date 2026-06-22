# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Feature flag registry (OMN-7776).

Single source of truth for every known ONEX feature flag. Declares each flag
with typed metadata (name, description, default, owning repo, gate type) and
exposes a typed resolution API that replaces scattered ``os.getenv("ENABLE_*")``
reads. The omnidash ``/api/settings/feature-flags`` endpoint renders the catalog
emitted by :func:`FeatureFlagRegistry.catalog`.
"""

from __future__ import annotations

from omnibase_core.feature_flags.registry import (
    FEATURE_FLAG_REGISTRY,
    FeatureFlagRegistry,
)
from omnibase_core.models.core.model_feature_flag_definition import (
    ModelFeatureFlagDefinition,
)
from omnibase_core.models.core.model_feature_flag_resolution import (
    ModelFeatureFlagResolution,
)

__all__ = [
    "FEATURE_FLAG_REGISTRY",
    "FeatureFlagRegistry",
    "ModelFeatureFlagDefinition",
    "ModelFeatureFlagResolution",
]
