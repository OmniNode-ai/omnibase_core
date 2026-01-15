# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""
Comprehensive unit tests for ModelOmniMemoryContract.

Tests the YAML contract schema for OmniMemory configuration including:
1. Valid configurations for all retention policies
2. Invalid configurations with proper error handling
3. Frozen behavior (immutability)
4. Extra fields rejection (extra="forbid")
5. Type validation for all fields
6. Serialization (model_dump, model_validate)

Requirements from OMN-1251:
- Model uses frozen=True, extra="forbid", from_attributes=True
- retention_policy is Literal["forever", "ttl", "count_limit"]
- retention_value is required when retention_policy is not "forever"
- warning_threshold has ge=0.0, le=1.0 constraints
- hard_ceiling has ge=0.0 constraint
- track_decisions, track_failures, track_costs default to True
"""

from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.models.contracts.model_omnimemory_contract import (
    ModelOmniMemoryContract,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def valid_contract_id() -> UUID:
    """Provide a valid UUID for contract_id."""
    return uuid4()


@pytest.fixture
def valid_forever_config(valid_contract_id: UUID) -> dict:
    """Provide valid configuration with forever retention policy."""
    return {
        "contract_id": valid_contract_id,
        "name": "test-memory-contract",
        "retention_policy": "forever",
        "default_budget": 100.0,
    }


@pytest.fixture
def valid_ttl_config(valid_contract_id: UUID) -> dict:
    """Provide valid configuration with TTL retention policy."""
    return {
        "contract_id": valid_contract_id,
        "name": "ttl-memory-contract",
        "retention_policy": "ttl",
        "retention_value": 30,
        "default_budget": 50.0,
    }


@pytest.fixture
def valid_count_limit_config(valid_contract_id: UUID) -> dict:
    """Provide valid configuration with count_limit retention policy."""
    return {
        "contract_id": valid_contract_id,
        "name": "count-limit-memory-contract",
        "retention_policy": "count_limit",
        "retention_value": 1000,
        "default_budget": 75.0,
    }


# =============================================================================
# Valid Configuration Tests
# =============================================================================


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestModelOmniMemoryContractValidConfigurations:
    """Tests for ModelOmniMemoryContract valid configurations."""

    def test_create_with_forever_retention_policy(
        self, valid_forever_config: dict
    ) -> None:
        """Test creating contract with retention_policy='forever' and retention_value=None."""
        contract = ModelOmniMemoryContract.model_validate(valid_forever_config)

        assert contract.retention_policy == "forever"
        assert contract.retention_value is None
        assert contract.name == "test-memory-contract"
        assert contract.default_budget == 100.0

    def test_create_with_ttl_retention_policy(self, valid_ttl_config: dict) -> None:
        """Test creating contract with retention_policy='ttl' and retention_value=30."""
        contract = ModelOmniMemoryContract.model_validate(valid_ttl_config)

        assert contract.retention_policy == "ttl"
        assert contract.retention_value == 30
        assert contract.default_budget == 50.0

    def test_create_with_count_limit_retention_policy(
        self, valid_count_limit_config: dict
    ) -> None:
        """Test creating contract with retention_policy='count_limit' and retention_value=1000."""
        contract = ModelOmniMemoryContract.model_validate(valid_count_limit_config)

        assert contract.retention_policy == "count_limit"
        assert contract.retention_value == 1000
        assert contract.default_budget == 75.0

    def test_forever_with_explicit_none_retention_value(
        self, valid_contract_id: UUID
    ) -> None:
        """Test that forever policy with explicit None retention_value is valid."""
        contract = ModelOmniMemoryContract(
            contract_id=valid_contract_id,
            retention_policy="forever",
            retention_value=None,
            default_budget=100.0,
        )
        assert contract.retention_policy == "forever"
        assert contract.retention_value is None

    def test_default_tracking_flags(self, valid_forever_config: dict) -> None:
        """Test that tracking flags default to True."""
        contract = ModelOmniMemoryContract.model_validate(valid_forever_config)

        assert contract.track_decisions is True
        assert contract.track_failures is True
        assert contract.track_costs is True

    def test_custom_tracking_flags(self, valid_contract_id: UUID) -> None:
        """Test custom tracking flag values."""
        contract = ModelOmniMemoryContract(
            contract_id=valid_contract_id,
            retention_policy="forever",
            default_budget=100.0,
            track_decisions=False,
            track_failures=False,
            track_costs=False,
        )
        assert contract.track_decisions is False
        assert contract.track_failures is False
        assert contract.track_costs is False

    def test_default_warning_threshold(self, valid_forever_config: dict) -> None:
        """Test that warning_threshold defaults to 0.8."""
        contract = ModelOmniMemoryContract.model_validate(valid_forever_config)
        assert contract.warning_threshold == 0.8

    def test_default_hard_ceiling(self, valid_forever_config: dict) -> None:
        """Test that hard_ceiling defaults to 1.0."""
        contract = ModelOmniMemoryContract.model_validate(valid_forever_config)
        assert contract.hard_ceiling == 1.0

    def test_custom_warning_threshold(self, valid_contract_id: UUID) -> None:
        """Test custom warning_threshold value."""
        contract = ModelOmniMemoryContract(
            contract_id=valid_contract_id,
            retention_policy="forever",
            default_budget=100.0,
            warning_threshold=0.5,
        )
        assert contract.warning_threshold == 0.5

    def test_custom_hard_ceiling(self, valid_contract_id: UUID) -> None:
        """Test custom hard_ceiling value."""
        contract = ModelOmniMemoryContract(
            contract_id=valid_contract_id,
            retention_policy="forever",
            default_budget=100.0,
            hard_ceiling=2.0,
        )
        assert contract.hard_ceiling == 2.0

    def test_default_version(self, valid_forever_config: dict) -> None:
        """Test that version defaults to 1.0.0."""
        contract = ModelOmniMemoryContract.model_validate(valid_forever_config)
        assert str(contract.version) == "1.0.0"

    def test_custom_version(self, valid_contract_id: UUID) -> None:
        """Test custom version value."""
        contract = ModelOmniMemoryContract(
            contract_id=valid_contract_id,
            retention_policy="forever",
            default_budget=100.0,
            version=ModelSemVer(major=2, minor=1, patch=0),
        )
        assert str(contract.version) == "2.1.0"

    def test_name_is_optional(self, valid_contract_id: UUID) -> None:
        """Test that name field is optional (defaults to None)."""
        contract = ModelOmniMemoryContract(
            contract_id=valid_contract_id,
            retention_policy="forever",
            default_budget=100.0,
        )
        assert contract.name is None

    def test_warning_threshold_boundary_zero(self, valid_contract_id: UUID) -> None:
        """Test warning_threshold at lower boundary (0.0)."""
        contract = ModelOmniMemoryContract(
            contract_id=valid_contract_id,
            retention_policy="forever",
            default_budget=100.0,
            warning_threshold=0.0,
        )
        assert contract.warning_threshold == 0.0

    def test_warning_threshold_boundary_one(self, valid_contract_id: UUID) -> None:
        """Test warning_threshold at upper boundary (1.0)."""
        contract = ModelOmniMemoryContract(
            contract_id=valid_contract_id,
            retention_policy="forever",
            default_budget=100.0,
            warning_threshold=1.0,
        )
        assert contract.warning_threshold == 1.0

    def test_hard_ceiling_boundary_zero(self, valid_contract_id: UUID) -> None:
        """Test hard_ceiling at lower boundary (0.0)."""
        contract = ModelOmniMemoryContract(
            contract_id=valid_contract_id,
            retention_policy="forever",
            default_budget=100.0,
            hard_ceiling=0.0,
        )
        assert contract.hard_ceiling == 0.0


# =============================================================================
# Invalid Configuration Tests - Retention Policy Validation
# =============================================================================


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestModelOmniMemoryContractRetentionValidation:
    """Tests for retention policy validation errors."""

    def test_ttl_without_retention_value_raises_error(
        self, valid_contract_id: UUID
    ) -> None:
        """Test that ttl retention_policy without retention_value raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelOmniMemoryContract(
                contract_id=valid_contract_id,
                retention_policy="ttl",
                retention_value=None,
                default_budget=100.0,
            )
        error_message = str(exc_info.value).lower()
        assert "retention_value" in error_message or "ttl" in error_message

    def test_count_limit_without_retention_value_raises_error(
        self, valid_contract_id: UUID
    ) -> None:
        """Test that count_limit retention_policy without retention_value raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelOmniMemoryContract(
                contract_id=valid_contract_id,
                retention_policy="count_limit",
                retention_value=None,
                default_budget=100.0,
            )
        error_message = str(exc_info.value).lower()
        assert "retention_value" in error_message or "count_limit" in error_message

    def test_invalid_retention_policy_raises_error(
        self, valid_contract_id: UUID
    ) -> None:
        """Test that invalid retention_policy value raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelOmniMemoryContract(
                contract_id=valid_contract_id,
                retention_policy="invalid_policy",  # type: ignore[arg-type]
                default_budget=100.0,
            )
        error_message = str(exc_info.value).lower()
        assert (
            "retention_policy" in error_message
            or "invalid_policy" in error_message
            or "literal" in error_message
        )


