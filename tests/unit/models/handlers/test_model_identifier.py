# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for ModelIdentifier."""

import pytest
from pydantic import ValidationError

from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.handlers.model_identifier import ModelIdentifier
from omnibase_core.models.primitives.model_semver import ModelSemVer


@pytest.mark.unit
class TestModelIdentifierInstantiation:
    """Tests for ModelIdentifier instantiation."""

    def test_basic_instantiation_with_namespace_and_name(self) -> None:
        """Test creating identifier with required namespace and name."""
        identifier = ModelIdentifier(namespace="onex", name="compute")
        assert identifier.namespace == "onex"
        assert identifier.name == "compute"
        assert identifier.variant is None
        assert identifier.version is None

    def test_instantiation_with_variant(self) -> None:
        """Test creating identifier with optional variant."""
        identifier = ModelIdentifier(namespace="vendor", name="handler", variant="v2")
        assert identifier.namespace == "vendor"
        assert identifier.name == "handler"
        assert identifier.variant == "v2"

    def test_instantiation_with_version(self) -> None:
        """Test creating identifier with optional semantic version."""
        version = ModelSemVer(major=1, minor=2, patch=3)
        identifier = ModelIdentifier(namespace="onex", name="compute", version=version)
        assert identifier.namespace == "onex"
        assert identifier.name == "compute"
        assert identifier.version == version

    def test_instantiation_with_all_fields(self) -> None:
        """Test creating identifier with all optional fields."""
        version = ModelSemVer(major=2, minor=0, patch=0)
        identifier = ModelIdentifier(
            namespace="vendor",
            name="handler",
            variant="async",
            version=version,
        )
        assert identifier.namespace == "vendor"
        assert identifier.name == "handler"
        assert identifier.variant == "async"
        assert identifier.version == version


