# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

#
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for ModelBinding."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from omnibase_core.models.bindings.model_binding import ModelBinding
from omnibase_core.models.errors.model_onex_error import ModelOnexError


@pytest.mark.unit
class TestModelBindingCreation:
    """Tests for ModelBinding creation and default values."""

    def test_create_with_all_required_fields(self) -> None:
        """Test creating ModelBinding with all required fields."""
        resolved_at = datetime.now(UTC)
        binding = ModelBinding(
            dependency_alias="db",
            capability="database.relational",
            resolved_provider="550e8400-e29b-41d4-a716-446655440000",
            adapter="omnibase.adapters.PostgresAdapter",
            connection_ref="secrets://postgres/primary",
            requirements_hash="sha256:abc123",
            resolution_profile="production",
            resolved_at=resolved_at,
        )
        assert binding.dependency_alias == "db"
        assert binding.capability == "database.relational"
        assert binding.resolved_provider == "550e8400-e29b-41d4-a716-446655440000"
        assert binding.adapter == "omnibase.adapters.PostgresAdapter"
        assert binding.connection_ref == "secrets://postgres/primary"
        assert binding.requirements_hash == "sha256:abc123"
        assert binding.resolution_profile == "production"
        assert binding.resolved_at == resolved_at

    def test_default_resolution_notes_is_empty_list(self) -> None:
        """Test that resolution_notes defaults to empty list."""
        binding = ModelBinding(
            dependency_alias="db",
            capability="database.relational",
            resolved_provider="test-id",
            adapter="test.Adapter",
            connection_ref="env://TEST",
            requirements_hash="hash123",
            resolution_profile="default",
            resolved_at=datetime.now(UTC),
        )
        assert binding.resolution_notes == []

    def test_default_candidates_considered_is_zero(self) -> None:
        """Test that candidates_considered defaults to 0."""
        binding = ModelBinding(
            dependency_alias="db",
            capability="database.relational",
            resolved_provider="test-id",
            adapter="test.Adapter",
            connection_ref="env://TEST",
            requirements_hash="hash123",
            resolution_profile="default",
            resolved_at=datetime.now(UTC),
        )
        assert binding.candidates_considered == 0

    def test_create_with_resolution_notes(self) -> None:
        """Test creating binding with resolution notes."""
        notes = [
            "Selected based on transaction support",
            "Matched region preference: us-east-1",
        ]
        binding = ModelBinding(
            dependency_alias="cache",
            capability="cache.distributed",
            resolved_provider="provider-123",
            adapter="omnibase.adapters.RedisAdapter",
            connection_ref="secrets://redis/primary",
            requirements_hash="sha256:def456",
            resolution_profile="production",
            resolved_at=datetime.now(UTC),
            resolution_notes=notes,
        )
        assert binding.resolution_notes == notes
        assert len(binding.resolution_notes) == 2

    def test_create_with_candidates_considered(self) -> None:
        """Test creating binding with candidates_considered."""
        binding = ModelBinding(
            dependency_alias="db",
            capability="database.relational",
            resolved_provider="test-id",
            adapter="test.Adapter",
            connection_ref="env://TEST",
            requirements_hash="hash123",
            resolution_profile="default",
            resolved_at=datetime.now(UTC),
            candidates_considered=5,
        )
        assert binding.candidates_considered == 5

    def test_create_with_all_fields(self) -> None:
        """Test creating binding with all fields including optional ones."""
        resolved_at = datetime.now(UTC)
        notes = ["Note 1", "Note 2", "Note 3"]
        binding = ModelBinding(
            dependency_alias="vectors",
            capability="storage.vector.qdrant",
            resolved_provider="qdrant-uuid-123",
            adapter="omnibase.adapters.QdrantAdapter",
            connection_ref="env://QDRANT_URL",
            requirements_hash="sha256:xyz789",
            resolution_profile="development",
            resolved_at=resolved_at,
            resolution_notes=notes,
            candidates_considered=3,
        )
        assert binding.dependency_alias == "vectors"
        assert binding.capability == "storage.vector.qdrant"
        assert binding.resolved_provider == "qdrant-uuid-123"
        assert binding.adapter == "omnibase.adapters.QdrantAdapter"
        assert binding.connection_ref == "env://QDRANT_URL"
        assert binding.requirements_hash == "sha256:xyz789"
        assert binding.resolution_profile == "development"
        assert binding.resolved_at == resolved_at
        assert binding.resolution_notes == notes
        assert binding.candidates_considered == 3