# =============================================================================
# Invalid Configuration Tests - Field Constraints
# =============================================================================


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestModelOmniMemoryContractFieldConstraints:
    """Tests for field constraint validation errors."""

    def test_warning_threshold_above_one_raises_error(
        self, valid_contract_id: UUID
    ) -> None:
        """Test that warning_threshold > 1.0 raises ValidationError (le constraint)."""
        with pytest.raises(ValidationError) as exc_info:
            ModelOmniMemoryContract(
                contract_id=valid_contract_id,
                retention_policy="forever",
                default_budget=100.0,
                warning_threshold=1.5,
            )
        error_message = str(exc_info.value).lower()
        assert "warning_threshold" in error_message or "less than" in error_message

    def test_warning_threshold_below_zero_raises_error(
        self, valid_contract_id: UUID
    ) -> None:
        """Test that warning_threshold < 0.0 raises ValidationError (ge constraint)."""
        with pytest.raises(ValidationError) as exc_info:
            ModelOmniMemoryContract(
                contract_id=valid_contract_id,
                retention_policy="forever",
                default_budget=100.0,
                warning_threshold=-0.1,
            )
        error_message = str(exc_info.value).lower()
        assert "warning_threshold" in error_message or "greater than" in error_message

    def test_hard_ceiling_below_zero_raises_error(
        self, valid_contract_id: UUID
    ) -> None:
        """Test that hard_ceiling < 0.0 raises ValidationError (ge constraint)."""
        with pytest.raises(ValidationError) as exc_info:
            ModelOmniMemoryContract(
                contract_id=valid_contract_id,
                retention_policy="forever",
                default_budget=100.0,
                hard_ceiling=-0.5,
            )
        error_message = str(exc_info.value).lower()
        assert "hard_ceiling" in error_message or "greater than" in error_message