@pytest.mark.unit
class TestModelIdentifierParse:
    """Tests for ModelIdentifier.parse() method."""

    def test_parse_basic_format(self) -> None:
        """Test parsing 'namespace:name' format."""
        identifier = ModelIdentifier.parse("onex:compute")
        assert identifier.namespace == "onex"
        assert identifier.name == "compute"
        assert identifier.variant is None

    def test_parse_with_variant(self) -> None:
        """Test parsing 'namespace:name@variant' format."""
        identifier = ModelIdentifier.parse("vendor:custom@v2")
        assert identifier.namespace == "vendor"
        assert identifier.name == "custom"
        assert identifier.variant == "v2"

    def test_parse_variant_starting_with_number(self) -> None:
        """Test parsing variant that starts with a number."""
        identifier = ModelIdentifier.parse("onex:handler@2024")
        assert identifier.namespace == "onex"
        assert identifier.name == "handler"
        assert identifier.variant == "2024"

    def test_parse_with_underscores(self) -> None:
        """Test parsing identifiers with underscores."""
        identifier = ModelIdentifier.parse("my_vendor:my_handler@my_variant")
        assert identifier.namespace == "my_vendor"
        assert identifier.name == "my_handler"
        assert identifier.variant == "my_variant"

    def test_parse_with_hyphens(self) -> None:
        """Test parsing identifiers with hyphens."""
        identifier = ModelIdentifier.parse("my-vendor:my-handler@my-variant")
        assert identifier.namespace == "my-vendor"
        assert identifier.name == "my-handler"
        assert identifier.variant == "my-variant"

    def test_parse_empty_string_raises_error(self) -> None:
        """Test that parsing empty string raises ModelOnexError."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelIdentifier.parse("")
        assert "Cannot parse empty string" in str(exc_info.value)

    def test_parse_invalid_format_no_colon_raises_error(self) -> None:
        """Test that parsing without colon raises ModelOnexError."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelIdentifier.parse("onexcompute")
        assert "Invalid identifier format" in str(exc_info.value)

    def test_parse_invalid_format_multiple_colons_raises_error(self) -> None:
        """Test that parsing with multiple colons raises ModelOnexError."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelIdentifier.parse("a:b:c")
        assert "Invalid identifier format" in str(exc_info.value)

    def test_parse_invalid_namespace_starting_with_number(self) -> None:
        """Test that namespace starting with number raises error."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelIdentifier.parse("1vendor:handler")
        assert "Invalid identifier format" in str(exc_info.value)

    def test_parse_invalid_name_starting_with_number(self) -> None:
        """Test that name starting with number raises error."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelIdentifier.parse("vendor:1handler")
        assert "Invalid identifier format" in str(exc_info.value)


@pytest.mark.unit
class TestModelIdentifierStringRepresentation:
    """Tests for ModelIdentifier string representation."""

    def test_str_returns_canonical_form_without_variant(self) -> None:
        """Test __str__ returns 'namespace:name' format."""
        identifier = ModelIdentifier(namespace="onex", name="compute")
        assert str(identifier) == "onex:compute"

    def test_str_returns_canonical_form_with_variant(self) -> None:
        """Test __str__ returns 'namespace:name@variant' format."""
        identifier = ModelIdentifier(namespace="vendor", name="handler", variant="v2")
        assert str(identifier) == "vendor:handler@v2"

    def test_repr_without_variant(self) -> None:
        """Test __repr__ without variant."""
        identifier = ModelIdentifier(namespace="onex", name="compute")
        repr_str = repr(identifier)
        assert "ModelIdentifier" in repr_str
        assert "namespace='onex'" in repr_str
        assert "name='compute'" in repr_str

    def test_repr_with_variant(self) -> None:
        """Test __repr__ with variant."""
        identifier = ModelIdentifier(namespace="vendor", name="handler", variant="v2")
        repr_str = repr(identifier)
        assert "ModelIdentifier" in repr_str
        assert "variant='v2'" in repr_str


@pytest.mark.unit
class TestModelIdentifierHashAndEquality:
    """Tests for ModelIdentifier hash and equality."""

    def test_hash_for_dict_keys(self) -> None:
        """Test that ModelIdentifier can be used as dict keys."""
        id1 = ModelIdentifier(namespace="onex", name="compute")
        id2 = ModelIdentifier(namespace="onex", name="compute")
        cache = {id1: "cached_value"}
        assert id2 in cache
        assert cache[id2] == "cached_value"

    def test_hash_consistency(self) -> None:
        """Test that hash is consistent for equal identifiers."""
        id1 = ModelIdentifier(namespace="onex", name="compute", variant="v1")
        id2 = ModelIdentifier(namespace="onex", name="compute", variant="v1")
        assert hash(id1) == hash(id2)

    def test_hash_differs_for_different_identifiers(self) -> None:
        """Test that hash differs for different identifiers."""
        id1 = ModelIdentifier(namespace="onex", name="compute")
        id2 = ModelIdentifier(namespace="onex", name="effect")
        assert hash(id1) != hash(id2)

    def test_equality_same_identifiers(self) -> None:
        """Test equality for identical identifiers."""
        id1 = ModelIdentifier(namespace="onex", name="compute")
        id2 = ModelIdentifier(namespace="onex", name="compute")
        assert id1 == id2

    def test_equality_different_namespace(self) -> None:
        """Test inequality for different namespaces."""
        id1 = ModelIdentifier(namespace="onex", name="compute")
        id2 = ModelIdentifier(namespace="vendor", name="compute")
        assert id1 != id2

    def test_equality_different_name(self) -> None:
        """Test inequality for different names."""
        id1 = ModelIdentifier(namespace="onex", name="compute")
        id2 = ModelIdentifier(namespace="onex", name="effect")
        assert id1 != id2

    def test_equality_different_variant(self) -> None:
        """Test inequality for different variants."""
        id1 = ModelIdentifier(namespace="onex", name="compute", variant="v1")
        id2 = ModelIdentifier(namespace="onex", name="compute", variant="v2")
        assert id1 != id2

    def test_equality_ignores_version(self) -> None:
        """Test that equality ignores version field."""
        v1 = ModelSemVer(major=1, minor=0, patch=0)
        v2 = ModelSemVer(major=2, minor=0, patch=0)
        id1 = ModelIdentifier(namespace="onex", name="compute", version=v1)
        id2 = ModelIdentifier(namespace="onex", name="compute", version=v2)
        assert id1 == id2  # Version is NOT considered for equality

    def test_equality_with_non_identifier(self) -> None:
        """Test inequality with non-ModelIdentifier objects."""
        identifier = ModelIdentifier(namespace="onex", name="compute")
        assert identifier != "onex:compute"
        assert identifier != {"namespace": "onex", "name": "compute"}
        assert identifier != 42

    def test_in_set(self) -> None:
        """Test that identifiers can be used in sets."""
        id1 = ModelIdentifier(namespace="onex", name="compute")
        id2 = ModelIdentifier(namespace="onex", name="compute")  # Same as id1
        id3 = ModelIdentifier(namespace="onex", name="effect")
        identifier_set = {id1, id2, id3}
        assert len(identifier_set) == 2  # id1 and id2 are equal


@pytest.mark.unit
class TestModelIdentifierQualifiedName:
    """Tests for ModelIdentifier.qualified_name property."""

    def test_qualified_name_without_variant(self) -> None:
        """Test qualified_name property returns canonical form."""
        identifier = ModelIdentifier(namespace="onex", name="compute")
        assert identifier.qualified_name == "onex:compute"

    def test_qualified_name_with_variant(self) -> None:
        """Test qualified_name property with variant."""
        identifier = ModelIdentifier(namespace="vendor", name="handler", variant="v2")
        assert identifier.qualified_name == "vendor:handler@v2"

    def test_qualified_name_equals_str(self) -> None:
        """Test that qualified_name equals __str__ result."""
        identifier = ModelIdentifier(namespace="onex", name="compute", variant="v1")
        assert identifier.qualified_name == str(identifier)


@pytest.mark.unit
class TestModelIdentifierMatches:
    """Tests for ModelIdentifier.matches() method."""

    def test_matches_base_matches_any_variant(self) -> None:
        """Test that base identifier (no variant) matches any variant."""
        base = ModelIdentifier(namespace="onex", name="compute")
        specific = ModelIdentifier(namespace="onex", name="compute", variant="v2")
        assert base.matches(specific)  # Base matches specific

    def test_matches_specific_requires_matching_variant(self) -> None:
        """Test that specific identifier requires matching variant."""
        base = ModelIdentifier(namespace="onex", name="compute")
        specific = ModelIdentifier(namespace="onex", name="compute", variant="v2")
        assert not specific.matches(base)  # Specific does NOT match base

    def test_matches_same_variant(self) -> None:
        """Test matching with same variant."""
        id1 = ModelIdentifier(namespace="onex", name="compute", variant="v2")
        id2 = ModelIdentifier(namespace="onex", name="compute", variant="v2")
        assert id1.matches(id2)

    def test_matches_different_variant_fails(self) -> None:
        """Test matching fails for different variants."""
        id1 = ModelIdentifier(namespace="onex", name="compute", variant="v1")
        id2 = ModelIdentifier(namespace="onex", name="compute", variant="v2")
        assert not id1.matches(id2)

    def test_matches_different_namespace_fails(self) -> None:
        """Test matching fails for different namespaces."""
        id1 = ModelIdentifier(namespace="onex", name="compute")
        id2 = ModelIdentifier(namespace="vendor", name="compute")
        assert not id1.matches(id2)

    def test_matches_different_name_fails(self) -> None:
        """Test matching fails for different names."""
        id1 = ModelIdentifier(namespace="onex", name="compute")
        id2 = ModelIdentifier(namespace="onex", name="effect")
        assert not id1.matches(id2)


@pytest.mark.unit
class TestModelIdentifierValidation:
    """Tests for ModelIdentifier validation."""

    def test_validation_rejects_empty_namespace(self) -> None:
        """Test that empty namespace raises ValidationError (min_length=1)."""
        with pytest.raises(ValidationError) as exc_info:
            ModelIdentifier(namespace="", name="compute")
        assert "String should have at least 1 character" in str(exc_info.value)

    def test_validation_rejects_empty_name(self) -> None:
        """Test that empty name raises ValidationError (min_length=1)."""
        with pytest.raises(ValidationError) as exc_info:
            ModelIdentifier(namespace="onex", name="")
        assert "String should have at least 1 character" in str(exc_info.value)

    def test_validation_rejects_namespace_starting_with_number(self) -> None:
        """Test namespace must start with a letter."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelIdentifier(namespace="1vendor", name="compute")
        assert "must start with a letter" in str(exc_info.value)

    def test_validation_rejects_name_starting_with_number(self) -> None:
        """Test name must start with a letter."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelIdentifier(namespace="onex", name="1compute")
        assert "must start with a letter" in str(exc_info.value)

    def test_validation_rejects_namespace_with_special_chars(self) -> None:
        """Test namespace rejects special characters."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelIdentifier(namespace="onex$vendor", name="compute")
        assert "must start with a letter" in str(exc_info.value)

    def test_validation_rejects_empty_string_variant(self) -> None:
        """Test that empty string variant raises error."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelIdentifier(namespace="onex", name="compute", variant="")
        assert "Variant cannot be empty string" in str(exc_info.value)

    def test_validation_accepts_valid_characters(self) -> None:
        """Test valid identifiers with letters, numbers, underscores, hyphens."""
        identifier = ModelIdentifier(
            namespace="my_vendor-123", name="my_handler-456", variant="v2"
        )
        assert identifier.namespace == "my_vendor-123"
        assert identifier.name == "my_handler-456"
        assert identifier.variant == "v2"


@pytest.mark.unit
class TestModelIdentifierImmutability:
    """Tests for ModelIdentifier frozen immutability."""

    def test_frozen_immutability_namespace(self) -> None:
        """Test that namespace cannot be modified (frozen model)."""
        identifier = ModelIdentifier(namespace="onex", name="compute")
        with pytest.raises(ValidationError, match="frozen"):
            identifier.namespace = "modified"  # type: ignore[misc]

    def test_frozen_immutability_name(self) -> None:
        """Test that name cannot be modified (frozen model)."""
        identifier = ModelIdentifier(namespace="onex", name="compute")
        with pytest.raises(ValidationError, match="frozen"):
            identifier.name = "modified"  # type: ignore[misc]

    def test_frozen_immutability_variant(self) -> None:
        """Test that variant cannot be modified (frozen model)."""
        identifier = ModelIdentifier(namespace="onex", name="compute", variant="v1")
        with pytest.raises(ValidationError, match="frozen"):
            identifier.variant = "v2"  # type: ignore[misc]


@pytest.mark.unit
class TestModelIdentifierFactoryMethods:
    """Tests for ModelIdentifier factory methods."""

    def test_with_variant_creates_new_identifier(self) -> None:
        """Test with_variant creates a new identifier with variant."""
        base = ModelIdentifier(namespace="onex", name="compute")
        versioned = base.with_variant("v2")
        assert str(versioned) == "onex:compute@v2"
        assert base.variant is None  # Original unchanged

    def test_with_variant_replaces_existing_variant(self) -> None:
        """Test with_variant replaces existing variant."""
        original = ModelIdentifier(namespace="onex", name="compute", variant="v1")
        updated = original.with_variant("v2")
        assert updated.variant == "v2"
        assert original.variant == "v1"  # Original unchanged

    def test_with_version_creates_new_identifier(self) -> None:
        """Test with_version creates a new identifier with version."""
        base = ModelIdentifier(namespace="onex", name="compute")
        version = ModelSemVer(major=1, minor=0, patch=0)
        versioned = base.with_version(version)
        assert versioned.version == version
        assert base.version is None  # Original unchanged

    def test_with_version_preserves_variant(self) -> None:
        """Test with_version preserves existing variant."""
        original = ModelIdentifier(namespace="onex", name="compute", variant="v1")
        version = ModelSemVer(major=2, minor=0, patch=0)
        updated = original.with_version(version)
        assert updated.variant == "v1"
        assert updated.version == version


@pytest.mark.unit
class TestModelIdentifierExtraFieldsForbidden:
    """Tests for extra fields rejection."""

    def test_extra_fields_rejected(self) -> None:
        """Test that extra fields are rejected."""
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            ModelIdentifier(
                namespace="onex",
                name="compute",
                extra_field="should_fail",  # type: ignore[call-arg]
            )