@pytest.mark.unit
class TestModelBindingDependencyAliasValidation:
    """Tests for dependency_alias field validation."""

    def test_valid_alias_simple(self) -> None:
        """Test valid simple alias."""
        binding = ModelBinding(
            dependency_alias="db",
            capability="database.relational",
            resolved_provider="test-id",
            adapter="test.Adapter",
            connection_ref="env://TEST",
            requirements_hash="hash123",
            resolution_profile="default",
            resolved_at=datetime.now(UTC),
        )
        assert binding.dependency_alias == "db"

    def test_valid_alias_with_underscore(self) -> None:
        """Test valid alias with underscores."""
        binding = ModelBinding(
            dependency_alias="my_database",
            capability="database.relational",
            resolved_provider="test-id",
            adapter="test.Adapter",
            connection_ref="env://TEST",
            requirements_hash="hash123",
            resolution_profile="default",
            resolved_at=datetime.now(UTC),
        )
        assert binding.dependency_alias == "my_database"

    def test_empty_alias_raises_validation_error(self) -> None:
        """Test that empty dependency_alias raises ValidationError."""
        with pytest.raises(ValidationError):
            ModelBinding(
                dependency_alias="",
                capability="database.relational",
                resolved_provider="test-id",
                adapter="test.Adapter",
                connection_ref="env://TEST",
                requirements_hash="hash123",
                resolution_profile="default",
                resolved_at=datetime.now(UTC),
            )

    def test_whitespace_only_alias_raises_error(self) -> None:
        """Test that whitespace-only dependency_alias raises ModelOnexError."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelBinding(
                dependency_alias="   ",
                capability="database.relational",
                resolved_provider="test-id",
                adapter="test.Adapter",
                connection_ref="env://TEST",
                requirements_hash="hash123",
                resolution_profile="default",
                resolved_at=datetime.now(UTC),
            )
        assert "cannot be empty or whitespace-only" in str(exc_info.value)

    def test_alias_with_leading_whitespace_is_stripped(self) -> None:
        """Test that alias with leading/trailing whitespace is stripped."""
        binding = ModelBinding(
            dependency_alias="  db  ",
            capability="database.relational",
            resolved_provider="test-id",
            adapter="test.Adapter",
            connection_ref="env://TEST",
            requirements_hash="hash123",
            resolution_profile="default",
            resolved_at=datetime.now(UTC),
        )
        assert binding.dependency_alias == "db"

    def test_alias_max_length_accepted(self) -> None:
        """Test that alias at max length (64 chars) is accepted."""
        long_alias = "a" * 64
        binding = ModelBinding(
            dependency_alias=long_alias,
            capability="database.relational",
            resolved_provider="test-id",
            adapter="test.Adapter",
            connection_ref="env://TEST",
            requirements_hash="hash123",
            resolution_profile="default",
            resolved_at=datetime.now(UTC),
        )
        assert binding.dependency_alias == long_alias

    def test_alias_exceeds_max_length_raises_error(self) -> None:
        """Test that alias exceeding max length (64 chars) raises error."""
        too_long_alias = "a" * 65
        with pytest.raises(ValidationError):
            ModelBinding(
                dependency_alias=too_long_alias,
                capability="database.relational",
                resolved_provider="test-id",
                adapter="test.Adapter",
                connection_ref="env://TEST",
                requirements_hash="hash123",
                resolution_profile="default",
                resolved_at=datetime.now(UTC),
            )


@pytest.mark.unit
class TestModelBindingCapabilityValidation:
    """Tests for capability field validation."""

    def test_valid_capability_two_tokens(self) -> None:
        """Test valid capability with two tokens."""
        binding = ModelBinding(
            dependency_alias="db",
            capability="database.relational",
            resolved_provider="test-id",
            adapter="test.Adapter",
            connection_ref="env://TEST",
            requirements_hash="hash123",
            resolution_profile="default",
            resolved_at=datetime.now(UTC),
        )
        assert binding.capability == "database.relational"

    def test_valid_capability_three_tokens(self) -> None:
        """Test valid capability with three tokens."""
        binding = ModelBinding(
            dependency_alias="cache",
            capability="cache.kv.redis",
            resolved_provider="test-id",
            adapter="test.Adapter",
            connection_ref="env://TEST",
            requirements_hash="hash123",
            resolution_profile="default",
            resolved_at=datetime.now(UTC),
        )
        assert binding.capability == "cache.kv.redis"

    def test_empty_capability_raises_validation_error(self) -> None:
        """Test that empty capability raises ValidationError."""
        with pytest.raises(ValidationError):
            ModelBinding(
                dependency_alias="db",
                capability="",
                resolved_provider="test-id",
                adapter="test.Adapter",
                connection_ref="env://TEST",
                requirements_hash="hash123",
                resolution_profile="default",
                resolved_at=datetime.now(UTC),
            )

    def test_whitespace_only_capability_raises_error(self) -> None:
        """Test that whitespace-only capability raises ModelOnexError."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelBinding(
                dependency_alias="db",
                capability="    ",
                resolved_provider="test-id",
                adapter="test.Adapter",
                connection_ref="env://TEST",
                requirements_hash="hash123",
                resolution_profile="default",
                resolved_at=datetime.now(UTC),
            )
        assert "cannot be empty or whitespace-only" in str(exc_info.value)

    def test_capability_with_whitespace_is_stripped(self) -> None:
        """Test that capability with whitespace is stripped."""
        binding = ModelBinding(
            dependency_alias="db",
            capability="  database.relational  ",
            resolved_provider="test-id",
            adapter="test.Adapter",
            connection_ref="env://TEST",
            requirements_hash="hash123",
            resolution_profile="default",
            resolved_at=datetime.now(UTC),
        )
        assert binding.capability == "database.relational"

    def test_capability_min_length_enforced(self) -> None:
        """Test that capability must be at least 3 characters."""
        with pytest.raises(ValidationError):
            ModelBinding(
                dependency_alias="db",
                capability="ab",  # Only 2 chars
                resolved_provider="test-id",
                adapter="test.Adapter",
                connection_ref="env://TEST",
                requirements_hash="hash123",
                resolution_profile="default",
                resolved_at=datetime.now(UTC),
            )

    def test_capability_max_length_accepted(self) -> None:
        """Test that capability at max length (128 chars) is accepted."""
        long_capability = "a.b" + "c" * 125  # 128 chars total
        binding = ModelBinding(
            dependency_alias="db",
            capability=long_capability,
            resolved_provider="test-id",
            adapter="test.Adapter",
            connection_ref="env://TEST",
            requirements_hash="hash123",
            resolution_profile="default",
            resolved_at=datetime.now(UTC),
        )
        assert binding.capability == long_capability


