# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Unit tests for EnumSignatureAlgorithm.

Tests all aspects of the signature algorithm enumeration including:
- ED25519 specific tests (primary focus for handler packaging v1)
- RSA, RSA-PSS, and ECDSA algorithm tests
- Value validation and integrity
- String conversion and comparison
- Enum member existence
- Serialization/deserialization
"""

from enum import Enum

import pytest

from omnibase_core.enums.enum_signature_algorithm import EnumSignatureAlgorithm


@pytest.mark.unit
class TestEnumSignatureAlgorithm:
    """Test cases for EnumSignatureAlgorithm."""

    # -------------------------------------------------------------------------
    # ED25519 Specific Tests (Primary Focus)
    # -------------------------------------------------------------------------

    def test_ed25519_exists(self):
        """Test that ED25519 enum member exists."""
        assert hasattr(EnumSignatureAlgorithm, "ED25519")
        assert EnumSignatureAlgorithm.ED25519 is not None

    def test_ed25519_value_is_lowercase(self):
        """Test that ED25519 value is lowercase 'ed25519'.

        This is the recommended algorithm for handler packaging v1 due to its
        compact signatures, fast verification, and modern security.
        """
        assert EnumSignatureAlgorithm.ED25519.value == "ed25519"
        assert EnumSignatureAlgorithm.ED25519 == "ed25519"

    def test_ed25519_is_string_enum(self):
        """Test that ED25519 inherits from str and Enum."""
        assert isinstance(EnumSignatureAlgorithm.ED25519, str)
        assert isinstance(EnumSignatureAlgorithm.ED25519, Enum)

    def test_ed25519_can_be_created_from_string(self):
        """Test that ED25519 can be created from its string value."""
        created = EnumSignatureAlgorithm("ed25519")
        assert created == EnumSignatureAlgorithm.ED25519
        assert created is EnumSignatureAlgorithm.ED25519

    def test_ed25519_case_sensitivity(self):
        """Test that ED25519 string value is case sensitive."""
        # Must use lowercase "ed25519"
        with pytest.raises(ValueError):
            EnumSignatureAlgorithm("ED25519")  # Uppercase should fail

        with pytest.raises(ValueError):
            EnumSignatureAlgorithm("Ed25519")  # Mixed case should fail

    # -------------------------------------------------------------------------
    # RSA Algorithm Tests
    # -------------------------------------------------------------------------

    def test_rsa_algorithms_exist(self):
        """Test that all RSA algorithms exist (RS256, RS384, RS512)."""
        assert hasattr(EnumSignatureAlgorithm, "RS256")
        assert hasattr(EnumSignatureAlgorithm, "RS384")
        assert hasattr(EnumSignatureAlgorithm, "RS512")

    def test_rsa_algorithm_values(self):
        """Test that RSA algorithms have correct uppercase string values."""
        assert EnumSignatureAlgorithm.RS256.value == "RS256"
        assert EnumSignatureAlgorithm.RS384.value == "RS384"
        assert EnumSignatureAlgorithm.RS512.value == "RS512"

    # -------------------------------------------------------------------------
    # RSA-PSS Algorithm Tests
    # -------------------------------------------------------------------------

    def test_rsa_pss_algorithms_exist(self):
        """Test that all RSA-PSS algorithms exist (PS256, PS384, PS512)."""
        assert hasattr(EnumSignatureAlgorithm, "PS256")
        assert hasattr(EnumSignatureAlgorithm, "PS384")
        assert hasattr(EnumSignatureAlgorithm, "PS512")

    def test_rsa_pss_algorithm_values(self):
        """Test that RSA-PSS algorithms have correct uppercase string values."""
        assert EnumSignatureAlgorithm.PS256.value == "PS256"
        assert EnumSignatureAlgorithm.PS384.value == "PS384"
        assert EnumSignatureAlgorithm.PS512.value == "PS512"

    # -------------------------------------------------------------------------
    # ECDSA Algorithm Tests
    # -------------------------------------------------------------------------

    def test_ecdsa_algorithms_exist(self):
        """Test that all ECDSA algorithms exist (ES256, ES384, ES512)."""
        assert hasattr(EnumSignatureAlgorithm, "ES256")
        assert hasattr(EnumSignatureAlgorithm, "ES384")
        assert hasattr(EnumSignatureAlgorithm, "ES512")

    def test_ecdsa_algorithm_values(self):
        """Test that ECDSA algorithms have correct uppercase string values."""
        assert EnumSignatureAlgorithm.ES256.value == "ES256"
        assert EnumSignatureAlgorithm.ES384.value == "ES384"
        assert EnumSignatureAlgorithm.ES512.value == "ES512"

    # -------------------------------------------------------------------------
    # General Enum Tests
    # -------------------------------------------------------------------------

    def test_enum_inherits_from_str_and_enum(self):
        """Test that EnumSignatureAlgorithm properly inherits from str and Enum."""
        assert issubclass(EnumSignatureAlgorithm, str)
        assert issubclass(EnumSignatureAlgorithm, Enum)

    def test_all_values_are_strings(self):
        """Test that all enum values are strings."""
        for member in EnumSignatureAlgorithm:
            assert isinstance(member.value, str)
            assert isinstance(member, str)

    def test_enum_member_count(self):
        """Test that the enum has exactly 10 members."""
        expected_count = 10
        actual_count = len(list(EnumSignatureAlgorithm))
        assert actual_count == expected_count, (
            f"Expected {expected_count} members, got {actual_count}"
        )

    def test_all_expected_members_exist(self):
        """Test that all expected enum members exist."""
        expected_members = [
            "RS256",
            "RS384",
            "RS512",
            "PS256",
            "PS384",
            "PS512",
            "ES256",
            "ES384",
            "ES512",
            "ED25519",
        ]

        for member_name in expected_members:
            assert hasattr(EnumSignatureAlgorithm, member_name), (
                f"Missing enum member: {member_name}"
            )

    def test_enum_member_uniqueness(self):
        """Test that all enum members have unique values."""
        values = [member.value for member in EnumSignatureAlgorithm]
        unique_values = set(values)
        assert len(values) == len(unique_values), "Enum members must have unique values"

    def test_enum_iteration(self):
        """Test that enum can be iterated over."""
        expected_values = {
            "RS256",
            "RS384",
            "RS512",
            "PS256",
            "PS384",
            "PS512",
            "ES256",
            "ES384",
            "ES512",
            "ed25519",  # Note: ED25519 uses lowercase value
        }
        actual_values = {member.value for member in EnumSignatureAlgorithm}
        assert actual_values == expected_values

    def test_enum_can_be_created_from_string(self):
        """Test that enum members can be created from string values."""
        assert EnumSignatureAlgorithm("RS256") == EnumSignatureAlgorithm.RS256
        assert EnumSignatureAlgorithm("RS384") == EnumSignatureAlgorithm.RS384
        assert EnumSignatureAlgorithm("RS512") == EnumSignatureAlgorithm.RS512
        assert EnumSignatureAlgorithm("PS256") == EnumSignatureAlgorithm.PS256
        assert EnumSignatureAlgorithm("PS384") == EnumSignatureAlgorithm.PS384
        assert EnumSignatureAlgorithm("PS512") == EnumSignatureAlgorithm.PS512
        assert EnumSignatureAlgorithm("ES256") == EnumSignatureAlgorithm.ES256
        assert EnumSignatureAlgorithm("ES384") == EnumSignatureAlgorithm.ES384
        assert EnumSignatureAlgorithm("ES512") == EnumSignatureAlgorithm.ES512
        assert EnumSignatureAlgorithm("ed25519") == EnumSignatureAlgorithm.ED25519

    def test_enum_string_comparison(self):
        """Test that enum members can be compared with strings."""
        assert EnumSignatureAlgorithm.RS256 == "RS256"
        assert EnumSignatureAlgorithm.RS384 == "RS384"
        assert EnumSignatureAlgorithm.RS512 == "RS512"
        assert EnumSignatureAlgorithm.PS256 == "PS256"
        assert EnumSignatureAlgorithm.PS384 == "PS384"
        assert EnumSignatureAlgorithm.PS512 == "PS512"
        assert EnumSignatureAlgorithm.ES256 == "ES256"
        assert EnumSignatureAlgorithm.ES384 == "ES384"
        assert EnumSignatureAlgorithm.ES512 == "ES512"
        assert EnumSignatureAlgorithm.ED25519 == "ed25519"

    def test_invalid_enum_value_raises_error(self):
        """Test that creating enum with invalid value raises ValueError."""
        with pytest.raises(ValueError):
            EnumSignatureAlgorithm("INVALID_ALGORITHM")

        with pytest.raises(ValueError):
            EnumSignatureAlgorithm("SHA256")

    def test_enum_hash_consistency(self):
        """Test that enum members are hashable and consistent."""
        algo_set = {EnumSignatureAlgorithm.RS256, EnumSignatureAlgorithm.ED25519}
        assert len(algo_set) == 2

        # Same enum members should have same hash
        assert hash(EnumSignatureAlgorithm.ED25519) == hash(
            EnumSignatureAlgorithm.ED25519
        )

    def test_enum_repr(self):
        """Test that enum members have proper string representation."""
        assert (
            repr(EnumSignatureAlgorithm.ED25519)
            == "<EnumSignatureAlgorithm.ED25519: 'ed25519'>"
        )
        assert (
            repr(EnumSignatureAlgorithm.RS256)
            == "<EnumSignatureAlgorithm.RS256: 'RS256'>"
        )

    def test_enum_bool_evaluation(self):
        """Test that all enum members evaluate to True in boolean context."""
        for member in EnumSignatureAlgorithm:
            assert bool(member) is True

    def test_enum_serialization_json_compatible(self):
        """Test that enum values are JSON serializable."""
        import json

        for member in EnumSignatureAlgorithm:
            # Should be able to serialize the value
            serialized = json.dumps(member.value)
            deserialized = json.loads(serialized)

            # Should be able to reconstruct the enum
            reconstructed = EnumSignatureAlgorithm(deserialized)
            assert reconstructed == member

    def test_enum_equality_and_identity(self):
        """Test enum equality and identity behavior."""
        # Same enum members should be identical
        assert EnumSignatureAlgorithm.ED25519 is EnumSignatureAlgorithm.ED25519

        # Different enum members should not be identical
        assert EnumSignatureAlgorithm.ED25519 is not EnumSignatureAlgorithm.RS256

        # Equality with strings should work
        assert EnumSignatureAlgorithm.ED25519 == "ed25519"
        assert EnumSignatureAlgorithm.ED25519 != "RS256"

    def test_enum_in_operator(self):
        """Test that 'in' operator works with enum."""
        assert EnumSignatureAlgorithm.ED25519 in EnumSignatureAlgorithm
        assert EnumSignatureAlgorithm.RS256 in EnumSignatureAlgorithm

    def test_enum_with_pydantic_compatibility(self):
        """Test that enum works with Pydantic models."""
        from pydantic import BaseModel

        class TestModel(BaseModel):
            algorithm: EnumSignatureAlgorithm

        # Test valid values
        model = TestModel(algorithm=EnumSignatureAlgorithm.ED25519)
        assert model.algorithm == EnumSignatureAlgorithm.ED25519

        # Test string initialization
        model = TestModel(algorithm="ed25519")
        assert model.algorithm == EnumSignatureAlgorithm.ED25519

        # Test serialization
        data = model.model_dump()
        assert data["algorithm"] == "ed25519"

        # Test deserialization
        new_model = TestModel.model_validate(data)
        assert new_model.algorithm == EnumSignatureAlgorithm.ED25519


@pytest.mark.unit
class TestEnumSignatureAlgorithmEdgeCases:
    """Test edge cases and error conditions for EnumSignatureAlgorithm."""

    def test_enum_with_none_value(self):
        """Test behavior when None is passed."""
        with pytest.raises((TypeError, ValueError)):
            EnumSignatureAlgorithm(None)

    def test_enum_with_empty_string(self):
        """Test behavior with empty string."""
        with pytest.raises(ValueError):
            EnumSignatureAlgorithm("")

    def test_enum_with_whitespace(self):
        """Test behavior with whitespace strings."""
        with pytest.raises(ValueError):
            EnumSignatureAlgorithm(" RS256 ")

        with pytest.raises(ValueError):
            EnumSignatureAlgorithm("ed25519 ")

    def test_enum_pickling(self):
        """Test that enum members can be pickled and unpickled."""
        import pickle

        for member in EnumSignatureAlgorithm:
            pickled = pickle.dumps(member)
            unpickled = pickle.loads(pickled)
            assert unpickled == member
            assert unpickled is member  # Should be the same object

    def test_enum_copy_behavior(self):
        """Test enum behavior with copy operations."""
        import copy

        algorithm = EnumSignatureAlgorithm.ED25519

        # Shallow copy should return the same object
        shallow_copy = copy.copy(algorithm)
        assert shallow_copy is algorithm

        # Deep copy should also return the same object
        deep_copy = copy.deepcopy(algorithm)
        assert deep_copy is algorithm


@pytest.mark.unit
class TestEnumSignatureAlgorithmCategories:
    """Test algorithm categorization by family."""

    def test_jwt_algorithms(self):
        """Test that JWT-compatible algorithms are identified correctly.

        RS*, PS*, and ES* algorithms are designed for JWT signing.
        """
        jwt_algorithms = [
            EnumSignatureAlgorithm.RS256,
            EnumSignatureAlgorithm.RS384,
            EnumSignatureAlgorithm.RS512,
            EnumSignatureAlgorithm.PS256,
            EnumSignatureAlgorithm.PS384,
            EnumSignatureAlgorithm.PS512,
            EnumSignatureAlgorithm.ES256,
            EnumSignatureAlgorithm.ES384,
            EnumSignatureAlgorithm.ES512,
        ]
        # All JWT algorithms should have uppercase values
        for algo in jwt_algorithms:
            assert algo.value.isupper(), f"{algo.name} should have uppercase value"

    def test_eddsa_algorithms(self):
        """Test EdDSA algorithms for artifact verification.

        ED25519 is the recommended algorithm for handler packaging v1.
        """
        eddsa_algorithms = [EnumSignatureAlgorithm.ED25519]
        assert len(eddsa_algorithms) == 1

        # ED25519 should have lowercase value
        assert EnumSignatureAlgorithm.ED25519.value == "ed25519"
        assert EnumSignatureAlgorithm.ED25519.value.islower()

    def test_algorithm_family_groupings(self):
        """Test that algorithms can be grouped by family."""
        rsa_family = {
            EnumSignatureAlgorithm.RS256,
            EnumSignatureAlgorithm.RS384,
            EnumSignatureAlgorithm.RS512,
        }
        pss_family = {
            EnumSignatureAlgorithm.PS256,
            EnumSignatureAlgorithm.PS384,
            EnumSignatureAlgorithm.PS512,
        }
        ecdsa_family = {
            EnumSignatureAlgorithm.ES256,
            EnumSignatureAlgorithm.ES384,
            EnumSignatureAlgorithm.ES512,
        }
        eddsa_family = {EnumSignatureAlgorithm.ED25519}

        all_algorithms = rsa_family | pss_family | ecdsa_family | eddsa_family
        assert len(all_algorithms) == 10

        # Verify no overlap between families
        assert len(rsa_family & pss_family) == 0
        assert len(rsa_family & ecdsa_family) == 0
        assert len(rsa_family & eddsa_family) == 0
        assert len(pss_family & ecdsa_family) == 0
        assert len(pss_family & eddsa_family) == 0
        assert len(ecdsa_family & eddsa_family) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
