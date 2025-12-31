# SPDX-FileCopyrightText: 2025 OmniNode Team
#
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for ModelContractRef.

Tests the lightweight contract reference model used in validation events
to identify contracts without embedding full contract contents.

Related:
    - OMN-1146: Contract validation event models
    - ModelContractRef: Contract reference model
"""

from pathlib import Path

import pytest
from pydantic import ValidationError

from omnibase_core.models.events.contract_validation import ModelContractRef
from omnibase_core.models.primitives.model_semver import ModelSemVer


@pytest.mark.unit
class TestModelContractRefCreation:
    """Tests for ModelContractRef creation and required fields."""

    def test_contract_ref_creation_with_required_fields(self) -> None:
        """Test that ModelContractRef can be created with only required fields."""
        contract_ref = ModelContractRef(contract_id="test-contract")

        assert contract_ref.contract_id == "test-contract"
        assert contract_ref.path is None
        assert contract_ref.content_hash is None
        assert contract_ref.schema_version is None

    def test_contract_ref_creation_with_all_fields(self) -> None:
        """Test that ModelContractRef can be created with all fields."""
        schema_version = ModelSemVer(major=1, minor=2, patch=3)

        contract_ref = ModelContractRef(
            contract_id="full-contract",
            path=Path("/contracts/full-contract.yaml"),
            content_hash="sha256:abc123def456",
            schema_version=schema_version,
        )

        assert contract_ref.contract_id == "full-contract"
        assert contract_ref.path == Path("/contracts/full-contract.yaml")
        assert contract_ref.content_hash == "sha256:abc123def456"
        assert contract_ref.schema_version == schema_version

    def test_contract_ref_missing_contract_id_raises_error(self) -> None:
        """Test that missing contract_id raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelContractRef()  # type: ignore[call-arg]

        error_str = str(exc_info.value)
        assert "contract_id" in error_str

    def test_contract_ref_accepts_path_as_string(self) -> None:
        """Test that path can be provided as string and is converted to Path."""
        contract_ref = ModelContractRef(
            contract_id="test-contract",
            path="/contracts/test.yaml",  # type: ignore[arg-type]
        )

        assert isinstance(contract_ref.path, Path)
        assert contract_ref.path == Path("/contracts/test.yaml")


@pytest.mark.unit
class TestModelContractRefOptionalFields:
    """Tests for optional fields in ModelContractRef."""

    def test_contract_ref_path_is_optional(self) -> None:
        """Test that path is optional and defaults to None."""
        contract_ref = ModelContractRef(contract_id="test-contract")
        assert contract_ref.path is None

    def test_contract_ref_content_hash_is_optional(self) -> None:
        """Test that content_hash is optional and defaults to None."""
        contract_ref = ModelContractRef(contract_id="test-contract")
        assert contract_ref.content_hash is None

    def test_contract_ref_schema_version_is_optional(self) -> None:
        """Test that schema_version is optional and defaults to None."""
        contract_ref = ModelContractRef(contract_id="test-contract")
        assert contract_ref.schema_version is None

    def test_contract_ref_with_only_path(self) -> None:
        """Test ModelContractRef with only contract_id and path."""
        contract_ref = ModelContractRef(
            contract_id="test-contract",
            path=Path("/contracts/test.yaml"),
        )

        assert contract_ref.contract_id == "test-contract"
        assert contract_ref.path == Path("/contracts/test.yaml")
        assert contract_ref.content_hash is None
        assert contract_ref.schema_version is None

    def test_contract_ref_with_only_content_hash(self) -> None:
        """Test ModelContractRef with only contract_id and content_hash."""
        contract_ref = ModelContractRef(
            contract_id="test-contract",
            content_hash="sha256:abc123",
        )

        assert contract_ref.contract_id == "test-contract"
        assert contract_ref.path is None
        assert contract_ref.content_hash == "sha256:abc123"
        assert contract_ref.schema_version is None

    def test_contract_ref_with_only_schema_version(self) -> None:
        """Test ModelContractRef with only contract_id and schema_version."""
        schema_version = ModelSemVer(major=0, minor=4, patch=0)
        contract_ref = ModelContractRef(
            contract_id="test-contract",
            schema_version=schema_version,
        )

        assert contract_ref.contract_id == "test-contract"
        assert contract_ref.path is None
        assert contract_ref.content_hash is None
        assert contract_ref.schema_version == schema_version


