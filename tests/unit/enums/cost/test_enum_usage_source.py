# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for cost usage source enum parsing."""

import pytest

from omnibase_core.enums.cost import EnumUsageSource


@pytest.mark.unit
@pytest.mark.parametrize("legacy_value", ["API", "api", "MISSING", "missing"])
def test_usage_source_rejects_legacy_aliases(legacy_value: str) -> None:
    with pytest.raises(ValueError):
        EnumUsageSource(legacy_value)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("measured", EnumUsageSource.MEASURED),
        ("estimated", EnumUsageSource.ESTIMATED),
        ("unknown", EnumUsageSource.UNKNOWN),
    ],
)
def test_usage_source_accepts_canonical_values(
    value: str, expected: EnumUsageSource
) -> None:
    assert EnumUsageSource(value) == expected


@pytest.mark.unit
def test_usage_source_rejects_unknown_value() -> None:
    with pytest.raises(ValueError):
        EnumUsageSource("LOCAL")
