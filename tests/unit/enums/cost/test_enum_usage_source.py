# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for cost usage source enum compatibility."""

import pytest

from omnibase_core.enums.cost import EnumUsageSource


@pytest.mark.unit
def test_usage_source_accepts_legacy_api_alias() -> None:
    assert EnumUsageSource("API") == EnumUsageSource.MEASURED
    assert EnumUsageSource("api") == EnumUsageSource.MEASURED


@pytest.mark.unit
def test_usage_source_accepts_legacy_missing_alias() -> None:
    assert EnumUsageSource("MISSING") == EnumUsageSource.UNKNOWN
    assert EnumUsageSource("missing") == EnumUsageSource.UNKNOWN


@pytest.mark.unit
def test_usage_source_accepts_estimated_value() -> None:
    assert EnumUsageSource("estimated") == EnumUsageSource.ESTIMATED


@pytest.mark.unit
def test_usage_source_accepts_legacy_estimated_alias() -> None:
    assert EnumUsageSource("ESTIMATED") == EnumUsageSource.ESTIMATED


@pytest.mark.unit
def test_usage_source_rejects_unknown_value() -> None:
    with pytest.raises(ValueError):
        EnumUsageSource("LOCAL")