@pytest.mark.unit
class TestModelContractRefImmutability:
    """Tests for frozen/immutable behavior of ModelContractRef."""

    def test_contract_ref_is_frozen(self) -> None:
        """Test that ModelContractRef config has frozen=True."""
        contract_ref = ModelContractRef(contract_id="test-contract")

        config = contract_ref.model_config
        assert config.get("frozen") is True

    def test_contract_ref_cannot_modify_contract_id(self) -> None:
        """Test that contract_id cannot be modified after creation."""
        contract_ref = ModelContractRef(contract_id="test-contract")

        with pytest.raises(ValidationError):
            contract_ref.contract_id = "new-id"  # type: ignore[misc]

    def test_contract_ref_cannot_modify_path(self) -> None:
        """Test that path cannot be modified after creation."""
        contract_ref = ModelContractRef(
            contract_id="test-contract",
            path=Path("/original/path.yaml"),
        )

        with pytest.raises(ValidationError):
            contract_ref.path = Path("/new/path.yaml")  # type: ignore[misc]

    def test_contract_ref_cannot_modify_content_hash(self) -> None:
        """Test that content_hash cannot be modified after creation."""
        contract_ref = ModelContractRef(
            contract_id="test-contract",
            content_hash="sha256:original",
        )

        with pytest.raises(ValidationError):
            contract_ref.content_hash = "sha256:new"  # type: ignore[misc]

    def test_contract_ref_cannot_modify_schema_version(self) -> None:
        """Test that schema_version cannot be modified after creation."""
        contract_ref = ModelContractRef(
            contract_id="test-contract",
            schema_version=ModelSemVer(major=1, minor=0, patch=0),
        )

        with pytest.raises(ValidationError):
            contract_ref.schema_version = ModelSemVer(  # type: ignore[misc]
                major=2, minor=0, patch=0
            )


@pytest.mark.unit
class TestModelContractRefExtraFieldRejection:
    """Tests for extra='forbid' configuration."""

    def test_contract_ref_rejects_extra_fields(self) -> None:
        """Test that extra fields are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelContractRef(
                contract_id="test-contract",
                unknown_field="should_fail",  # type: ignore[call-arg]
            )

        error_str = str(exc_info.value).lower()
        assert "extra" in error_str or "unknown_field" in error_str

    def test_contract_ref_rejects_multiple_extra_fields(self) -> None:
        """Test that multiple extra fields are all rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelContractRef(
                contract_id="test-contract",
                extra_field_1="value1",  # type: ignore[call-arg]
                extra_field_2="value2",  # type: ignore[call-arg]
            )

        error_str = str(exc_info.value).lower()
        assert "extra" in error_str or "extra_field" in error_str

    def test_contract_ref_config_has_extra_forbid(self) -> None:
        """Test that model is configured with extra='forbid'."""
        contract_ref = ModelContractRef(contract_id="test-contract")

        config = contract_ref.model_config
        assert config.get("extra") == "forbid"