@pytest.mark.unit
class TestModelBindingProviderIdValidation:
    """Tests for resolved_provider field validation."""

    def test_valid_resolved_provider_uuid(self) -> None:
        """Test valid UUID-format resolved_provider."""
        binding = ModelBinding(
            dependency_alias="db",
            capability="database.relational",
            resolved_provider="550e8400-e29b-41d4-a716-446655440000",
            adapter="test.Adapter",
            connection_ref="env://TEST",
            requirements_hash="hash123",
            resolution_profile="default",
            resolved_at=datetime.now(UTC),
        )
        assert binding.resolved_provider == "550e8400-e29b-41d4-a716-446655440000"

    def test_valid_resolved_provider_non_uuid(self) -> None:
        """Test that non-UUID resolved_provider is accepted (flexible format)."""
        binding = ModelBinding(
            dependency_alias="db",
            capability="database.relational",
            resolved_provider="custom-provider-id-123",
            adapter="test.Adapter",
            connection_ref="env://TEST",
            requirements_hash="hash123",
            resolution_profile="default",
            resolved_at=datetime.now(UTC),
        )
        assert binding.resolved_provider == "custom-provider-id-123"

    def test_empty_resolved_provider_raises_validation_error(self) -> None:
        """Test that empty resolved_provider raises ValidationError."""
        with pytest.raises(ValidationError):
            ModelBinding(
                dependency_alias="db",
                capability="database.relational",
                resolved_provider="",
                adapter="test.Adapter",
                connection_ref="env://TEST",
                requirements_hash="hash123",
                resolution_profile="default",
                resolved_at=datetime.now(UTC),
            )

    def test_whitespace_only_resolved_provider_raises_error(self) -> None:
        """Test that whitespace-only resolved_provider raises ModelOnexError."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelBinding(
                dependency_alias="db",
                capability="database.relational",
                resolved_provider="   ",
                adapter="test.Adapter",
                connection_ref="env://TEST",
                requirements_hash="hash123",
                resolution_profile="default",
                resolved_at=datetime.now(UTC),
            )
        assert "cannot be empty or whitespace-only" in str(exc_info.value)

    def test_resolved_provider_with_whitespace_is_stripped(self) -> None:
        """Test that resolved_provider with whitespace is stripped."""
        binding = ModelBinding(
            dependency_alias="db",
            capability="database.relational",
            resolved_provider="  provider-123  ",
            adapter="test.Adapter",
            connection_ref="env://TEST",
            requirements_hash="hash123",
            resolution_profile="default",
            resolved_at=datetime.now(UTC),
        )
        assert binding.resolved_provider == "provider-123"


@pytest.mark.unit
class TestModelBindingAdapterValidation:
    """Tests for adapter field validation."""

    def test_valid_adapter_import_path(self) -> None:
        """Test valid Python import path for adapter."""
        binding = ModelBinding(
            dependency_alias="db",
            capability="database.relational",
            resolved_provider="test-id",
            adapter="omnibase_infra.adapters.PostgresAdapter",
            connection_ref="env://TEST",
            requirements_hash="hash123",
            resolution_profile="default",
            resolved_at=datetime.now(UTC),
        )
        assert binding.adapter == "omnibase_infra.adapters.PostgresAdapter"

    def test_empty_adapter_raises_validation_error(self) -> None:
        """Test that empty adapter raises ValidationError."""
        with pytest.raises(ValidationError):
            ModelBinding(
                dependency_alias="db",
                capability="database.relational",
                resolved_provider="test-id",
                adapter="",
                connection_ref="env://TEST",
                requirements_hash="hash123",
                resolution_profile="default",
                resolved_at=datetime.now(UTC),
            )

    def test_whitespace_only_adapter_raises_error(self) -> None:
        """Test that whitespace-only adapter raises ModelOnexError."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelBinding(
                dependency_alias="db",
                capability="database.relational",
                resolved_provider="test-id",
                adapter="   ",
                connection_ref="env://TEST",
                requirements_hash="hash123",
                resolution_profile="default",
                resolved_at=datetime.now(UTC),
            )
        assert "cannot be empty or whitespace-only" in str(exc_info.value)

    def test_adapter_with_whitespace_is_stripped(self) -> None:
        """Test that adapter with whitespace is stripped."""
        binding = ModelBinding(
            dependency_alias="db",
            capability="database.relational",
            resolved_provider="test-id",
            adapter="  my.Adapter  ",
            connection_ref="env://TEST",
            requirements_hash="hash123",
            resolution_profile="default",
            resolved_at=datetime.now(UTC),
        )
        assert binding.adapter == "my.Adapter"


@pytest.mark.unit
class TestModelBindingConnectionRefValidation:
    """Tests for connection_ref field validation."""

    def test_valid_secrets_ref(self) -> None:
        """Test valid secrets:// connection reference."""
        binding = ModelBinding(
            dependency_alias="db",
            capability="database.relational",
            resolved_provider="test-id",
            adapter="test.Adapter",
            connection_ref="secrets://postgres/primary",
            requirements_hash="hash123",
            resolution_profile="default",
            resolved_at=datetime.now(UTC),
        )
        assert binding.connection_ref == "secrets://postgres/primary"

    def test_valid_env_ref(self) -> None:
        """Test valid env:// connection reference."""
        binding = ModelBinding(
            dependency_alias="db",
            capability="database.relational",
            resolved_provider="test-id",
            adapter="test.Adapter",
            connection_ref="env://DATABASE_URL",
            requirements_hash="hash123",
            resolution_profile="default",
            resolved_at=datetime.now(UTC),
        )
        assert binding.connection_ref == "env://DATABASE_URL"

    def test_empty_connection_ref_raises_validation_error(self) -> None:
        """Test that empty connection_ref raises ValidationError."""
        with pytest.raises(ValidationError):
            ModelBinding(
                dependency_alias="db",
                capability="database.relational",
                resolved_provider="test-id",
                adapter="test.Adapter",
                connection_ref="",
                requirements_hash="hash123",
                resolution_profile="default",
                resolved_at=datetime.now(UTC),
            )

    def test_whitespace_only_connection_ref_raises_error(self) -> None:
        """Test that whitespace-only connection_ref raises ModelOnexError."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelBinding(
                dependency_alias="db",
                capability="database.relational",
                resolved_provider="test-id",
                adapter="test.Adapter",
                connection_ref="   ",
                requirements_hash="hash123",
                resolution_profile="default",
                resolved_at=datetime.now(UTC),
            )
        assert "cannot be empty or whitespace-only" in str(exc_info.value)


@pytest.mark.unit
class TestModelBindingRequirementsHashValidation:
    """Tests for requirements_hash field validation."""

    def test_valid_requirements_hash(self) -> None:
        """Test valid requirements hash."""
        binding = ModelBinding(
            dependency_alias="db",
            capability="database.relational",
            resolved_provider="test-id",
            adapter="test.Adapter",
            connection_ref="env://TEST",
            requirements_hash="sha256:abc123def456",
            resolution_profile="default",
            resolved_at=datetime.now(UTC),
        )
        assert binding.requirements_hash == "sha256:abc123def456"

    def test_empty_requirements_hash_raises_validation_error(self) -> None:
        """Test that empty requirements_hash raises ValidationError."""
        with pytest.raises(ValidationError):
            ModelBinding(
                dependency_alias="db",
                capability="database.relational",
                resolved_provider="test-id",
                adapter="test.Adapter",
                connection_ref="env://TEST",
                requirements_hash="",
                resolution_profile="default",
                resolved_at=datetime.now(UTC),
            )

    def test_whitespace_only_requirements_hash_raises_error(self) -> None:
        """Test that whitespace-only requirements_hash raises ModelOnexError."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelBinding(
                dependency_alias="db",
                capability="database.relational",
                resolved_provider="test-id",
                adapter="test.Adapter",
                connection_ref="env://TEST",
                requirements_hash="   ",
                resolution_profile="default",
                resolved_at=datetime.now(UTC),
            )
        assert "cannot be empty or whitespace-only" in str(exc_info.value)


