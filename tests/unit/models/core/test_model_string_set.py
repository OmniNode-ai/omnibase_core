# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pydantic-boundary regressions for ModelStringSet's uniqueness contract."""

import pytest

from omnibase_core.models.core.model_string_set import ModelStringSet


@pytest.mark.unit
def test_constructor_normalizes_duplicates_in_first_seen_order() -> None:
    """Direct construction enforces the documented unique-element invariant."""
    string_set = ModelStringSet(elements=["beta", "alpha", "beta", "gamma", "alpha"])

    assert string_set.elements == ["beta", "alpha", "gamma"]
    assert string_set.to_list() == ["beta", "alpha", "gamma"]
    assert string_set.size() == 3


@pytest.mark.unit
def test_model_validate_and_json_round_trip_normalize_duplicate_wire_values() -> None:
    """All Pydantic validation entry points preserve deterministic set wire data."""
    validated = ModelStringSet.model_validate({"elements": ["a", "b", "a"]})
    restored = ModelStringSet.model_validate_json('{"elements":["a","b","a","c"]}')

    assert validated.elements == ["a", "b"]
    assert restored.elements == ["a", "b", "c"]
    assert ModelStringSet.model_validate_json(restored.model_dump_json()) == restored
    assert restored.model_dump_json() == '{"elements":["a","b","c"]}'


@pytest.mark.unit
def test_mutators_and_set_operations_remain_idempotent() -> None:
    """Normalization composes with the existing mutable set API."""
    string_set = ModelStringSet(elements=["a", "a"])

    string_set.add("a")
    string_set.add("b")
    string_set.add("b")

    assert string_set.elements == ["a", "b"]
    assert string_set.union(ModelStringSet(elements=["b", "c", "c"])).elements == [
        "a",
        "b",
        "c",
    ]
    assert string_set.intersection(ModelStringSet(elements=["b", "b"])).elements == [
        "b"
    ]