@pytest.mark.unit
class TestModelContractRefSerialization:
    """Tests for serialization and deserialization of ModelContractRef."""

    def test_contract_ref_model_dump(self) -> None:
        """Test that ModelContractRef can be dumped to dict."""
        schema_version = ModelSemVer(major=1, minor=2, patch=3)
        contract_ref = ModelContractRef(
            contract_id="test-contract",
            path=Path("/contracts/test.yaml"),
            content_hash="sha256:abc123",
            schema_version=schema_version,
        )

        data = contract_ref.model_dump()

        assert data["contract_id"] == "test-contract"
        assert data["path"] == Path("/contracts/test.yaml")
        assert data["content_hash"] == "sha256:abc123"
        assert "schema_version" in data

    def test_contract_ref_model_dump_json(self) -> None:
        """Test that ModelContractRef can be serialized to JSON."""
        contract_ref = ModelContractRef(
            contract_id="test-contract",
            path=Path("/contracts/test.yaml"),
        )

        json_str = contract_ref.model_dump_json()

        assert isinstance(json_str, str)
        assert "test-contract" in json_str
        assert "contracts" in json_str or "test.yaml" in json_str

    def test_contract_ref_round_trip_serialization(self) -> None:
        """Test that ModelContractRef can be serialized and deserialized."""
        original = ModelContractRef(
            contract_id="test-contract",
            content_hash="sha256:abc123",
        )

        # Round-trip through JSON
        json_str = original.model_dump_json()
        restored = ModelContractRef.model_validate_json(json_str)

        assert restored.contract_id == original.contract_id
        assert restored.content_hash == original.content_hash
        assert restored.path == original.path
        assert restored.schema_version == original.schema_version

    def test_contract_ref_round_trip_with_schema_version(self) -> None:
        """Test round-trip serialization with schema_version."""
        schema_version = ModelSemVer(major=0, minor=4, patch=0)
        original = ModelContractRef(
            contract_id="versioned-contract",
            schema_version=schema_version,
        )

        # Round-trip through dict
        data = original.model_dump()
        restored = ModelContractRef.model_validate(data)

        assert restored.contract_id == original.contract_id
        assert restored.schema_version is not None
        assert restored.schema_version.major == 0
        assert restored.schema_version.minor == 4
        assert restored.schema_version.patch == 0

    def test_contract_ref_model_validate_from_dict(self) -> None:
        """Test that ModelContractRef can be created from dict via model_validate."""
        data = {
            "contract_id": "dict-contract",
            "path": "/contracts/dict.yaml",
            "content_hash": "sha256:dict123",
            "schema_version": {"major": 1, "minor": 0, "patch": 0},
        }

        contract_ref = ModelContractRef.model_validate(data)

        assert contract_ref.contract_id == "dict-contract"
        assert contract_ref.path == Path("/contracts/dict.yaml")
        assert contract_ref.content_hash == "sha256:dict123"
        assert contract_ref.schema_version is not None
        assert contract_ref.schema_version.major == 1


@pytest.mark.unit
class TestModelContractRefFromAttributes:
    """Tests for from_attributes=True configuration."""

    def test_contract_ref_has_from_attributes_config(self) -> None:
        """Test that ModelContractRef is configured with from_attributes=True."""
        contract_ref = ModelContractRef(contract_id="test-contract")

        config = contract_ref.model_config
        assert config.get("from_attributes") is True

    def test_contract_ref_can_be_created_from_object_with_attributes(self) -> None:
        """Test that ModelContractRef can be created from an object with attributes."""

        class ContractRefLike:
            """A class with contract_id attribute."""

            def __init__(self) -> None:
                self.contract_id = "obj-contract"
                self.path = Path("/obj/path.yaml")
                self.content_hash = "sha256:obj123"
                self.schema_version = None

        obj = ContractRefLike()
        contract_ref = ModelContractRef.model_validate(obj)

        assert contract_ref.contract_id == "obj-contract"
        assert contract_ref.path == Path("/obj/path.yaml")
        assert contract_ref.content_hash == "sha256:obj123"


@pytest.mark.unit
class TestModelContractRefHashability:
    """Tests for hashability and set/dict usage."""

    def test_contract_ref_is_hashable(self) -> None:
        """Test that ModelContractRef is hashable (frozen=True)."""
        contract_ref = ModelContractRef(contract_id="test-contract")

        # Should not raise TypeError
        hash_value = hash(contract_ref)
        assert isinstance(hash_value, int)

    def test_contract_ref_can_be_used_in_set(self) -> None:
        """Test that ModelContractRef can be used in sets."""
        ref1 = ModelContractRef(contract_id="contract-1")
        ref2 = ModelContractRef(contract_id="contract-2")
        ref3 = ModelContractRef(contract_id="contract-1")  # Same as ref1

        contract_set = {ref1, ref2, ref3}

        # ref1 and ref3 should be deduplicated
        assert len(contract_set) == 2

    def test_contract_ref_can_be_used_as_dict_key(self) -> None:
        """Test that ModelContractRef can be used as dict key."""
        ref1 = ModelContractRef(contract_id="contract-1")
        ref2 = ModelContractRef(contract_id="contract-2")

        contract_dict = {ref1: "data-1", ref2: "data-2"}

        assert contract_dict[ref1] == "data-1"
        assert contract_dict[ref2] == "data-2"