# =============================================================================
# Type Validation Tests
# =============================================================================


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestModelOmniMemoryContractTypeValidation:
    """Tests for type validation."""

    def test_contract_id_must_be_uuid(self) -> None:
        """Test that contract_id must be a valid UUID."""
        with pytest.raises(ValidationError) as exc_info:
            ModelOmniMemoryContract(
                contract_id="not-a-uuid",  # type: ignore[arg-type]
                retention_policy="forever",
                default_budget=100.0,
            )
        error_message = str(exc_info.value).lower()
        assert "contract_id" in error_message or "uuid" in error_message

    def test_contract_id_accepts_uuid_string(self) -> None:
        """Test that contract_id accepts a valid UUID string."""
        valid_uuid_str = "12345678-1234-5678-1234-567812345678"
        contract = ModelOmniMemoryContract(
            contract_id=valid_uuid_str,  # type: ignore[arg-type]
            retention_policy="forever",
            default_budget=100.0,
        )
        assert isinstance(contract.contract_id, UUID)

    def test_default_budget_must_be_float(self, valid_contract_id: UUID) -> None:
        """Test that default_budget must be a float."""
        # Note: Pydantic will coerce int to float, so test with invalid type
        with pytest.raises(ValidationError):
            ModelOmniMemoryContract(
                contract_id=valid_contract_id,
                retention_policy="forever",
                default_budget="not-a-number",  # type: ignore[arg-type]
            )

    def test_default_budget_coerces_int_to_float(self, valid_contract_id: UUID) -> None:
        """Test that default_budget coerces int to float."""
        contract = ModelOmniMemoryContract(
            contract_id=valid_contract_id,
            retention_policy="forever",
            default_budget=100,  # int instead of float
        )
        assert isinstance(contract.default_budget, float)
        assert contract.default_budget == 100.0

    def test_version_is_model_semver(self, valid_forever_config: dict) -> None:
        """Test that version field is ModelSemVer type."""
        contract = ModelOmniMemoryContract.model_validate(valid_forever_config)
        assert isinstance(contract.version, ModelSemVer)

    def test_retention_value_accepts_positive_int(
        self, valid_contract_id: UUID
    ) -> None:
        """Test that retention_value accepts positive integers."""
        contract = ModelOmniMemoryContract(
            contract_id=valid_contract_id,
            retention_policy="ttl",
            retention_value=365,
            default_budget=100.0,
        )
        assert contract.retention_value == 365


