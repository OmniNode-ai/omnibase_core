# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for ModelCanaryTier and ModelCanaryTierAssignments — OMN-10250."""

import pytest
from pydantic import BaseModel


@pytest.mark.unit
def test_model_canary_tier_importable() -> None:
    from omnibase_core.models.governance.model_canary_tier import ModelCanaryTier

    assert issubclass(ModelCanaryTier, BaseModel)


@pytest.mark.unit
def test_model_canary_tier_assignments_importable() -> None:
    from omnibase_core.models.governance.model_canary_tier_assignments import (
        ModelCanaryTierAssignments,
    )

    assert issubclass(ModelCanaryTierAssignments, BaseModel)


@pytest.mark.unit
def test_model_canary_tier_fields() -> None:
    from omnibase_core.models.governance.model_canary_tier import ModelCanaryTier

    tier = ModelCanaryTier(name="canary", repos=["repo-a"], description="Canary tier")
    assert tier.name == "canary"
    assert tier.repos == ["repo-a"]
    assert tier.description == "Canary tier"


@pytest.mark.unit
def test_model_canary_tier_repos_not_empty() -> None:
    from omnibase_core.models.governance.model_canary_tier import ModelCanaryTier

    with pytest.raises(Exception):
        ModelCanaryTier(name="canary", repos=[], description="empty repos")


@pytest.mark.unit
def test_model_canary_tier_assignments_fields() -> None:
    from omnibase_core.models.governance.model_canary_tier import ModelCanaryTier
    from omnibase_core.models.governance.model_canary_tier_assignments import (
        ModelCanaryTierAssignments,
    )

    tier = ModelCanaryTier(name="ga", repos=["repo-b"], description="GA tier")
    assignments = ModelCanaryTierAssignments(version="1.0", tiers=[tier])
    assert assignments.version == "1.0"
    assert len(assignments.tiers) == 1
