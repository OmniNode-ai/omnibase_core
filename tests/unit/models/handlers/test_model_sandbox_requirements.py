# SPDX-FileCopyrightText: 2025 OmniNode Team
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for ModelSandboxRequirements."""

import pytest
from pydantic import ValidationError

from omnibase_core.models.handlers.model_sandbox_requirements import (
    ModelSandboxRequirements,
)


@pytest.mark.unit
class TestModelSandboxRequirementsInstantiation:
    """Tests for ModelSandboxRequirements instantiation."""

    def test_default_instantiation(self) -> None:
        """Test creating sandbox requirements with all defaults (most restrictive)."""
        sandbox = ModelSandboxRequirements()
        assert sandbox.requires_network is False
        assert sandbox.requires_filesystem is False
        assert sandbox.allowed_domains == []
        assert sandbox.memory_limit_mb is None
        assert sandbox.cpu_limit_cores is None

    def test_instantiation_with_network_enabled(self) -> None:
        """Test creating sandbox requirements with network access."""
        sandbox = ModelSandboxRequirements(requires_network=True)
        assert sandbox.requires_network is True
        assert sandbox.requires_filesystem is False

    def test_instantiation_with_filesystem_enabled(self) -> None:
        """Test creating sandbox requirements with filesystem access."""
        sandbox = ModelSandboxRequirements(requires_filesystem=True)
        assert sandbox.requires_network is False
        assert sandbox.requires_filesystem is True

    def test_instantiation_with_allowed_domains(self) -> None:
        """Test creating sandbox requirements with allowed domains."""
        domains = ["api.example.com", "storage.example.com"]
        sandbox = ModelSandboxRequirements(
            requires_network=True,
            allowed_domains=domains,
        )
        assert sandbox.allowed_domains == domains

    def test_instantiation_with_memory_limit(self) -> None:
        """Test creating sandbox requirements with memory limit."""
        sandbox = ModelSandboxRequirements(memory_limit_mb=1024)
        assert sandbox.memory_limit_mb == 1024

    def test_instantiation_with_cpu_limit(self) -> None:
        """Test creating sandbox requirements with CPU limit."""
        sandbox = ModelSandboxRequirements(cpu_limit_cores=4.0)
        assert sandbox.cpu_limit_cores == 4.0

    def test_instantiation_with_all_fields(self) -> None:
        """Test creating sandbox requirements with all fields."""
        sandbox = ModelSandboxRequirements(
            requires_network=True,
            requires_filesystem=True,
            allowed_domains=["api.example.com"],
            memory_limit_mb=2048,
            cpu_limit_cores=8.0,
        )
        assert sandbox.requires_network is True
        assert sandbox.requires_filesystem is True
        assert sandbox.allowed_domains == ["api.example.com"]
        assert sandbox.memory_limit_mb == 2048
        assert sandbox.cpu_limit_cores == 8.0


@pytest.mark.unit
class TestModelSandboxRequirementsMemoryValidation:
    """Tests for memory_limit_mb validation bounds."""

    def test_memory_limit_minimum_valid(self) -> None:
        """Test minimum valid memory limit (64 MB)."""
        sandbox = ModelSandboxRequirements(memory_limit_mb=64)
        assert sandbox.memory_limit_mb == 64

    def test_memory_limit_maximum_valid(self) -> None:
        """Test maximum valid memory limit (262144 MB = 256 GB)."""
        sandbox = ModelSandboxRequirements(memory_limit_mb=262144)
        assert sandbox.memory_limit_mb == 262144

    def test_memory_limit_below_minimum_rejected(self) -> None:
        """Test memory limit below minimum is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelSandboxRequirements(memory_limit_mb=63)
        assert "greater than or equal to 64" in str(exc_info.value)

    def test_memory_limit_above_maximum_rejected(self) -> None:
        """Test memory limit above maximum is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelSandboxRequirements(memory_limit_mb=262145)
        assert "less than or equal to 262144" in str(exc_info.value)

    def test_memory_limit_zero_rejected(self) -> None:
        """Test memory limit of zero is rejected."""
        with pytest.raises(ValidationError):
            ModelSandboxRequirements(memory_limit_mb=0)


@pytest.mark.unit
class TestModelSandboxRequirementsCPUValidation:
    """Tests for cpu_limit_cores validation bounds."""

    def test_cpu_limit_minimum_valid(self) -> None:
        """Test minimum valid CPU limit (0.1 cores)."""
        sandbox = ModelSandboxRequirements(cpu_limit_cores=0.1)
        assert sandbox.cpu_limit_cores == 0.1

    def test_cpu_limit_maximum_valid(self) -> None:
        """Test maximum valid CPU limit (256 cores)."""
        sandbox = ModelSandboxRequirements(cpu_limit_cores=256.0)
        assert sandbox.cpu_limit_cores == 256.0

    def test_cpu_limit_below_minimum_rejected(self) -> None:
        """Test CPU limit below minimum is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelSandboxRequirements(cpu_limit_cores=0.05)
        assert "greater than or equal to 0.1" in str(exc_info.value)

    def test_cpu_limit_above_maximum_rejected(self) -> None:
        """Test CPU limit above maximum is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelSandboxRequirements(cpu_limit_cores=257.0)
        assert "less than or equal to 256" in str(exc_info.value)

    def test_cpu_limit_zero_rejected(self) -> None:
        """Test CPU limit of zero is rejected."""
        with pytest.raises(ValidationError):
            ModelSandboxRequirements(cpu_limit_cores=0.0)


@pytest.mark.unit
class TestModelSandboxRequirementsDomainValidation:
    """Tests for allowed_domains validation."""

    def test_valid_simple_domain(self) -> None:
        """Test valid simple domain."""
        sandbox = ModelSandboxRequirements(allowed_domains=["example.com"])
        assert sandbox.allowed_domains == ["example.com"]

    def test_valid_subdomain(self) -> None:
        """Test valid subdomain."""
        sandbox = ModelSandboxRequirements(
            allowed_domains=["api.example.com", "cdn.storage.example.com"]
        )
        assert len(sandbox.allowed_domains) == 2

    def test_valid_wildcard_at_leftmost(self) -> None:
        """Test valid wildcard at leftmost position."""
        sandbox = ModelSandboxRequirements(allowed_domains=["*.example.com"])
        assert sandbox.allowed_domains == ["*.example.com"]

    def test_valid_multiple_domains_with_wildcard(self) -> None:
        """Test multiple domains including wildcard."""
        domains = ["api.example.com", "*.storage.example.com"]
        sandbox = ModelSandboxRequirements(allowed_domains=domains)
        assert sandbox.allowed_domains == domains

    def test_invalid_nested_wildcard_rejected(self) -> None:
        """Test nested wildcard (*.*.example.com) is rejected."""
        with pytest.raises(Exception) as exc_info:
            ModelSandboxRequirements(allowed_domains=["*.*.example.com"])
        assert "Invalid domain" in str(exc_info.value)

    def test_invalid_wildcard_not_at_leftmost_rejected(self) -> None:
        """Test wildcard not at leftmost position is rejected."""
        with pytest.raises(Exception) as exc_info:
            ModelSandboxRequirements(allowed_domains=["api.*.example.com"])
        assert "Invalid domain" in str(exc_info.value)

    def test_invalid_wildcard_in_middle_rejected(self) -> None:
        """Test wildcard in middle of label is rejected."""
        with pytest.raises(Exception) as exc_info:
            ModelSandboxRequirements(allowed_domains=["a*pi.example.com"])
        assert "Invalid domain" in str(exc_info.value)

    def test_invalid_domain_with_scheme_rejected(self) -> None:
        """Test domain with scheme (https://) is rejected."""
        with pytest.raises(Exception) as exc_info:
            ModelSandboxRequirements(allowed_domains=["https://example.com"])
        assert "Invalid domain" in str(exc_info.value)

    def test_invalid_domain_with_path_rejected(self) -> None:
        """Test domain with path is rejected."""
        with pytest.raises(Exception) as exc_info:
            ModelSandboxRequirements(allowed_domains=["example.com/api"])
        assert "Invalid domain" in str(exc_info.value)

    def test_invalid_empty_domain_rejected(self) -> None:
        """Test empty domain string is rejected."""
        with pytest.raises(Exception) as exc_info:
            ModelSandboxRequirements(allowed_domains=[""])
        assert "Invalid domain" in str(exc_info.value)

    def test_invalid_domain_with_consecutive_dots_rejected(self) -> None:
        """Test domain with consecutive dots is rejected."""
        with pytest.raises(Exception) as exc_info:
            ModelSandboxRequirements(allowed_domains=["api..example.com"])
        assert "Invalid domain" in str(exc_info.value)

    def test_valid_single_label_domain(self) -> None:
        """Test valid single label domain (e.g., localhost)."""
        sandbox = ModelSandboxRequirements(allowed_domains=["localhost"])
        assert sandbox.allowed_domains == ["localhost"]

    def test_valid_domain_with_hyphen(self) -> None:
        """Test valid domain with hyphens in labels."""
        sandbox = ModelSandboxRequirements(
            allowed_domains=["my-api.example-domain.com"]
        )
        assert sandbox.allowed_domains == ["my-api.example-domain.com"]

    def test_invalid_domain_starting_with_hyphen_rejected(self) -> None:
        """Test domain label starting with hyphen is rejected."""
        with pytest.raises(Exception) as exc_info:
            ModelSandboxRequirements(allowed_domains=["-api.example.com"])
        assert "Invalid domain" in str(exc_info.value)

    def test_invalid_domain_ending_with_hyphen_rejected(self) -> None:
        """Test domain label ending with hyphen is rejected."""
        with pytest.raises(Exception) as exc_info:
            ModelSandboxRequirements(allowed_domains=["api-.example.com"])
        assert "Invalid domain" in str(exc_info.value)


@pytest.mark.unit
class TestModelSandboxRequirementsImmutability:
    """Tests for ModelSandboxRequirements frozen immutability."""

    def test_frozen_immutability_requires_network(self) -> None:
        """Test that requires_network cannot be modified (frozen model)."""
        sandbox = ModelSandboxRequirements(requires_network=True)
        with pytest.raises(ValidationError, match="frozen"):
            sandbox.requires_network = False  # type: ignore[misc]

    def test_frozen_immutability_requires_filesystem(self) -> None:
        """Test that requires_filesystem cannot be modified (frozen model)."""
        sandbox = ModelSandboxRequirements(requires_filesystem=True)
        with pytest.raises(ValidationError, match="frozen"):
            sandbox.requires_filesystem = False  # type: ignore[misc]

    def test_frozen_immutability_memory_limit(self) -> None:
        """Test that memory_limit_mb cannot be modified (frozen model)."""
        sandbox = ModelSandboxRequirements(memory_limit_mb=1024)
        with pytest.raises(ValidationError, match="frozen"):
            sandbox.memory_limit_mb = 2048  # type: ignore[misc]


@pytest.mark.unit
class TestModelSandboxRequirementsExtraFields:
    """Tests for extra field rejection."""

    def test_extra_fields_rejected(self) -> None:
        """Test that extra fields are rejected (extra='forbid')."""
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            ModelSandboxRequirements(
                extra_field="should_fail",  # type: ignore[call-arg]
            )


@pytest.mark.unit
class TestModelSandboxRequirementsSerialization:
    """Tests for ModelSandboxRequirements serialization."""

    def test_model_dump_defaults(self) -> None:
        """Test model_dump with default fields."""
        sandbox = ModelSandboxRequirements()
        data = sandbox.model_dump()
        assert data["requires_network"] is False
        assert data["requires_filesystem"] is False
        assert data["allowed_domains"] == []
        assert data["memory_limit_mb"] is None
        assert data["cpu_limit_cores"] is None

    def test_model_dump_full(self) -> None:
        """Test model_dump with all fields."""
        sandbox = ModelSandboxRequirements(
            requires_network=True,
            requires_filesystem=True,
            allowed_domains=["api.example.com"],
            memory_limit_mb=2048,
            cpu_limit_cores=4.0,
        )
        data = sandbox.model_dump()
        assert data["requires_network"] is True
        assert data["requires_filesystem"] is True
        assert data["allowed_domains"] == ["api.example.com"]
        assert data["memory_limit_mb"] == 2048
        assert data["cpu_limit_cores"] == 4.0

    def test_model_dump_roundtrip(self) -> None:
        """Test serialization and deserialization roundtrip."""
        original = ModelSandboxRequirements(
            requires_network=True,
            allowed_domains=["*.example.com"],
            memory_limit_mb=512,
            cpu_limit_cores=2.0,
        )
        data = original.model_dump()
        restored = ModelSandboxRequirements(**data)

        assert restored.requires_network == original.requires_network
        assert restored.requires_filesystem == original.requires_filesystem
        assert restored.allowed_domains == original.allowed_domains
        assert restored.memory_limit_mb == original.memory_limit_mb
        assert restored.cpu_limit_cores == original.cpu_limit_cores


@pytest.mark.unit
class TestModelSandboxRequirementsRepr:
    """Tests for __repr__ output."""

    def test_repr_isolated(self) -> None:
        """Test repr for isolated (default) sandbox."""
        sandbox = ModelSandboxRequirements()
        repr_str = repr(sandbox)
        assert "isolated" in repr_str

    def test_repr_with_network(self) -> None:
        """Test repr with network enabled."""
        sandbox = ModelSandboxRequirements(requires_network=True)
        repr_str = repr(sandbox)
        assert "network=True" in repr_str

    def test_repr_with_domains(self) -> None:
        """Test repr with domains shows count."""
        sandbox = ModelSandboxRequirements(
            requires_network=True,
            allowed_domains=["a.com", "b.com", "c.com"],
        )
        repr_str = repr(sandbox)
        assert "domains=3" in repr_str

    def test_repr_with_memory(self) -> None:
        """Test repr with memory limit."""
        sandbox = ModelSandboxRequirements(memory_limit_mb=1024)
        repr_str = repr(sandbox)
        assert "mem=1024MB" in repr_str

    def test_repr_with_cpu(self) -> None:
        """Test repr with CPU limit."""
        sandbox = ModelSandboxRequirements(cpu_limit_cores=4.0)
        repr_str = repr(sandbox)
        assert "cpu=4.0" in repr_str