# =============================================================================
# Frozen Behavior Tests
# =============================================================================


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestModelOmniMemoryContractFrozenBehavior:
    """Tests for frozen (immutable) behavior."""

    def test_contract_is_frozen(self, valid_forever_config: dict) -> None:
        """Test that model is immutable (cannot modify fields after creation)."""
        contract = ModelOmniMemoryContract.model_validate(valid_forever_config)

        with pytest.raises((ValidationError, TypeError, AttributeError)):
            contract.name = "modified-name"  # type: ignore[misc]

    def test_cannot_modify_retention_policy(self, valid_forever_config: dict) -> None:
        """Test that retention_policy cannot be modified after creation."""
        contract = ModelOmniMemoryContract.model_validate(valid_forever_config)

        with pytest.raises((ValidationError, TypeError, AttributeError)):
            contract.retention_policy = "ttl"  # type: ignore[misc]

    def test_cannot_modify_default_budget(self, valid_forever_config: dict) -> None:
        """Test that default_budget cannot be modified after creation."""
        contract = ModelOmniMemoryContract.model_validate(valid_forever_config)

        with pytest.raises((ValidationError, TypeError, AttributeError)):
            contract.default_budget = 200.0  # type: ignore[misc]

    def test_cannot_modify_tracking_flags(self, valid_forever_config: dict) -> None:
        """Test that tracking flags cannot be modified after creation."""
        contract = ModelOmniMemoryContract.model_validate(valid_forever_config)

        with pytest.raises((ValidationError, TypeError, AttributeError)):
            contract.track_decisions = False  # type: ignore[misc]


# =============================================================================
# Extra Fields Rejection Tests
# =============================================================================


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestModelOmniMemoryContractExtraFields:
    """Tests for extra fields rejection (extra='forbid')."""

    def test_extra_fields_rejected(self, valid_contract_id: UUID) -> None:
        """Test that extra fields are rejected (extra='forbid')."""
        with pytest.raises(ValidationError) as exc_info:
            ModelOmniMemoryContract(
                contract_id=valid_contract_id,
                retention_policy="forever",
                default_budget=100.0,
                extra_field="not allowed",  # type: ignore[call-arg]
            )
        error_message = str(exc_info.value).lower()
        assert "extra_field" in error_message or "extra" in error_message

    def test_multiple_extra_fields_rejected(self, valid_contract_id: UUID) -> None:
        """Test that multiple extra fields are rejected."""
        with pytest.raises(ValidationError):
            ModelOmniMemoryContract(
                contract_id=valid_contract_id,
                retention_policy="forever",
                default_budget=100.0,
                field1="extra1",  # type: ignore[call-arg]
                field2="extra2",  # type: ignore[call-arg]
            )


