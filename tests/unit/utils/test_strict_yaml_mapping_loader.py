# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Strict duplicate-key regression coverage for typed YAML schema boundaries."""

from __future__ import annotations

import pytest

from omnibase_core.errors.error_duplicate_yaml_mapping_key import (
    DuplicateYamlMappingKeyError,
)
from omnibase_core.utils.util_safe_yaml_loader import load_yaml_mapping_no_duplicates


@pytest.mark.unit
@pytest.mark.parametrize("second_value", ["same", "different"])
def test_typed_yaml_mapping_boundary_rejects_every_duplicate_key(
    second_value: str,
) -> None:
    """Same-value duplicates are as ambiguous as differing-value duplicates."""
    content = f"""\
metadata:
  owner: first
  owner: {second_value}
"""

    with pytest.raises(DuplicateYamlMappingKeyError) as raised:
        load_yaml_mapping_no_duplicates(content, source="unit-contract.yaml")

    assert raised.value.source == "unit-contract.yaml"
    assert raised.value.key == "owner"
    assert raised.value.line == 3


@pytest.mark.unit
def test_typed_yaml_mapping_boundary_accepts_non_overlapping_merge_keys() -> None:
    """YAML merges are supported only when every resolved key is unique."""
    assert load_yaml_mapping_no_duplicates(
        """\
defaults: &defaults
  mode: strict
descriptor:
  settings:
    <<: *defaults
    retries: 3
""",
        source="unit-contract.yaml",
    ) == {
        "defaults": {"mode": "strict"},
        "descriptor": {"settings": {"mode": "strict", "retries": 3}},
    }


@pytest.mark.unit
def test_typed_yaml_mapping_boundary_rejects_merge_key_collision() -> None:
    """Merged and local values cannot rely on YAML precedence semantics."""
    with pytest.raises(DuplicateYamlMappingKeyError, match="duplicate key 'mode'"):
        load_yaml_mapping_no_duplicates(
            """\
defaults: &defaults
  mode: strict
descriptor:
  settings:
    <<: *defaults
    mode: permissive
""",
            source="unit-contract.yaml",
        )


@pytest.mark.unit
def test_typed_yaml_mapping_boundary_rejects_colliding_merged_maps() -> None:
    """Merge order must not decide which typed-schema value survives."""
    with pytest.raises(DuplicateYamlMappingKeyError, match="duplicate key 'mode'"):
        load_yaml_mapping_no_duplicates(
            """\
strict: &strict
  mode: strict
permissive: &permissive
  mode: permissive
descriptor:
  settings:
    <<: [*strict, *permissive]
""",
            source="unit-contract.yaml",
        )