@pytest.mark.unit
class TestModelBindingProfileIdValidation:
    """Tests for resolution_profile field validation."""

    def test_valid_resolution_profile(self) -> None:
        """Test valid resolution_profile."""
        binding = ModelBinding(
            dependency_alias="db",
            capability="database.relational",
            resolved_provider="test-id",
            adapter="test.Adapter",
            connection_ref="env://TEST",
            requirements_hash="hash123",
            resolution_profile="production",
            resolved_at=datetime.now(UTC),
        )
        assert binding.resolution_profile == "production"

    def test_empty_resolution_profile_raises_validation_error(self) -> None:
        """Test that empty resolution_profile raises ValidationError."""
        with pytest.raises(ValidationError):
            ModelBinding(
                dependency_alias="db",
                capability="database.relational",
                resolved_provider="test-id",
                adapter="test.Adapter",
                connection_ref="env://TEST",
                requirements_hash="hash123",
                resolution_profile="",
                resolved_at=datetime.now(UTC),
            )

    def test_whitespace_only_resolution_profile_raises_error(self) -> None:
        """Test that whitespace-only resolution_profile raises ModelOnexError."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelBinding(
                dependency_alias="db",
                capability="database.relational",
                resolved_provider="test-id",
                adapter="test.Adapter",
                connection_ref="env://TEST",
                requirements_hash="hash123",
                resolution_profile="   ",
                resolved_at=datetime.now(UTC),
            )
        assert "cannot be empty or whitespace-only" in str(exc_info.value)


@pytest.mark.unit
class TestModelBindingResolutionNotesValidation:
    """Tests for resolution_notes field validation."""

    def test_resolution_notes_strips_whitespace(self) -> None:
        """Test that whitespace is stripped from notes."""
        binding = ModelBinding(
            dependency_alias="db",
            capability="database.relational",
            resolved_provider="test-id",
            adapter="test.Adapter",
            connection_ref="env://TEST",
            requirements_hash="hash123",
            resolution_profile="default",
            resolved_at=datetime.now(UTC),
            resolution_notes=["  Note with whitespace  ", "  Another note  "],
        )
        assert binding.resolution_notes == [
            "Note with whitespace",
            "Another note",
        ]

    def test_resolution_notes_filters_empty_notes(self) -> None:
        """Test that empty notes are filtered out."""
        binding = ModelBinding(
            dependency_alias="db",
            capability="database.relational",
            resolved_provider="test-id",
            adapter="test.Adapter",
            connection_ref="env://TEST",
            requirements_hash="hash123",
            resolution_profile="default",
            resolved_at=datetime.now(UTC),
            resolution_notes=["Note 1", "", "   ", "Note 2"],
        )
        assert binding.resolution_notes == ["Note 1", "Note 2"]

    def test_resolution_notes_rejects_non_string(self) -> None:
        """Test that non-string notes raise ModelOnexError."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelBinding(
                dependency_alias="db",
                capability="database.relational",
                resolved_provider="test-id",
                adapter="test.Adapter",
                connection_ref="env://TEST",
                requirements_hash="hash123",
                resolution_profile="default",
                resolved_at=datetime.now(UTC),
                resolution_notes=["Valid note", 123],  # type: ignore[list-item]
            )
        assert "must be a string" in str(exc_info.value)

    def test_resolution_notes_multiple_entries(self) -> None:
        """Test resolution notes with many entries."""
        notes = [f"Note {i}" for i in range(10)]
        binding = ModelBinding(
            dependency_alias="db",
            capability="database.relational",
            resolved_provider="test-id",
            adapter="test.Adapter",
            connection_ref="env://TEST",
            requirements_hash="hash123",
            resolution_profile="default",
            resolved_at=datetime.now(UTC),
            resolution_notes=notes,
        )
        assert len(binding.resolution_notes) == 10
        assert binding.resolution_notes == notes


@pytest.mark.unit
class TestModelBindingCandidatesConsideredValidation:
    """Tests for candidates_considered field validation."""

    def test_candidates_considered_zero_valid(self) -> None:
        """Test that candidates_considered=0 is valid."""
        binding = ModelBinding(
            dependency_alias="db",
            capability="database.relational",
            resolved_provider="test-id",
            adapter="test.Adapter",
            connection_ref="env://TEST",
            requirements_hash="hash123",
            resolution_profile="default",
            resolved_at=datetime.now(UTC),
            candidates_considered=0,
        )
        assert binding.candidates_considered == 0

    def test_candidates_considered_positive_valid(self) -> None:
        """Test that positive candidates_considered is valid."""
        binding = ModelBinding(
            dependency_alias="db",
            capability="database.relational",
            resolved_provider="test-id",
            adapter="test.Adapter",
            connection_ref="env://TEST",
            requirements_hash="hash123",
            resolution_profile="default",
            resolved_at=datetime.now(UTC),
            candidates_considered=100,
        )
        assert binding.candidates_considered == 100

    def test_candidates_considered_negative_raises_error(self) -> None:
        """Test that negative candidates_considered raises ValidationError."""
        with pytest.raises(ValidationError):
            ModelBinding(
                dependency_alias="db",
                capability="database.relational",
                resolved_provider="test-id",
                adapter="test.Adapter",
                connection_ref="env://TEST",
                requirements_hash="hash123",
                resolution_profile="default",
                resolved_at=datetime.now(UTC),
                candidates_considered=-1,
            )

    def test_candidates_considered_large_value(self) -> None:
        """Test that large candidates_considered values are accepted."""
        binding = ModelBinding(
            dependency_alias="db",
            capability="database.relational",
            resolved_provider="test-id",
            adapter="test.Adapter",
            connection_ref="env://TEST",
            requirements_hash="hash123",
            resolution_profile="default",
            resolved_at=datetime.now(UTC),
            candidates_considered=1000000,
        )
        assert binding.candidates_considered == 1000000