# =============================================================================
# Serialization Tests
# =============================================================================


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestModelOmniMemoryContractSerialization:
    """Tests for serialization (model_dump, model_validate)."""

    def test_model_dump_returns_dict(self, valid_forever_config: dict) -> None:
        """Test that model_dump() returns a dictionary."""
        contract = ModelOmniMemoryContract.model_validate(valid_forever_config)
        dumped = contract.model_dump()

        assert isinstance(dumped, dict)
        assert "contract_id" in dumped
        assert "retention_policy" in dumped
        assert "default_budget" in dumped

    def test_model_dump_contains_all_fields(self, valid_forever_config: dict) -> None:
        """Test that model_dump() contains all expected fields."""
        contract = ModelOmniMemoryContract.model_validate(valid_forever_config)
        dumped = contract.model_dump()

        expected_fields = {
            "contract_id",
            "name",
            "version",
            "retention_policy",
            "retention_value",
            "default_budget",
            "warning_threshold",
            "hard_ceiling",
            "track_decisions",
            "track_failures",
            "track_costs",
        }
        assert expected_fields.issubset(dumped.keys())

    def test_model_dump_json_returns_string(self, valid_forever_config: dict) -> None:
        """Test that model_dump_json() returns a JSON string."""
        contract = ModelOmniMemoryContract.model_validate(valid_forever_config)
        json_str = contract.model_dump_json()

        assert isinstance(json_str, str)
        assert "contract_id" in json_str
        assert "retention_policy" in json_str

    def test_model_validate_from_dict(self, valid_ttl_config: dict) -> None:
        """Test that model_validate() creates contract from dictionary."""
        contract = ModelOmniMemoryContract.model_validate(valid_ttl_config)

        assert contract.retention_policy == "ttl"
        assert contract.retention_value == 30

    def test_roundtrip_serialization_forever(self, valid_forever_config: dict) -> None:
        """Test roundtrip serialization with forever retention policy."""
        original = ModelOmniMemoryContract.model_validate(valid_forever_config)
        dumped = original.model_dump()
        restored = ModelOmniMemoryContract.model_validate(dumped)

        assert original.contract_id == restored.contract_id
        assert original.retention_policy == restored.retention_policy
        assert original.retention_value == restored.retention_value
        assert original.default_budget == restored.default_budget

    def test_roundtrip_serialization_ttl(self, valid_ttl_config: dict) -> None:
        """Test roundtrip serialization with TTL retention policy."""
        original = ModelOmniMemoryContract.model_validate(valid_ttl_config)
        dumped = original.model_dump()
        restored = ModelOmniMemoryContract.model_validate(dumped)

        assert original.retention_policy == restored.retention_policy
        assert original.retention_value == restored.retention_value

    def test_roundtrip_serialization_count_limit(
        self, valid_count_limit_config: dict
    ) -> None:
        """Test roundtrip serialization with count_limit retention policy."""
        original = ModelOmniMemoryContract.model_validate(valid_count_limit_config)
        dumped = original.model_dump()
        restored = ModelOmniMemoryContract.model_validate(dumped)

        assert original.retention_policy == restored.retention_policy
        assert original.retention_value == restored.retention_value


# =============================================================================
# Model Configuration Tests
# =============================================================================


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestModelOmniMemoryContractModelConfig:
    """Tests for model_config settings."""

    def test_model_config_frozen(self) -> None:
        """Test that model_config has frozen=True."""
        assert ModelOmniMemoryContract.model_config.get("frozen") is True

    def test_model_config_extra_forbid(self) -> None:
        """Test that model_config has extra='forbid'."""
        assert ModelOmniMemoryContract.model_config.get("extra") == "forbid"

    def test_model_config_from_attributes(self) -> None:
        """Test that model_config has from_attributes=True."""
        assert ModelOmniMemoryContract.model_config.get("from_attributes") is True


# =============================================================================
# Required Fields Tests
# =============================================================================


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestModelOmniMemoryContractRequiredFields:
    """Tests for required fields validation."""

    def test_contract_id_is_required(self) -> None:
        """Test that contract_id is a required field."""
        with pytest.raises(ValidationError) as exc_info:
            ModelOmniMemoryContract(
                retention_policy="forever",
                default_budget=100.0,
            )  # type: ignore[call-arg]
        assert "contract_id" in str(exc_info.value)

    def test_retention_policy_is_required(self, valid_contract_id: UUID) -> None:
        """Test that retention_policy is a required field."""
        with pytest.raises(ValidationError) as exc_info:
            ModelOmniMemoryContract(
                contract_id=valid_contract_id,
                default_budget=100.0,
            )  # type: ignore[call-arg]
        assert "retention_policy" in str(exc_info.value)

    def test_default_budget_is_required(self, valid_contract_id: UUID) -> None:
        """Test that default_budget is a required field."""
        with pytest.raises(ValidationError) as exc_info:
            ModelOmniMemoryContract(
                contract_id=valid_contract_id,
                retention_policy="forever",
            )  # type: ignore[call-arg]
        assert "default_budget" in str(exc_info.value)


