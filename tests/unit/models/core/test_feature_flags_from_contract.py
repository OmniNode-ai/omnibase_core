# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for ModelFeatureFlags.from_contract_declarations() factory."""

import pytest

from omnibase_core.enums.enum_feature_flag_category import EnumFeatureFlagCategory
from omnibase_core.models.contracts.model_contract_feature_flag import (
    ModelContractFeatureFlag,
)
from omnibase_core.models.core.model_feature_flags import ModelFeatureFlags


@pytest.mark.unit
class TestFromContractDeclarations:
    """Tests for from_contract_declarations classmethod."""

    @pytest.mark.unit
    def test_empty_declarations(self) -> None:
        """Empty declaration list produces empty flags."""
        flags = ModelFeatureFlags.from_contract_declarations([])
        assert flags.flags == {}
        assert flags.flag_metadata == {}

    @pytest.mark.unit
    def test_defaults_only(self) -> None:
        """Factory populates flag values from default_value."""
        decls = [
            ModelContractFeatureFlag(name="a", default_value=True),
            ModelContractFeatureFlag(name="b", default_value=False),
        ]
        flags = ModelFeatureFlags.from_contract_declarations(decls)
        assert flags.is_enabled("a") is True
        assert flags.is_enabled("b") is False

    @pytest.mark.unit
    def test_preserves_metadata_description(self) -> None:
        """Factory preserves description in metadata."""
        decls = [
            ModelContractFeatureFlag(
                name="x",
                description="Test description",
            ),
        ]
        flags = ModelFeatureFlags.from_contract_declarations(decls)
        meta = flags.get_flag_metadata("x")
        assert meta is not None
        assert meta.description == "Test description"

    @pytest.mark.unit
    def test_preserves_metadata_owner(self) -> None:
        """Factory preserves owner in metadata."""
        decls = [
            ModelContractFeatureFlag(
                name="x",
                owner="omniintelligence",
            ),
        ]
        flags = ModelFeatureFlags.from_contract_declarations(decls)
        meta = flags.get_flag_metadata("x")
        assert meta is not None
        assert meta.owner == "omniintelligence"

    @pytest.mark.unit
    def test_preserves_category_as_tag(self) -> None:
        """Factory maps category to tags list."""
        decls = [
            ModelContractFeatureFlag(
                name="x",
                category=EnumFeatureFlagCategory.INTELLIGENCE,
            ),
        ]
        flags = ModelFeatureFlags.from_contract_declarations(decls)
        meta = flags.get_flag_metadata("x")
        assert meta is not None
        assert "intelligence" in meta.tags

    @pytest.mark.unit
    def test_multiple_flags(self) -> None:
        """Factory handles multiple declarations."""
        decls = [
            ModelContractFeatureFlag(name="flag_a", default_value=True),
            ModelContractFeatureFlag(name="flag_b", default_value=False),
            ModelContractFeatureFlag(name="flag_c", default_value=True),
        ]
        flags = ModelFeatureFlags.from_contract_declarations(decls)
        assert flags.get_flag_count() == 3
        assert flags.is_enabled("flag_a") is True
        assert flags.is_enabled("flag_b") is False
        assert flags.is_enabled("flag_c") is True

    @pytest.mark.unit
    def test_flag_has_correct_type(self) -> None:
        """Result is a proper ModelFeatureFlags instance."""
        decls = [ModelContractFeatureFlag(name="x")]
        flags = ModelFeatureFlags.from_contract_declarations(decls)
        assert isinstance(flags, ModelFeatureFlags)
        assert flags.has_flag("x")