@pytest.mark.unit
class TestModelBindingImmutability:
    """Tests for ModelBinding frozen immutability."""

    def test_frozen_immutability_dependency_alias(self) -> None:
        """Test that dependency_alias cannot be modified."""
        binding = ModelBinding(
            dependency_alias="db",
            capability="database.relational",
            resolved_provider="test-id",
            adapter="test.Adapter",
            connection_ref="env://TEST",
            requirements_hash="hash123",
            resolution_profile="default",
            resolved_at=datetime.now(UTC),
        )
        with pytest.raises(ValidationError, match="frozen"):
            binding.dependency_alias = "modified"  # type: ignore[misc]

    def test_frozen_immutability_capability(self) -> None:
        """Test that capability cannot be modified."""
        binding = ModelBinding(
            dependency_alias="db",
            capability="database.relational",
            resolved_provider="test-id",
            adapter="test.Adapter",
            connection_ref="env://TEST",
            requirements_hash="hash123",
            resolution_profile="default",
            resolved_at=datetime.now(UTC),
        )
        with pytest.raises(ValidationError, match="frozen"):
            binding.capability = "cache.kv"  # type: ignore[misc]

    def test_frozen_immutability_resolved_provider(self) -> None:
        """Test that resolved_provider cannot be modified."""
        binding = ModelBinding(
            dependency_alias="db",
            capability="database.relational",
            resolved_provider="test-id",
            adapter="test.Adapter",
            connection_ref="env://TEST",
            requirements_hash="hash123",
            resolution_profile="default",
            resolved_at=datetime.now(UTC),
        )
        with pytest.raises(ValidationError, match="frozen"):
            binding.resolved_provider = "modified"  # type: ignore[misc]

    def test_frozen_immutability_adapter(self) -> None:
        """Test that adapter cannot be modified."""
        binding = ModelBinding(
            dependency_alias="db",
            capability="database.relational",
            resolved_provider="test-id",
            adapter="test.Adapter",
            connection_ref="env://TEST",
            requirements_hash="hash123",
            resolution_profile="default",
            resolved_at=datetime.now(UTC),
        )
        with pytest.raises(ValidationError, match="frozen"):
            binding.adapter = "other.Adapter"  # type: ignore[misc]

    def test_frozen_immutability_resolution_notes(self) -> None:
        """Test that resolution_notes cannot be reassigned."""
        binding = ModelBinding(
            dependency_alias="db",
            capability="database.relational",
            resolved_provider="test-id",
            adapter="test.Adapter",
            connection_ref="env://TEST",
            requirements_hash="hash123",
            resolution_profile="default",
            resolved_at=datetime.now(UTC),
            resolution_notes=["Original note"],
        )
        with pytest.raises(ValidationError, match="frozen"):
            binding.resolution_notes = ["Modified"]  # type: ignore[misc]

    def test_frozen_immutability_candidates_considered(self) -> None:
        """Test that candidates_considered cannot be modified."""
        binding = ModelBinding(
            dependency_alias="db",
            capability="database.relational",
            resolved_provider="test-id",
            adapter="test.Adapter",
            connection_ref="env://TEST",
            requirements_hash="hash123",
            resolution_profile="default",
            resolved_at=datetime.now(UTC),
            candidates_considered=5,
        )
        with pytest.raises(ValidationError, match="frozen"):
            binding.candidates_considered = 10  # type: ignore[misc]


@pytest.mark.unit
class TestModelBindingExtraFields:
    """Tests for extra fields rejection."""

    def test_extra_fields_rejected(self) -> None:
        """Test that extra fields are rejected."""
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            ModelBinding(
                dependency_alias="db",
                capability="database.relational",
                resolved_provider="test-id",
                adapter="test.Adapter",
                connection_ref="env://TEST",
                requirements_hash="hash123",
                resolution_profile="default",
                resolved_at=datetime.now(UTC),
                extra_field="should_fail",  # type: ignore[call-arg]
            )


