"""Unit tests for EnumBackendType enumeration."""

import pytest

from omnibase_core.enums.enum_backend_type import EnumBackendType
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError


@pytest.mark.unit
class TestEnumBackendType:
    """Test suite for EnumBackendType enumeration."""

    def test_enum_values_exist(self) -> None:
        """Test that all expected backend types are defined."""
        assert EnumBackendType.ENVIRONMENT.value == "environment"
        assert EnumBackendType.DOTENV.value == "dotenv"
        assert EnumBackendType.VAULT.value == "vault"
        assert EnumBackendType.KUBERNETES.value == "kubernetes"
        assert EnumBackendType.FILE.value == "file"

    def test_from_string_valid_lowercase(self) -> None:
        """Test from_string with valid lowercase values."""
        assert EnumBackendType.from_string("environment") == EnumBackendType.ENVIRONMENT
        assert EnumBackendType.from_string("dotenv") == EnumBackendType.DOTENV
        assert EnumBackendType.from_string("vault") == EnumBackendType.VAULT
        assert EnumBackendType.from_string("kubernetes") == EnumBackendType.KUBERNETES
        assert EnumBackendType.from_string("file") == EnumBackendType.FILE

    def test_from_string_valid_uppercase(self) -> None:
        """Test from_string converts uppercase to lowercase correctly."""
        assert EnumBackendType.from_string("ENVIRONMENT") == EnumBackendType.ENVIRONMENT
        assert EnumBackendType.from_string("DOTENV") == EnumBackendType.DOTENV
        assert EnumBackendType.from_string("VAULT") == EnumBackendType.VAULT
        assert EnumBackendType.from_string("KUBERNETES") == EnumBackendType.KUBERNETES
        assert EnumBackendType.from_string("FILE") == EnumBackendType.FILE

    def test_from_string_valid_mixed_case(self) -> None:
        """Test from_string handles mixed case input."""
        assert EnumBackendType.from_string("EnViRoNmEnT") == EnumBackendType.ENVIRONMENT
        assert EnumBackendType.from_string("DoTeNv") == EnumBackendType.DOTENV
        assert EnumBackendType.from_string("VaUlT") == EnumBackendType.VAULT

    def test_from_string_invalid_value_raises_error(self) -> None:
        """Test from_string raises ModelOnexError for invalid values."""
        with pytest.raises(AssertionError) as exc_info:
            EnumBackendType.from_string("invalid_backend")

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "Invalid backend type" in exc_info.value.message
        assert "invalid_backend" in exc_info.value.message
        assert "environment" in exc_info.value.message.lower()
        assert "dotenv" in exc_info.value.message.lower()

    def test_from_string_empty_string_raises_error(self) -> None:
        """Test from_string raises error for empty string."""
        with pytest.raises(AssertionError) as exc_info:
            EnumBackendType.from_string("")

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "Invalid backend type" in exc_info.value.message

    def test_from_string_whitespace_only_raises_error(self) -> None:
        """Test from_string raises error for whitespace-only string."""
        with pytest.raises(AssertionError) as exc_info:
            EnumBackendType.from_string("   ")

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR

    def test_from_string_numeric_string_raises_error(self) -> None:
        """Test from_string raises error for numeric strings."""
        with pytest.raises(AssertionError) as exc_info:
            EnumBackendType.from_string("12345")

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "Invalid backend type: 12345" in exc_info.value.message

    def test_from_string_special_characters_raises_error(self) -> None:
        """Test from_string raises error for strings with special characters."""
        with pytest.raises(AssertionError) as exc_info:
            EnumBackendType.from_string("vault@#$")

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR

    def test_from_string_partial_match_raises_error(self) -> None:
        """Test from_string doesn't accept partial matches."""
        with pytest.raises(AssertionError) as exc_info:
            EnumBackendType.from_string("env")  # Partial match of "environment"

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR

    def test_error_message_contains_all_valid_options(self) -> None:
        """Test error message lists all valid backend types."""
        with pytest.raises(AssertionError) as exc_info:
            EnumBackendType.from_string("invalid")

        error_msg = exc_info.value.message.lower()
        assert "environment" in error_msg
        assert "dotenv" in error_msg
        assert "vault" in error_msg
        assert "kubernetes" in error_msg
        assert "file" in error_msg

    def test_enum_members_count(self) -> None:
        """Test that EnumBackendType has exactly 5 members."""
        members = list(EnumBackendType)
        assert len(members) == 5

    def test_enum_uniqueness(self) -> None:
        """Test that all enum values are unique."""
        values = [e.value for e in EnumBackendType]
        assert len(values) == len(set(values))

    def test_enum_comparison(self) -> None:
        """Test enum member equality comparison."""
        backend1 = EnumBackendType.ENVIRONMENT
        backend2 = EnumBackendType.ENVIRONMENT
        backend3 = EnumBackendType.VAULT

        assert backend1 == backend2
        assert backend1 != backend3
        assert backend1 is backend2  # Same singleton instance

    def test_enum_string_representation(self) -> None:
        """Test enum string representation."""
        assert str(EnumBackendType.ENVIRONMENT) == "EnumBackendType.ENVIRONMENT"
        assert repr(EnumBackendType.VAULT) == "<EnumBackendType.VAULT: 'vault'>"

    def test_enum_iteration(self) -> None:
        """Test iterating over enum members."""
        members = list(EnumBackendType)
        assert len(members) == 5
        assert EnumBackendType.ENVIRONMENT in members
        assert EnumBackendType.VAULT in members

    def test_enum_membership(self) -> None:
        """Test enum membership checks."""
        assert "environment" in [e.value for e in EnumBackendType]
        assert "invalid" not in [e.value for e in EnumBackendType]