@pytest.mark.unit
class TestModelContractRefEquality:
    """Tests for equality comparisons."""

    def test_contract_ref_equality_same_values(self) -> None:
        """Test that ModelContractRef instances with same values are equal."""
        ref1 = ModelContractRef(
            contract_id="test-contract",
            content_hash="sha256:abc123",
        )
        ref2 = ModelContractRef(
            contract_id="test-contract",
            content_hash="sha256:abc123",
        )

        assert ref1 == ref2

    def test_contract_ref_inequality_different_contract_id(self) -> None:
        """Test that ModelContractRef instances with different contract_id are not equal."""
        ref1 = ModelContractRef(contract_id="contract-1")
        ref2 = ModelContractRef(contract_id="contract-2")

        assert ref1 != ref2

    def test_contract_ref_inequality_different_path(self) -> None:
        """Test that ModelContractRef instances with different path are not equal."""
        ref1 = ModelContractRef(
            contract_id="test-contract",
            path=Path("/path/1.yaml"),
        )
        ref2 = ModelContractRef(
            contract_id="test-contract",
            path=Path("/path/2.yaml"),
        )

        assert ref1 != ref2

    def test_contract_ref_inequality_different_content_hash(self) -> None:
        """Test that ModelContractRef instances with different content_hash are not equal."""
        ref1 = ModelContractRef(
            contract_id="test-contract",
            content_hash="sha256:hash1",
        )
        ref2 = ModelContractRef(
            contract_id="test-contract",
            content_hash="sha256:hash2",
        )

        assert ref1 != ref2


@pytest.mark.unit
class TestModelContractRefEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_contract_ref_empty_contract_id_raises_validation_error(self) -> None:
        """Test that empty string contract_id is rejected.

        The model enforces min_length=1 on contract_id, so empty strings
        are rejected by Pydantic validation.
        """
        with pytest.raises(ValidationError):
            ModelContractRef(contract_id="")

    def test_contract_ref_with_unicode_contract_id(self) -> None:
        """Test that unicode characters in contract_id are handled."""
        contract_ref = ModelContractRef(
            contract_id="contract-\u4e2d\u6587-test",  # Contains Chinese characters
        )

        assert contract_ref.contract_id == "contract-\u4e2d\u6587-test"

    def test_contract_ref_with_special_characters_in_contract_id(self) -> None:
        """Test that special characters in contract_id are handled."""
        contract_ref = ModelContractRef(
            contract_id="contract/with:special@chars#123",
        )

        assert contract_ref.contract_id == "contract/with:special@chars#123"

    def test_contract_ref_with_long_content_hash(self) -> None:
        """Test that long content hashes are handled."""
        long_hash = "sha512:" + "a" * 128
        contract_ref = ModelContractRef(
            contract_id="test-contract",
            content_hash=long_hash,
        )

        assert contract_ref.content_hash == long_hash

    def test_contract_ref_with_relative_path(self) -> None:
        """Test that relative paths are accepted."""
        contract_ref = ModelContractRef(
            contract_id="test-contract",
            path=Path("relative/path/contract.yaml"),
        )

        assert contract_ref.path == Path("relative/path/contract.yaml")
        assert not contract_ref.path.is_absolute()


@pytest.mark.unit
class TestModelContractRefRepr:
    """Tests for __repr__ output."""

    def test_contract_ref_repr_includes_contract_id(self) -> None:
        """Test that __repr__ includes the contract_id."""
        contract_ref = ModelContractRef(contract_id="repr-test-contract")

        repr_str = repr(contract_ref)

        assert "ModelContractRef" in repr_str
        assert "repr-test-contract" in repr_str