@pytest.mark.unit
class TestModelBindingHashability:
    """Tests for ModelBinding hashability.

    ModelBinding implements __hash__ based on identity fields
    (dependency_alias, capability, resolved_provider). Metadata fields
    (resolved_at, resolution_notes, candidates_considered) are
    not included in hash computation for deduplication purposes.
    """

    def test_hashable_can_use_in_set(self) -> None:
        """Test that bindings can be added to sets."""
        # Use fixed timestamp so binding1 and binding2 have identical values
        fixed_timestamp = datetime.now(UTC)

        binding1 = ModelBinding(
            dependency_alias="db",
            capability="database.relational",
            resolved_provider="provider-1",
            adapter="test.Adapter",
            connection_ref="env://TEST",
            requirements_hash="hash123",
            resolution_profile="default",
            resolved_at=fixed_timestamp,
        )
        binding2 = ModelBinding(
            dependency_alias="db",
            capability="database.relational",
            resolved_provider="provider-1",
            adapter="test.Adapter",
            connection_ref="env://TEST",
            requirements_hash="hash123",
            resolution_profile="default",
            resolved_at=fixed_timestamp,
        )
        binding3 = ModelBinding(
            dependency_alias="cache",
            capability="cache.redis",
            resolved_provider="provider-2",
            adapter="test.Adapter",
            connection_ref="env://TEST",
            requirements_hash="hash456",
            resolution_profile="default",
            resolved_at=fixed_timestamp,
        )

        bindings = {binding1, binding2, binding3}
        # binding1 and binding2 have same identity fields
        assert len(bindings) == 2

    def test_hashable_can_use_as_dict_key(self) -> None:
        """Test that bindings can be used as dict keys."""
        binding = ModelBinding(
            dependency_alias="db",
            capability="database.relational",
            resolved_provider="provider-1",
            adapter="test.Adapter",
            connection_ref="env://TEST",
            requirements_hash="hash123",
            resolution_profile="default",
            resolved_at=datetime.now(UTC),
        )
        cache: dict[ModelBinding, str] = {binding: "cached_value"}
        assert cache[binding] == "cached_value"

    def test_hash_stability_same_object(self) -> None:
        """Test that hash is stable for the same object."""
        binding = ModelBinding(
            dependency_alias="db",
            capability="database.relational",
            resolved_provider="provider-1",
            adapter="test.Adapter",
            connection_ref="env://TEST",
            requirements_hash="hash123",
            resolution_profile="default",
            resolved_at=datetime.now(UTC),
        )
        h1 = hash(binding)
        h2 = hash(binding)
        assert h1 == h2

    def test_hash_consistency_equal_identity_fields(self) -> None:
        """Test that bindings with same identity fields have same hash."""
        resolved_at = datetime.now(UTC)
        binding1 = ModelBinding(
            dependency_alias="db",
            capability="database.relational",
            resolved_provider="provider-1",
            adapter="test.Adapter",
            connection_ref="env://TEST",
            requirements_hash="hash123",
            resolution_profile="default",
            resolved_at=resolved_at,
        )
        binding2 = ModelBinding(
            dependency_alias="db",
            capability="database.relational",
            resolved_provider="provider-1",
            adapter="test.Adapter",
            connection_ref="env://TEST",
            requirements_hash="hash123",
            resolution_profile="default",
            resolved_at=resolved_at,
        )
        assert hash(binding1) == hash(binding2)

    def test_hash_differs_for_different_alias(self) -> None:
        """Test that hash differs when dependency_alias differs."""
        resolved_at = datetime.now(UTC)
        binding1 = ModelBinding(
            dependency_alias="db",
            capability="database.relational",
            resolved_provider="provider-1",
            adapter="test.Adapter",
            connection_ref="env://TEST",
            requirements_hash="hash123",
            resolution_profile="default",
            resolved_at=resolved_at,
        )
        binding2 = ModelBinding(
            dependency_alias="other_db",
            capability="database.relational",
            resolved_provider="provider-1",
            adapter="test.Adapter",
            connection_ref="env://TEST",
            requirements_hash="hash123",
            resolution_profile="default",
            resolved_at=resolved_at,
        )
        assert hash(binding1) != hash(binding2)

    def test_hash_differs_for_different_capability(self) -> None:
        """Test that hash differs when capability differs."""
        resolved_at = datetime.now(UTC)
        binding1 = ModelBinding(
            dependency_alias="db",
            capability="database.relational",
            resolved_provider="provider-1",
            adapter="test.Adapter",
            connection_ref="env://TEST",
            requirements_hash="hash123",
            resolution_profile="default",
            resolved_at=resolved_at,
        )
        binding2 = ModelBinding(
            dependency_alias="db",
            capability="database.document",
            resolved_provider="provider-1",
            adapter="test.Adapter",
            connection_ref="env://TEST",
            requirements_hash="hash123",
            resolution_profile="default",
            resolved_at=resolved_at,
        )
        assert hash(binding1) != hash(binding2)

    def test_hash_differs_for_different_resolved_provider(self) -> None:
        """Test that hash differs when resolved_provider differs."""
        resolved_at = datetime.now(UTC)
        binding1 = ModelBinding(
            dependency_alias="db",
            capability="database.relational",
            resolved_provider="provider-1",
            adapter="test.Adapter",
            connection_ref="env://TEST",
            requirements_hash="hash123",
            resolution_profile="default",
            resolved_at=resolved_at,
        )
        binding2 = ModelBinding(
            dependency_alias="db",
            capability="database.relational",
            resolved_provider="provider-2",
            adapter="test.Adapter",
            connection_ref="env://TEST",
            requirements_hash="hash123",
            resolution_profile="default",
            resolved_at=resolved_at,
        )
        assert hash(binding1) != hash(binding2)

    def test_hash_same_for_different_metadata(self) -> None:
        """Test that hash is same for bindings with different metadata.

        This is intentional: bindings are deduplicated by identity
        (dependency_alias, capability, resolved_provider), not by metadata
        (resolved_at, resolution_notes, candidates_considered).
        """
        binding1 = ModelBinding(
            dependency_alias="db",
            capability="database.relational",
            resolved_provider="provider-1",
            adapter="test.Adapter",
            connection_ref="env://TEST",
            requirements_hash="hash123",
            resolution_profile="default",
            resolved_at=datetime(2024, 1, 1, tzinfo=UTC),
            resolution_notes=["Note 1"],
            candidates_considered=5,
        )
        binding2 = ModelBinding(
            dependency_alias="db",
            capability="database.relational",
            resolved_provider="provider-1",
            adapter="test.Adapter",
            connection_ref="env://TEST",
            requirements_hash="hash123",
            resolution_profile="default",
            resolved_at=datetime(2025, 6, 15, tzinfo=UTC),
            resolution_notes=["Different note"],
            candidates_considered=10,
        )
        # Same identity fields -> same hash
        assert hash(binding1) == hash(binding2)

    def test_hash_equality_contract_satisfied(self) -> None:
        """Test that hash/equality contract is satisfied.

        Python's hash/equality contract requires:
        - If a == b, then hash(a) == hash(b)
        - If hash(a) == hash(b), objects SHOULD be equal (for good hash behavior)

        Our implementation ensures bindings with same identity fields are
        both hash-equal AND equality-equal, satisfying the contract.
        """
        # Two bindings with same identity but different metadata
        binding1 = ModelBinding(
            dependency_alias="db",
            capability="database.relational",
            resolved_provider="provider-1",
            adapter="test.Adapter",
            connection_ref="env://TEST",
            requirements_hash="hash123",
            resolution_profile="default",
            resolved_at=datetime(2024, 1, 1, tzinfo=UTC),
            resolution_notes=["Note 1"],
            candidates_considered=5,
        )
        binding2 = ModelBinding(
            dependency_alias="db",
            capability="database.relational",
            resolved_provider="provider-1",
            adapter="test.Adapter",
            connection_ref="env://TEST",
            requirements_hash="hash456",  # Different metadata
            resolution_profile="production",  # Different metadata
            resolved_at=datetime(2025, 6, 15, tzinfo=UTC),  # Different metadata
            resolution_notes=["Different note"],  # Different metadata
            candidates_considered=10,  # Different metadata
        )

        # Contract: same hash AND same equality for same identity
        assert hash(binding1) == hash(binding2), (
            "Bindings with same identity should have same hash"
        )
        assert binding1 == binding2, "Bindings with same identity should be equal"