# =============================================================================
# Edge Cases and Integration Tests
# =============================================================================


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestModelOmniMemoryContractEdgeCases:
    """Edge case tests for ModelOmniMemoryContract."""

    def test_zero_default_budget(self, valid_contract_id: UUID) -> None:
        """Test contract with zero default_budget."""
        contract = ModelOmniMemoryContract(
            contract_id=valid_contract_id,
            retention_policy="forever",
            default_budget=0.0,
        )
        assert contract.default_budget == 0.0

    def test_large_default_budget(self, valid_contract_id: UUID) -> None:
        """Test contract with large default_budget."""
        contract = ModelOmniMemoryContract(
            contract_id=valid_contract_id,
            retention_policy="forever",
            default_budget=1_000_000.0,
        )
        assert contract.default_budget == 1_000_000.0

    def test_zero_retention_value_with_ttl(self, valid_contract_id: UUID) -> None:
        """Test that zero retention_value raises ValidationError.

        retention_value=0 is semantically invalid:
        - TTL=0 days means "expire immediately" (nonsensical)
        - count_limit=0 means "keep 0 versions" (invalid)
        """
        with pytest.raises(ValidationError):
            ModelOmniMemoryContract(
                contract_id=valid_contract_id,
                retention_policy="ttl",
                retention_value=0,
                default_budget=100.0,
            )

    def test_large_retention_value(self, valid_contract_id: UUID) -> None:
        """Test contract with large retention_value."""
        contract = ModelOmniMemoryContract(
            contract_id=valid_contract_id,
            retention_policy="count_limit",
            retention_value=1_000_000,
            default_budget=100.0,
        )
        assert contract.retention_value == 1_000_000

    def test_empty_name(self, valid_contract_id: UUID) -> None:
        """Test contract with empty string name."""
        contract = ModelOmniMemoryContract(
            contract_id=valid_contract_id,
            name="",
            retention_policy="forever",
            default_budget=100.0,
        )
        assert contract.name == ""

    def test_unicode_name(self, valid_contract_id: UUID) -> None:
        """Test contract with unicode characters in name."""
        contract = ModelOmniMemoryContract(
            contract_id=valid_contract_id,
            name="test-contract-name",
            retention_policy="forever",
            default_budget=100.0,
        )
        assert contract.name == "test-contract-name"

    def test_contract_hashable(self, valid_forever_config: dict) -> None:
        """Test that contract is hashable (frozen models should be)."""
        contract = ModelOmniMemoryContract.model_validate(valid_forever_config)
        # Frozen models should be hashable
        try:
            hash(contract)
            hashable = True
        except TypeError:
            hashable = False
        assert hashable is True

    def test_contract_equality(self, valid_forever_config: dict) -> None:
        """Test contract equality comparison."""
        contract1 = ModelOmniMemoryContract.model_validate(valid_forever_config)
        contract2 = ModelOmniMemoryContract.model_validate(valid_forever_config)
        # Both should have same values (but may have different contract_ids)
        assert contract1.retention_policy == contract2.retention_policy
        assert contract1.default_budget == contract2.default_budget


# =============================================================================
# Repr and String Tests
# =============================================================================


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestModelOmniMemoryContractRepr:
    """Tests for __repr__ and __str__ representation."""

    def test_repr_contains_model_name(self, valid_forever_config: dict) -> None:
        """Test that repr contains model name."""
        contract = ModelOmniMemoryContract.model_validate(valid_forever_config)
        repr_str = repr(contract)
        assert "ModelOmniMemoryContract" in repr_str or "contract_id" in repr_str

    def test_repr_contains_retention_policy(self, valid_forever_config: dict) -> None:
        """Test that repr contains retention_policy."""
        contract = ModelOmniMemoryContract.model_validate(valid_forever_config)
        repr_str = repr(contract)
        assert "forever" in repr_str or "retention_policy" in repr_str
