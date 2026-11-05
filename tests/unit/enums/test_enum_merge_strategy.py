# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Import and serialization tests for EnumMergeStrategy (OMN-18154).

The legacy ``MergeStrategy`` alias was removed after a consumer audit found
no live importers; these tests pin the canonical surface and its absence.
"""

from __future__ import annotations

import importlib
import json
from enum import Enum

import pytest
from pydantic import BaseModel, ConfigDict, ValidationError

from omnibase_core.enums.enum_merge_strategy import EnumMergeStrategy

pytestmark = pytest.mark.unit


class _ModelCarrier(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    strategy: EnumMergeStrategy


class TestEnumMergeStrategyImport:
    def test_canonical_name_importable(self) -> None:
        module = importlib.import_module("omnibase_core.enums.enum_merge_strategy")
        assert module.EnumMergeStrategy is EnumMergeStrategy

    def test_legacy_alias_removed(self) -> None:
        module = importlib.import_module("omnibase_core.enums.enum_merge_strategy")
        assert not hasattr(module, "MergeStrategy")

    def test_adapters_export_canonical_name(self) -> None:
        adapters = importlib.import_module("omnibase_core.adapters")
        assert adapters.EnumMergeStrategy is EnumMergeStrategy
        assert not hasattr(adapters, "MergeStrategy")

    def test_enum_shape(self) -> None:
        assert issubclass(EnumMergeStrategy, str)
        assert issubclass(EnumMergeStrategy, Enum)
        assert [m.value for m in EnumMergeStrategy] == ["merge_queue", "squash_auto"]


class TestEnumMergeStrategySerialization:
    @pytest.mark.parametrize("member", list(EnumMergeStrategy))
    def test_json_round_trip(self, member: EnumMergeStrategy) -> None:
        dumped = json.dumps(member)
        assert dumped == f'"{member.value}"'
        assert EnumMergeStrategy(json.loads(dumped)) is member

    @pytest.mark.parametrize("member", list(EnumMergeStrategy))
    def test_pydantic_round_trip(self, member: EnumMergeStrategy) -> None:
        payload = _ModelCarrier(strategy=member).model_dump_json()
        assert payload == f'{{"strategy":"{member.value}"}}'
        restored = _ModelCarrier.model_validate_json(payload)
        assert restored.strategy is member

    def test_pydantic_rejects_unknown_value(self) -> None:
        with pytest.raises(ValidationError):
            _ModelCarrier.model_validate({"strategy": "rebase"})