@pytest.mark.unit
class TestModelBindingEquality:
    """Tests for ModelBinding equality."""

    def test_equality_same_bindings(self) -> None:
        """Test equality for identical bindings."""
        resolved_at = datetime.now(UTC)
        binding1 = ModelBinding(
            dependency_alias="db",
            capability="database.relational",
            resolved_provider="provider-1",
            adapter="test.Adapter",
            connection_ref="env://TEST",
            requirements_hash="hash123",
            resolution_profile="default",
            resolved_at=resolved_at,
        )
        binding2 = ModelBinding(
            dependency_alias="db",
            capability="database.relational",
            resolved_provider="provider-1",
            adapter="test.Adapter",
            connection_ref="env://TEST",
            requirements_hash="hash123",
            resolution_profile="default",
            resolved_at=resolved_at,
        )
        assert binding1 == binding2

    def test_inequality_different_alias(self) -> None:
        """Test inequality for different aliases."""
        resolved_at = datetime.now(UTC)
        binding1 = ModelBinding(
            dependency_alias="db",
            capability="database.relational",
            resolved_provider="provider-1",
            adapter="test.Adapter",
            connection_ref="env://TEST",
            requirements_hash="hash123",
            resolution_profile="default",
            resolved_at=resolved_at,
        )
        binding2 = ModelBinding(
            dependency_alias="database",
            capability="database.relational",
            resolved_provider="provider-1",
            adapter="test.Adapter",
            connection_ref="env://TEST",
            requirements_hash="hash123",
            resolution_profile="default",
            resolved_at=resolved_at,
        )
        assert binding1 != binding2

    def test_inequality_different_capability(self) -> None:
        """Test inequality for different capabilities."""
        resolved_at = datetime.now(UTC)
        binding1 = ModelBinding(
            dependency_alias="db",
            capability="database.relational",
            resolved_provider="provider-1",
            adapter="test.Adapter",
            connection_ref="env://TEST",
            requirements_hash="hash123",
            resolution_profile="default",
            resolved_at=resolved_at,
        )
        binding2 = ModelBinding(
            dependency_alias="db",
            capability="database.document",
            resolved_provider="provider-1",
            adapter="test.Adapter",
            connection_ref="env://TEST",
            requirements_hash="hash123",
            resolution_profile="default",
            resolved_at=resolved_at,
        )
        assert binding1 != binding2

    def test_inequality_different_resolved_provider(self) -> None:
        """Test inequality for different resolved_providers."""
        resolved_at = datetime.now(UTC)
        binding1 = ModelBinding(
            dependency_alias="db",
            capability="database.relational",
            resolved_provider="provider-1",
            adapter="test.Adapter",
            connection_ref="env://TEST",
            requirements_hash="hash123",
            resolution_profile="default",
            resolved_at=resolved_at,
        )
        binding2 = ModelBinding(
            dependency_alias="db",
            capability="database.relational",
            resolved_provider="provider-2",
            adapter="test.Adapter",
            connection_ref="env://TEST",
            requirements_hash="hash123",
            resolution_profile="default",
            resolved_at=resolved_at,
        )
        assert binding1 != binding2

    def test_equality_same_identity_different_metadata(self) -> None:
        """Test equality for same identity fields but different metadata.

        Custom __eq__ compares only identity fields (dependency_alias,
        capability, resolved_provider), so bindings with same identity are
        equal even if metadata differs.
        """
        binding1 = ModelBinding(
            dependency_alias="db",
            capability="database.relational",
            resolved_provider="provider-1",
            adapter="test.Adapter",
            connection_ref="env://TEST",
            requirements_hash="hash123",
            resolution_profile="default",
            resolved_at=datetime(2024, 1, 1, tzinfo=UTC),
            resolution_notes=["Note 1"],
            candidates_considered=5,
        )
        binding2 = ModelBinding(
            dependency_alias="db",
            capability="database.relational",
            resolved_provider="provider-1",
            adapter="test.Adapter",
            connection_ref="env://TEST",
            requirements_hash="hash456",  # Different metadata
            resolution_profile="production",  # Different metadata
            resolved_at=datetime(2025, 1, 1, tzinfo=UTC),  # Different metadata
            resolution_notes=["Different note"],  # Different metadata
            candidates_considered=10,  # Different metadata
        )
        # Custom equality uses only identity fields
        assert binding1 == binding2


@pytest.mark.unit
class TestModelBindingStringRepresentation:
    """Tests for string representation."""

    def test_str_returns_arrow_format(self) -> None:
        """Test __str__ returns 'alias -> capability @ resolved_provider' format."""
        binding = ModelBinding(
            dependency_alias="db",
            capability="database.relational",
            resolved_provider="550e8400",
            adapter="test.Adapter",
            connection_ref="env://TEST",
            requirements_hash="hash123",
            resolution_profile="default",
            resolved_at=datetime.now(UTC),
        )
        assert str(binding) == "db -> database.relational @ 550e8400"

    def test_repr_contains_essential_info(self) -> None:
        """Test __repr__ contains alias, capability, and resolved_provider."""
        binding = ModelBinding(
            dependency_alias="db",
            capability="database.relational",
            resolved_provider="550e8400-e29b-41d4-a716-446655440000",
            adapter="test.Adapter",
            connection_ref="env://TEST",
            requirements_hash="hash123",
            resolution_profile="default",
            resolved_at=datetime.now(UTC),
        )
        repr_str = repr(binding)
        assert "ModelBinding" in repr_str
        assert "db" in repr_str
        assert "database.relational" in repr_str
        assert "550e8400-e29b-41d4-a716-446655440000" in repr_str


@pytest.mark.unit
class TestModelBindingFromAttributes:
    """Tests for from_attributes configuration."""

    def test_from_attributes_allows_object_construction(self) -> None:
        """Test that from_attributes=True allows construction from objects."""

        class MockBinding:
            dependency_alias = "db"
            capability = "database.relational"
            resolved_provider = "provider-123"
            adapter = "test.Adapter"
            connection_ref = "env://TEST"
            requirements_hash = "hash123"
            resolution_profile = "default"
            resolved_at = datetime.now(UTC)
            resolution_notes: list[str] = []
            candidates_considered = 0

        # This should work due to from_attributes=True
        binding = ModelBinding.model_validate(MockBinding())
        assert binding.dependency_alias == "db"
        assert binding.capability == "database.relational"
        assert binding.resolved_provider == "provider-123"


