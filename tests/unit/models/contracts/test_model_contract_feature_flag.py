# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for ModelContractFeatureFlag and EnumFeatureFlagCategory."""

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_feature_flag_category import EnumFeatureFlagCategory
from omnibase_core.models.contracts.model_contract_feature_flag import (
    ModelContractFeatureFlag,
)


@pytest.mark.unit
class TestEnumFeatureFlagCategory:
    """Tests for EnumFeatureFlagCategory enum."""

    @pytest.mark.unit
    def test_all_categories_present(self) -> None:
        """All six categories exist."""
        assert len(EnumFeatureFlagCategory) == 6
        expected = {
            "runtime",
            "intelligence",
            "observability",
            "infrastructure",
            "dashboard",
            "general",
        }
        assert {c.value for c in EnumFeatureFlagCategory} == expected

    @pytest.mark.unit
    def test_str_returns_value(self) -> None:
        """str() returns the lowercase value, not 'EnumFeatureFlagCategory.RUNTIME'."""
        assert str(EnumFeatureFlagCategory.RUNTIME) == "runtime"


@pytest.mark.unit
class TestModelContractFeatureFlag:
    """Tests for ModelContractFeatureFlag model."""

    @pytest.mark.unit
    def test_construct_minimal(self) -> None:
        """Minimal construction with name only uses sensible defaults."""
        flag = ModelContractFeatureFlag(name="pattern_enforcement")
        assert flag.name == "pattern_enforcement"
        assert flag.default_value is False
        assert flag.category == EnumFeatureFlagCategory.GENERAL
        assert flag.description == ""
        assert flag.env_var is None
        assert flag.owner is None

    @pytest.mark.unit
    def test_construct_full(self) -> None:
        """Full construction with all fields."""
        flag = ModelContractFeatureFlag(
            name="pattern_enforcement",
            description="Enable code pattern enforcement checks",
            default_value=True,
            env_var="ENABLE_PATTERN_ENFORCEMENT",
            category=EnumFeatureFlagCategory.INTELLIGENCE,
            owner="omniintelligence",
        )
        assert flag.name == "pattern_enforcement"
        assert flag.description == "Enable code pattern enforcement checks"
        assert flag.default_value is True
        assert flag.env_var == "ENABLE_PATTERN_ENFORCEMENT"
        assert flag.category == EnumFeatureFlagCategory.INTELLIGENCE
        assert flag.owner == "omniintelligence"

    @pytest.mark.unit
    def test_frozen(self) -> None:
        """Model is immutable — assignment raises ValidationError."""
        flag = ModelContractFeatureFlag(name="x")
        with pytest.raises(ValidationError):
            flag.name = "y"  # type: ignore[misc]

    @pytest.mark.unit
    def test_extra_forbid(self) -> None:
        """Extra fields are rejected."""
        with pytest.raises(ValidationError):
            ModelContractFeatureFlag(name="x", unexpected_field="bad")  # type: ignore[call-arg]

    @pytest.mark.unit
    def test_name_must_be_snake_case(self) -> None:
        """Name must match ^[a-z][a-z0-9_]*$."""
        with pytest.raises(ValidationError):
            ModelContractFeatureFlag(name="NotSnakeCase")

    @pytest.mark.unit
    def test_name_no_leading_underscore(self) -> None:
        """Name must start with a lowercase letter."""
        with pytest.raises(ValidationError):
            ModelContractFeatureFlag(name="_leading")

    @pytest.mark.unit
    def test_name_no_leading_digit(self) -> None:
        """Name must start with a lowercase letter, not a digit."""
        with pytest.raises(ValidationError):
            ModelContractFeatureFlag(name="1bad")

    @pytest.mark.unit
    def test_name_empty_rejected(self) -> None:
        """Empty name is rejected (min_length=1)."""
        with pytest.raises(ValidationError):
            ModelContractFeatureFlag(name="")

    @pytest.mark.unit
    def test_env_var_must_be_uppercase(self) -> None:
        """env_var must match ^[A-Z][A-Z0-9_]*$."""
        with pytest.raises(ValidationError):
            ModelContractFeatureFlag(name="x", env_var="lowercase_var")

    @pytest.mark.unit
    def test_env_var_none_is_valid(self) -> None:
        """env_var=None is the default and valid."""
        flag = ModelContractFeatureFlag(name="x", env_var=None)
        assert flag.env_var is None

    @pytest.mark.unit
    def test_category_from_string(self) -> None:
        """Category can be provided as a string value."""
        flag = ModelContractFeatureFlag(name="x", category="intelligence")  # type: ignore[arg-type]
        assert flag.category == EnumFeatureFlagCategory.INTELLIGENCE

    @pytest.mark.unit
    def test_round_trip_dict(self) -> None:
        """model_dump() -> reconstruct produces equal model."""
        flag = ModelContractFeatureFlag(
            name="x", default_value=True, env_var="ENABLE_X"
        )
        reconstructed = ModelContractFeatureFlag(**flag.model_dump())
        assert reconstructed == flag

    @pytest.mark.unit
    def test_round_trip_json(self) -> None:
        """model_dump_json() -> model_validate_json() produces equal model."""
        flag = ModelContractFeatureFlag(
            name="test_flag",
            default_value=True,
            category=EnumFeatureFlagCategory.OBSERVABILITY,
        )
        json_str = flag.model_dump_json()
        reconstructed = ModelContractFeatureFlag.model_validate_json(json_str)
        assert reconstructed == flag
