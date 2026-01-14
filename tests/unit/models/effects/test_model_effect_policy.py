"""Tests for ModelEffectPolicySpec.

Part of OMN-1147: Effect Classification System test suite.
"""

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_effect_category import EnumEffectCategory
from omnibase_core.enums.enum_effect_policy_level import EnumEffectPolicyLevel
from omnibase_core.models.effects.model_effect_policy import ModelEffectPolicySpec


@pytest.mark.unit
class TestModelEffectPolicySpec:
    """Test cases for ModelEffectPolicySpec model."""

    def test_model_creation_with_all_fields(self) -> None:
        """Test creating model with all fields specified."""
        policy = ModelEffectPolicySpec(
            policy_level=EnumEffectPolicyLevel.STRICT,
            allowed_categories=(EnumEffectCategory.DATABASE,),
            blocked_categories=(EnumEffectCategory.NETWORK,),
            require_mocks_for_categories=(EnumEffectCategory.TIME,),
            allowlist_effect_ids=("db.readonly_query",),
            denylist_effect_ids=("network.unsafe_call",),
        )

        assert policy.policy_level == EnumEffectPolicyLevel.STRICT
        assert EnumEffectCategory.DATABASE in policy.allowed_categories
        assert EnumEffectCategory.NETWORK in policy.blocked_categories
        assert EnumEffectCategory.TIME in policy.require_mocks_for_categories
        assert "db.readonly_query" in policy.allowlist_effect_ids
        assert "network.unsafe_call" in policy.denylist_effect_ids

    def test_model_creation_minimal_required_fields(self) -> None:
        """Test creating model with only required fields."""
        policy = ModelEffectPolicySpec(
            policy_level=EnumEffectPolicyLevel.WARN,
        )

        assert policy.policy_level == EnumEffectPolicyLevel.WARN
        # Check defaults
        assert policy.allowed_categories == ()
        assert policy.blocked_categories == ()
        assert policy.require_mocks_for_categories == ()
        assert policy.allowlist_effect_ids == ()
        assert policy.denylist_effect_ids == ()

    def test_policy_level_is_required(self) -> None:
        """Test that policy_level field is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelEffectPolicySpec()  # type: ignore[call-arg]

        assert "policy_level" in str(exc_info.value)

    def test_immutability_frozen_model(self) -> None:
        """Test that model is immutable (frozen=True in ConfigDict)."""
        policy = ModelEffectPolicySpec(
            policy_level=EnumEffectPolicyLevel.WARN,
        )

        with pytest.raises(ValidationError):
            policy.policy_level = EnumEffectPolicyLevel.STRICT  # type: ignore[misc]

    # Tests for is_category_allowed method

    def test_is_category_allowed_returns_true_for_allowed_categories(self) -> None:
        """Test is_category_allowed returns True for explicitly allowed categories."""
        policy = ModelEffectPolicySpec(
            policy_level=EnumEffectPolicyLevel.STRICT,
            allowed_categories=(EnumEffectCategory.DATABASE, EnumEffectCategory.TIME),
        )

        assert policy.is_category_allowed(EnumEffectCategory.DATABASE) is True
        assert policy.is_category_allowed(EnumEffectCategory.TIME) is True

    def test_is_category_allowed_returns_false_for_blocked_categories(self) -> None:
        """Test is_category_allowed returns False for explicitly blocked categories."""
        policy = ModelEffectPolicySpec(
            policy_level=EnumEffectPolicyLevel.PERMISSIVE,
            blocked_categories=(EnumEffectCategory.NETWORK,),
        )

        assert policy.is_category_allowed(EnumEffectCategory.NETWORK) is False
        # Other categories should still be allowed under PERMISSIVE
        assert policy.is_category_allowed(EnumEffectCategory.DATABASE) is True

    def test_is_category_allowed_blocked_takes_precedence(self) -> None:
        """Test that blocked_categories takes precedence over allowed_categories."""
        policy = ModelEffectPolicySpec(
            policy_level=EnumEffectPolicyLevel.WARN,
            allowed_categories=(EnumEffectCategory.NETWORK,),
            blocked_categories=(EnumEffectCategory.NETWORK,),  # Same category!
        )

        # Blocked should win
        assert policy.is_category_allowed(EnumEffectCategory.NETWORK) is False

    def test_is_category_allowed_strict_policy_blocks_by_default(self) -> None:
        """Test that STRICT policy blocks unspecified categories by default."""
        policy = ModelEffectPolicySpec(
            policy_level=EnumEffectPolicyLevel.STRICT,
        )

        # STRICT policy blocks everything not in allowed_categories
        assert policy.is_category_allowed(EnumEffectCategory.NETWORK) is False
        assert policy.is_category_allowed(EnumEffectCategory.DATABASE) is False
        assert policy.is_category_allowed(EnumEffectCategory.TIME) is False

    def test_is_category_allowed_warn_policy_allows_by_default(self) -> None:
        """Test that WARN policy allows unspecified categories."""
        policy = ModelEffectPolicySpec(
            policy_level=EnumEffectPolicyLevel.WARN,
        )

        # WARN policy allows everything not in blocked_categories
        assert policy.is_category_allowed(EnumEffectCategory.NETWORK) is True
        assert policy.is_category_allowed(EnumEffectCategory.DATABASE) is True

    def test_is_category_allowed_permissive_policy_allows_all(self) -> None:
        """Test that PERMISSIVE policy allows unspecified categories."""
        policy = ModelEffectPolicySpec(
            policy_level=EnumEffectPolicyLevel.PERMISSIVE,
        )

        # PERMISSIVE allows all unless explicitly blocked
        for category in EnumEffectCategory:
            assert policy.is_category_allowed(category) is True

    def test_is_category_allowed_mocked_policy_allows_by_default(self) -> None:
        """Test that MOCKED policy allows unspecified categories."""
        policy = ModelEffectPolicySpec(
            policy_level=EnumEffectPolicyLevel.MOCKED,
        )

        # MOCKED policy allows (but mocks) unless blocked
        assert policy.is_category_allowed(EnumEffectCategory.TIME) is True
        assert policy.is_category_allowed(EnumEffectCategory.RANDOM) is True

    # Tests for requires_mock method

    def test_requires_mock_returns_true_for_mocked_categories(self) -> None:
        """Test requires_mock returns True for categories in require_mocks_for_categories."""
        policy = ModelEffectPolicySpec(
            policy_level=EnumEffectPolicyLevel.WARN,
            require_mocks_for_categories=(
                EnumEffectCategory.TIME,
                EnumEffectCategory.RANDOM,
            ),
        )

        assert policy.requires_mock(EnumEffectCategory.TIME) is True
        assert policy.requires_mock(EnumEffectCategory.RANDOM) is True
        assert policy.requires_mock(EnumEffectCategory.NETWORK) is False

    def test_requires_mock_returns_false_for_non_mocked_categories(self) -> None:
        """Test requires_mock returns False for categories not requiring mocks."""
        policy = ModelEffectPolicySpec(
            policy_level=EnumEffectPolicyLevel.WARN,
            require_mocks_for_categories=(EnumEffectCategory.TIME,),
        )

        assert policy.requires_mock(EnumEffectCategory.NETWORK) is False
        assert policy.requires_mock(EnumEffectCategory.DATABASE) is False
        assert policy.requires_mock(EnumEffectCategory.FILESYSTEM) is False

    def test_requires_mock_mocked_policy_requires_all(self) -> None:
        """Test that MOCKED policy requires mocking for all categories."""
        policy = ModelEffectPolicySpec(
            policy_level=EnumEffectPolicyLevel.MOCKED,
        )

        # MOCKED policy requires mocks for everything
        for category in EnumEffectCategory:
            assert policy.requires_mock(category) is True

    def test_requires_mock_strict_policy_does_not_require_by_default(self) -> None:
        """Test that STRICT policy doesn't automatically require mocks."""
        policy = ModelEffectPolicySpec(
            policy_level=EnumEffectPolicyLevel.STRICT,
        )

        # STRICT blocks but doesn't mock unless specified
        assert policy.requires_mock(EnumEffectCategory.NETWORK) is False
        assert policy.requires_mock(EnumEffectCategory.TIME) is False

    # Tests for is_effect_allowed method

    def test_is_effect_allowed_allowlist_allows_specific_effect(self) -> None:
        """Test is_effect_allowed allows effects in allowlist_effect_ids."""
        policy = ModelEffectPolicySpec(
            policy_level=EnumEffectPolicyLevel.STRICT,
            blocked_categories=(EnumEffectCategory.NETWORK,),
            allowlist_effect_ids=("network.safe_endpoint",),
        )

        # Effect in allowlist is allowed even though category is blocked
        assert (
            policy.is_effect_allowed(
                "network.safe_endpoint", EnumEffectCategory.NETWORK
            )
            is True
        )

    def test_is_effect_allowed_denylist_blocks_specific_effect(self) -> None:
        """Test is_effect_allowed blocks effects in denylist_effect_ids."""
        policy = ModelEffectPolicySpec(
            policy_level=EnumEffectPolicyLevel.PERMISSIVE,
            allowed_categories=(EnumEffectCategory.DATABASE,),
            denylist_effect_ids=("db.dangerous_query",),
        )

        # Effect in denylist is blocked even though category is allowed
        assert (
            policy.is_effect_allowed("db.dangerous_query", EnumEffectCategory.DATABASE)
            is False
        )

    def test_is_effect_allowed_denylist_takes_precedence(self) -> None:
        """Test that denylist takes precedence over allowlist."""
        policy = ModelEffectPolicySpec(
            policy_level=EnumEffectPolicyLevel.WARN,
            allowlist_effect_ids=("test.effect",),
            denylist_effect_ids=("test.effect",),  # Same effect!
        )

        # Denylist should win
        assert (
            policy.is_effect_allowed("test.effect", EnumEffectCategory.NETWORK) is False
        )

    def test_is_effect_allowed_fallback_to_category_rules(self) -> None:
        """Test is_effect_allowed falls back to category rules when effect not listed."""
        policy = ModelEffectPolicySpec(
            policy_level=EnumEffectPolicyLevel.STRICT,
            allowed_categories=(EnumEffectCategory.DATABASE,),
        )

        # Effect not in any list, falls back to category
        assert policy.is_effect_allowed("db.query", EnumEffectCategory.DATABASE) is True
        assert (
            policy.is_effect_allowed("network.call", EnumEffectCategory.NETWORK)
            is False
        )

    def test_extra_fields_forbidden(self) -> None:
        """Test that extra fields are not allowed (extra='forbid')."""
        with pytest.raises(ValidationError) as exc_info:
            ModelEffectPolicySpec(
                policy_level=EnumEffectPolicyLevel.WARN,
                unknown_field="value",  # type: ignore[call-arg]
            )

        assert (
            "unknown_field" in str(exc_info.value).lower()
            or "extra" in str(exc_info.value).lower()
        )

    def test_model_equality(self) -> None:
        """Test model equality comparison."""
        policy1 = ModelEffectPolicySpec(
            policy_level=EnumEffectPolicyLevel.STRICT,
            allowed_categories=(EnumEffectCategory.DATABASE,),
        )
        policy2 = ModelEffectPolicySpec(
            policy_level=EnumEffectPolicyLevel.STRICT,
            allowed_categories=(EnumEffectCategory.DATABASE,),
        )
        policy3 = ModelEffectPolicySpec(
            policy_level=EnumEffectPolicyLevel.WARN,
            allowed_categories=(EnumEffectCategory.DATABASE,),
        )

        assert policy1 == policy2
        assert policy1 != policy3

    def test_model_hashable(self) -> None:
        """Test that frozen model can be hashed."""
        policy = ModelEffectPolicySpec(
            policy_level=EnumEffectPolicyLevel.WARN,
        )

        hash_value = hash(policy)
        assert isinstance(hash_value, int)

    def test_all_policy_levels_accepted(self) -> None:
        """Test that all EnumEffectPolicyLevel values are valid."""
        for level in EnumEffectPolicyLevel:
            policy = ModelEffectPolicySpec(policy_level=level)
            assert policy.policy_level == level

    def test_tuples_are_immutable(self) -> None:
        """Test that all tuple fields are immutable."""
        policy = ModelEffectPolicySpec(
            policy_level=EnumEffectPolicyLevel.WARN,
            allowed_categories=(EnumEffectCategory.DATABASE,),
            blocked_categories=(EnumEffectCategory.NETWORK,),
        )

        assert isinstance(policy.allowed_categories, tuple)
        assert isinstance(policy.blocked_categories, tuple)
        assert isinstance(policy.require_mocks_for_categories, tuple)
        assert isinstance(policy.allowlist_effect_ids, tuple)
        assert isinstance(policy.denylist_effect_ids, tuple)

    def test_from_attributes_enabled(self) -> None:
        """Test that from_attributes=True allows ORM-style creation."""

        class MockORM:
            policy_level = EnumEffectPolicyLevel.MOCKED
            allowed_categories = ()
            blocked_categories = ()
            require_mocks_for_categories = ()
            allowlist_effect_ids = ()
            denylist_effect_ids = ()

        policy = ModelEffectPolicySpec.model_validate(MockORM())
        assert policy.policy_level == EnumEffectPolicyLevel.MOCKED

    def test_model_dump(self) -> None:
        """Test that model can be serialized to dict."""
        policy = ModelEffectPolicySpec(
            policy_level=EnumEffectPolicyLevel.STRICT,
            allowed_categories=(EnumEffectCategory.TIME,),
        )

        data = policy.model_dump()

        assert data["policy_level"] == EnumEffectPolicyLevel.STRICT
        assert EnumEffectCategory.TIME in data["allowed_categories"]
        assert data["blocked_categories"] == ()

    def test_model_json_serialization(self) -> None:
        """Test that model can be serialized to JSON."""
        policy = ModelEffectPolicySpec(
            policy_level=EnumEffectPolicyLevel.PERMISSIVE,
        )

        json_str = policy.model_dump_json()
        assert "permissive" in json_str

    def test_combined_policy_scenario_strict_with_exceptions(self) -> None:
        """Test a realistic policy scenario with STRICT and exceptions."""
        policy = ModelEffectPolicySpec(
            policy_level=EnumEffectPolicyLevel.STRICT,
            # Allow database and filesystem effects
            allowed_categories=(
                EnumEffectCategory.DATABASE,
                EnumEffectCategory.FILESYSTEM,
            ),
            # Require mocks for time-based effects
            require_mocks_for_categories=(EnumEffectCategory.TIME,),
            # Allowlist specific safe network endpoints
            allowlist_effect_ids=(
                "network.health_check",
                "network.metrics",
            ),
            # Denylist dangerous operations
            denylist_effect_ids=("db.drop_table",),
        )

        # Allowed categories work
        assert policy.is_category_allowed(EnumEffectCategory.DATABASE) is True
        assert policy.is_category_allowed(EnumEffectCategory.FILESYSTEM) is True

        # Unspecified categories blocked under STRICT
        assert policy.is_category_allowed(EnumEffectCategory.NETWORK) is False

        # Specific effects override category rules
        assert (
            policy.is_effect_allowed("network.health_check", EnumEffectCategory.NETWORK)
            is True
        )
        assert (
            policy.is_effect_allowed("db.drop_table", EnumEffectCategory.DATABASE)
            is False
        )

        # Mock requirements
        assert policy.requires_mock(EnumEffectCategory.TIME) is True
        assert policy.requires_mock(EnumEffectCategory.DATABASE) is False