@pytest.mark.unit
class TestModelBindingEdgeCases:
    """Tests for edge cases and special characters."""

    def test_special_characters_in_connection_ref(self) -> None:
        """Test special characters in connection_ref."""
        binding = ModelBinding(
            dependency_alias="db",
            capability="database.relational",
            resolved_provider="test-id",
            adapter="test.Adapter",
            connection_ref="secrets://my-vault/postgres@primary?ssl=true&timeout=30",
            requirements_hash="hash123",
            resolution_profile="default",
            resolved_at=datetime.now(UTC),
        )
        assert (
            binding.connection_ref
            == "secrets://my-vault/postgres@primary?ssl=true&timeout=30"
        )

    def test_unicode_characters_in_resolution_notes(self) -> None:
        """Test unicode characters in resolution notes."""
        binding = ModelBinding(
            dependency_alias="db",
            capability="database.relational",
            resolved_provider="test-id",
            adapter="test.Adapter",
            connection_ref="env://TEST",
            requirements_hash="hash123",
            resolution_profile="default",
            resolved_at=datetime.now(UTC),
            resolution_notes=["Selected provider in region eu-west-1"],
        )
        assert "eu-west-1" in binding.resolution_notes[0]

    def test_very_long_adapter_path(self) -> None:
        """Test very long adapter import path."""
        long_adapter = "omnibase_infra.adapters.deep.nested.module.PostgresAdapter"
        binding = ModelBinding(
            dependency_alias="db",
            capability="database.relational",
            resolved_provider="test-id",
            adapter=long_adapter,
            connection_ref="env://TEST",
            requirements_hash="hash123",
            resolution_profile="default",
            resolved_at=datetime.now(UTC),
        )
        assert binding.adapter == long_adapter

    def test_numeric_resolved_provider(self) -> None:
        """Test numeric string resolved_provider."""
        binding = ModelBinding(
            dependency_alias="db",
            capability="database.relational",
            resolved_provider="12345",
            adapter="test.Adapter",
            connection_ref="env://TEST",
            requirements_hash="hash123",
            resolution_profile="default",
            resolved_at=datetime.now(UTC),
        )
        assert binding.resolved_provider == "12345"

    def test_capability_with_hyphens(self) -> None:
        """Test capability with hyphens in tokens."""
        binding = ModelBinding(
            dependency_alias="embed",
            capability="llm.text-embedding.v1",
            resolved_provider="test-id",
            adapter="test.Adapter",
            connection_ref="env://TEST",
            requirements_hash="hash123",
            resolution_profile="default",
            resolved_at=datetime.now(UTC),
        )
        assert binding.capability == "llm.text-embedding.v1"

    def test_resolved_at_with_different_timezones(self) -> None:
        """Test resolved_at with UTC timezone."""
        resolved_at = datetime(2024, 6, 15, 10, 30, 0, tzinfo=UTC)
        binding = ModelBinding(
            dependency_alias="db",
            capability="database.relational",
            resolved_provider="test-id",
            adapter="test.Adapter",
            connection_ref="env://TEST",
            requirements_hash="hash123",
            resolution_profile="default",
            resolved_at=resolved_at,
        )
        assert binding.resolved_at == resolved_at
        assert binding.resolved_at.tzinfo == UTC

    def test_model_copy_creates_independent_instance(self) -> None:
        """Test that model_copy creates an independent instance."""
        binding = ModelBinding(
            dependency_alias="db",
            capability="database.relational",
            resolved_provider="test-id",
            adapter="test.Adapter",
            connection_ref="env://TEST",
            requirements_hash="hash123",
            resolution_profile="default",
            resolved_at=datetime.now(UTC),
            candidates_considered=5,
        )
        copied = binding.model_copy(update={"candidates_considered": 10})
        assert binding.candidates_considered == 5
        assert copied.candidates_considered == 10
        assert binding.dependency_alias == copied.dependency_alias


@pytest.mark.unit
class TestModelBindingSerialization:
    """Tests for model serialization and deserialization."""

    def test_model_dump_produces_dict(self) -> None:
        """Test that model_dump produces a dictionary."""
        resolved_at = datetime.now(UTC)
        binding = ModelBinding(
            dependency_alias="db",
            capability="database.relational",
            resolved_provider="test-id",
            adapter="test.Adapter",
            connection_ref="env://TEST",
            requirements_hash="hash123",
            resolution_profile="production",
            resolved_at=resolved_at,
            resolution_notes=["Note 1"],
            candidates_considered=3,
        )
        data = binding.model_dump()
        assert isinstance(data, dict)
        assert data["dependency_alias"] == "db"
        assert data["capability"] == "database.relational"
        assert data["resolved_provider"] == "test-id"
        assert data["resolution_notes"] == ["Note 1"]
        assert data["candidates_considered"] == 3

    def test_model_dump_json_produces_json_string(self) -> None:
        """Test that model_dump_json produces valid JSON."""
        binding = ModelBinding(
            dependency_alias="db",
            capability="database.relational",
            resolved_provider="test-id",
            adapter="test.Adapter",
            connection_ref="env://TEST",
            requirements_hash="hash123",
            resolution_profile="default",
            resolved_at=datetime.now(UTC),
        )
        json_str = binding.model_dump_json()
        assert isinstance(json_str, str)
        assert '"dependency_alias":"db"' in json_str

    def test_model_validate_from_dict(self) -> None:
        """Test that model_validate can reconstruct from dict."""
        resolved_at = datetime.now(UTC)
        data = {
            "dependency_alias": "db",
            "capability": "database.relational",
            "resolved_provider": "test-id",
            "adapter": "test.Adapter",
            "connection_ref": "env://TEST",
            "requirements_hash": "hash123",
            "resolution_profile": "default",
            "resolved_at": resolved_at,
            "resolution_notes": ["Note 1"],
            "candidates_considered": 5,
        }
        binding = ModelBinding.model_validate(data)
        assert binding.dependency_alias == "db"
        assert binding.resolution_notes == ["Note 1"]
        assert binding.candidates_considered == 5
