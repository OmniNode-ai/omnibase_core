# SPDX-FileCopyrightText: 2025 OmniNode Team
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for ModelHandlerPackaging."""

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_hash_algorithm import EnumHashAlgorithm
from omnibase_core.enums.enum_signature_algorithm import EnumSignatureAlgorithm
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.handlers.model_handler_packaging import ModelHandlerPackaging
from omnibase_core.models.handlers.model_sandbox_requirements import (
    ModelSandboxRequirements,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer

# Test fixtures
VALID_SHA256_HASH = "a" * 64  # 64 lowercase hex chars
VALID_HTTPS_ARTIFACT = "https://releases.example.com/handler-1.0.0.whl"
VALID_OCI_ARTIFACT = "oci://ghcr.io/omninode/handlers/validator:v1.0.0"
VALID_FILE_ARTIFACT = "file:///opt/handlers/validator.whl"
VALID_REGISTRY_ARTIFACT = "registry://myorg/handler/v1.0.0"


@pytest.mark.unit
class TestModelHandlerPackagingInstantiation:
    """Tests for ModelHandlerPackaging instantiation."""

    def test_minimal_instantiation(self) -> None:
        """Test creating packaging with minimal required fields."""
        packaging = ModelHandlerPackaging(
            artifact_reference=VALID_HTTPS_ARTIFACT,
            integrity_hash=VALID_SHA256_HASH,
            sandbox_compatibility=ModelSandboxRequirements(),
            min_runtime_version=ModelSemVer(major=0, minor=6, patch=0),
        )
        assert packaging.artifact_reference == VALID_HTTPS_ARTIFACT
        assert packaging.integrity_hash == VALID_SHA256_HASH
        assert packaging.hash_algorithm == EnumHashAlgorithm.SHA256  # default
        assert packaging.signature_reference is None
        assert packaging.signature_algorithm is None
        assert packaging.max_runtime_version is None

    def test_instantiation_with_signature(self) -> None:
        """Test creating packaging with signature verification."""
        packaging = ModelHandlerPackaging(
            artifact_reference=VALID_OCI_ARTIFACT,
            integrity_hash=VALID_SHA256_HASH,
            signature_reference="https://releases.example.com/handler.sig",
            signature_algorithm=EnumSignatureAlgorithm.ED25519,
            sandbox_compatibility=ModelSandboxRequirements(),
            min_runtime_version=ModelSemVer(major=0, minor=6, patch=0),
        )
        assert (
            packaging.signature_reference == "https://releases.example.com/handler.sig"
        )
        assert packaging.signature_algorithm == EnumSignatureAlgorithm.ED25519

    def test_instantiation_with_max_version(self) -> None:
        """Test creating packaging with max runtime version."""
        packaging = ModelHandlerPackaging(
            artifact_reference=VALID_HTTPS_ARTIFACT,
            integrity_hash=VALID_SHA256_HASH,
            sandbox_compatibility=ModelSandboxRequirements(),
            min_runtime_version=ModelSemVer(major=0, minor=6, patch=0),
            max_runtime_version=ModelSemVer(major=1, minor=0, patch=0),
        )
        assert packaging.min_runtime_version == ModelSemVer(major=0, minor=6, patch=0)
        assert packaging.max_runtime_version == ModelSemVer(major=1, minor=0, patch=0)

    def test_instantiation_with_all_fields(self) -> None:
        """Test creating packaging with all fields."""
        sandbox = ModelSandboxRequirements(
            requires_network=True,
            memory_limit_mb=512,
        )
        packaging = ModelHandlerPackaging(
            artifact_reference=VALID_OCI_ARTIFACT,
            integrity_hash=VALID_SHA256_HASH,
            hash_algorithm=EnumHashAlgorithm.SHA256,
            signature_reference="https://example.com/sig",
            signature_algorithm=EnumSignatureAlgorithm.ED25519,
            sandbox_compatibility=sandbox,
            min_runtime_version=ModelSemVer(major=0, minor=6, patch=0),
            max_runtime_version=ModelSemVer(major=2, minor=0, patch=0),
        )
        assert packaging.artifact_reference == VALID_OCI_ARTIFACT
        assert packaging.sandbox_compatibility == sandbox


@pytest.mark.unit
class TestModelHandlerPackagingArtifactReferenceValidation:
    """Tests for artifact_reference validation."""

    def test_valid_https_artifact(self) -> None:
        """Test valid HTTPS artifact reference."""
        packaging = ModelHandlerPackaging(
            artifact_reference=VALID_HTTPS_ARTIFACT,
            integrity_hash=VALID_SHA256_HASH,
            sandbox_compatibility=ModelSandboxRequirements(),
            min_runtime_version=ModelSemVer(major=0, minor=6, patch=0),
        )
        assert packaging.artifact_reference.startswith("https://")

    def test_valid_oci_artifact(self) -> None:
        """Test valid OCI artifact reference."""
        packaging = ModelHandlerPackaging(
            artifact_reference=VALID_OCI_ARTIFACT,
            integrity_hash=VALID_SHA256_HASH,
            sandbox_compatibility=ModelSandboxRequirements(),
            min_runtime_version=ModelSemVer(major=0, minor=6, patch=0),
        )
        assert packaging.artifact_reference.startswith("oci://")

    def test_valid_file_artifact(self) -> None:
        """Test valid file:/// artifact reference."""
        packaging = ModelHandlerPackaging(
            artifact_reference=VALID_FILE_ARTIFACT,
            integrity_hash=VALID_SHA256_HASH,
            sandbox_compatibility=ModelSandboxRequirements(),
            min_runtime_version=ModelSemVer(major=0, minor=6, patch=0),
        )
        assert packaging.artifact_reference.startswith("file:///")

    def test_valid_registry_artifact(self) -> None:
        """Test valid registry:// artifact reference."""
        packaging = ModelHandlerPackaging(
            artifact_reference=VALID_REGISTRY_ARTIFACT,
            integrity_hash=VALID_SHA256_HASH,
            sandbox_compatibility=ModelSandboxRequirements(),
            min_runtime_version=ModelSemVer(major=0, minor=6, patch=0),
        )
        assert packaging.artifact_reference.startswith("registry://")

    def test_invalid_raw_local_path_rejected(self) -> None:
        """Test raw local path without file:// scheme is rejected."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelHandlerPackaging(
                artifact_reference="/opt/handlers/validator.whl",
                integrity_hash=VALID_SHA256_HASH,
                sandbox_compatibility=ModelSandboxRequirements(),
                min_runtime_version=ModelSemVer(major=0, minor=6, patch=0),
            )
        assert "Invalid artifact_reference" in str(exc_info.value)

    def test_invalid_http_artifact_rejected(self) -> None:
        """Test HTTP (not HTTPS) artifact reference is rejected."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelHandlerPackaging(
                artifact_reference="http://example.com/handler.whl",
                integrity_hash=VALID_SHA256_HASH,
                sandbox_compatibility=ModelSandboxRequirements(),
                min_runtime_version=ModelSemVer(major=0, minor=6, patch=0),
            )
        assert "Invalid artifact_reference" in str(exc_info.value)

    def test_invalid_unknown_scheme_rejected(self) -> None:
        """Test unknown scheme is rejected."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelHandlerPackaging(
                artifact_reference="ftp://example.com/handler.whl",
                integrity_hash=VALID_SHA256_HASH,
                sandbox_compatibility=ModelSandboxRequirements(),
                min_runtime_version=ModelSemVer(major=0, minor=6, patch=0),
            )
        assert "Invalid artifact_reference" in str(exc_info.value)

    def test_invalid_empty_artifact_rejected(self) -> None:
        """Test empty artifact reference is rejected."""
        with pytest.raises(ValidationError):
            ModelHandlerPackaging(
                artifact_reference="",
                integrity_hash=VALID_SHA256_HASH,
                sandbox_compatibility=ModelSandboxRequirements(),
                min_runtime_version=ModelSemVer(major=0, minor=6, patch=0),
            )


@pytest.mark.unit
class TestModelHandlerPackagingURLStructureValidation:
    """Tests for URL structure validation using urlparse."""

    def test_https_url_without_host_rejected(self) -> None:
        """Test HTTPS URL without host is rejected."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelHandlerPackaging(
                artifact_reference="https:///path/to/handler.whl",
                integrity_hash=VALID_SHA256_HASH,
                sandbox_compatibility=ModelSandboxRequirements(),
                min_runtime_version=ModelSemVer(major=0, minor=6, patch=0),
            )
        assert "must include a host" in str(exc_info.value)

    def test_https_url_without_path_rejected(self) -> None:
        """Test HTTPS URL without path is rejected."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelHandlerPackaging(
                artifact_reference="https://example.com",
                integrity_hash=VALID_SHA256_HASH,
                sandbox_compatibility=ModelSandboxRequirements(),
                min_runtime_version=ModelSemVer(major=0, minor=6, patch=0),
            )
        assert "must include a path" in str(exc_info.value)

    def test_https_url_with_only_slash_path_rejected(self) -> None:
        """Test HTTPS URL with only root path is rejected."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelHandlerPackaging(
                artifact_reference="https://example.com/",
                integrity_hash=VALID_SHA256_HASH,
                sandbox_compatibility=ModelSandboxRequirements(),
                min_runtime_version=ModelSemVer(major=0, minor=6, patch=0),
            )
        assert "must include a path" in str(exc_info.value)

    def test_oci_url_without_registry_rejected(self) -> None:
        """Test OCI URL without registry host is rejected."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelHandlerPackaging(
                artifact_reference="oci:///image:tag",
                integrity_hash=VALID_SHA256_HASH,
                sandbox_compatibility=ModelSandboxRequirements(),
                min_runtime_version=ModelSemVer(major=0, minor=6, patch=0),
            )
        assert "must include a host" in str(exc_info.value)

    def test_oci_url_without_image_path_rejected(self) -> None:
        """Test OCI URL without image path is rejected."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelHandlerPackaging(
                artifact_reference="oci://ghcr.io",
                integrity_hash=VALID_SHA256_HASH,
                sandbox_compatibility=ModelSandboxRequirements(),
                min_runtime_version=ModelSemVer(major=0, minor=6, patch=0),
            )
        assert "must include a path" in str(exc_info.value)

    def test_registry_url_without_host_rejected(self) -> None:
        """Test registry URL without host is rejected."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelHandlerPackaging(
                artifact_reference="registry:///org/handler",
                integrity_hash=VALID_SHA256_HASH,
                sandbox_compatibility=ModelSandboxRequirements(),
                min_runtime_version=ModelSemVer(major=0, minor=6, patch=0),
            )
        assert "must include a host" in str(exc_info.value)

    def test_file_url_without_path_rejected(self) -> None:
        """Test file URL without path is rejected."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelHandlerPackaging(
                artifact_reference="file:///",
                integrity_hash=VALID_SHA256_HASH,
                sandbox_compatibility=ModelSandboxRequirements(),
                min_runtime_version=ModelSemVer(major=0, minor=6, patch=0),
            )
        assert "must include a path" in str(exc_info.value)

    def test_valid_urls_with_proper_structure_accepted(self) -> None:
        """Test valid URLs with proper structure are accepted."""
        valid_urls = [
            "https://example.com/path/to/handler.whl",
            "https://releases.example.com/v1/handlers/my-handler.whl",
            "oci://ghcr.io/org/handler:v1.0.0",
            "oci://docker.io/library/python:3.12",
            "registry://internal.corp/handlers/validator",
            "file:///opt/handlers/handler.whl",
            "file:///home/user/handlers/handler.whl",
        ]
        for url in valid_urls:
            packaging = ModelHandlerPackaging(
                artifact_reference=url,
                integrity_hash=VALID_SHA256_HASH,
                sandbox_compatibility=ModelSandboxRequirements(),
                min_runtime_version=ModelSemVer(major=0, minor=6, patch=0),
            )
            assert packaging.artifact_reference == url


@pytest.mark.unit
class TestModelHandlerPackagingIntegrityHashValidation:
    """Tests for integrity_hash validation."""

    def test_valid_sha256_hash(self) -> None:
        """Test valid SHA256 hash (64 lowercase hex)."""
        valid_hash = "0123456789abcdef" * 4  # 64 chars
        packaging = ModelHandlerPackaging(
            artifact_reference=VALID_HTTPS_ARTIFACT,
            integrity_hash=valid_hash,
            sandbox_compatibility=ModelSandboxRequirements(),
            min_runtime_version=ModelSemVer(major=0, minor=6, patch=0),
        )
        assert packaging.integrity_hash == valid_hash

    def test_invalid_hash_wrong_length_rejected(self) -> None:
        """Test hash with wrong length is rejected.

        Note: Pydantic's min_length=64 constraint catches this before
        the custom validator runs, so we expect ValidationError.
        """
        with pytest.raises(ValidationError) as exc_info:
            ModelHandlerPackaging(
                artifact_reference=VALID_HTTPS_ARTIFACT,
                integrity_hash="a" * 63,  # 63 chars - too short
                sandbox_compatibility=ModelSandboxRequirements(),
                min_runtime_version=ModelSemVer(major=0, minor=6, patch=0),
            )
        error_str = str(exc_info.value)
        assert "64" in error_str or "string_too_short" in error_str

    def test_invalid_hash_uppercase_rejected(self) -> None:
        """Test hash with uppercase chars is rejected."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelHandlerPackaging(
                artifact_reference=VALID_HTTPS_ARTIFACT,
                integrity_hash="A" * 64,  # uppercase
                sandbox_compatibility=ModelSandboxRequirements(),
                min_runtime_version=ModelSemVer(major=0, minor=6, patch=0),
            )
        assert "Invalid integrity_hash" in str(exc_info.value)

    def test_invalid_hash_non_hex_rejected(self) -> None:
        """Test hash with non-hex chars is rejected."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelHandlerPackaging(
                artifact_reference=VALID_HTTPS_ARTIFACT,
                integrity_hash="g" * 64,  # 'g' is not hex
                sandbox_compatibility=ModelSandboxRequirements(),
                min_runtime_version=ModelSemVer(major=0, minor=6, patch=0),
            )
        assert "Invalid integrity_hash" in str(exc_info.value)


@pytest.mark.unit
class TestModelHandlerPackagingHashAlgorithmValidation:
    """Tests for hash_algorithm validation (v1 = SHA256 only)."""

    def test_sha256_algorithm_accepted(self) -> None:
        """Test SHA256 hash algorithm is accepted."""
        packaging = ModelHandlerPackaging(
            artifact_reference=VALID_HTTPS_ARTIFACT,
            integrity_hash=VALID_SHA256_HASH,
            hash_algorithm=EnumHashAlgorithm.SHA256,
            sandbox_compatibility=ModelSandboxRequirements(),
            min_runtime_version=ModelSemVer(major=0, minor=6, patch=0),
        )
        assert packaging.hash_algorithm == EnumHashAlgorithm.SHA256

    def test_default_hash_algorithm_is_sha256(self) -> None:
        """Test default hash algorithm is SHA256."""
        packaging = ModelHandlerPackaging(
            artifact_reference=VALID_HTTPS_ARTIFACT,
            integrity_hash=VALID_SHA256_HASH,
            sandbox_compatibility=ModelSandboxRequirements(),
            min_runtime_version=ModelSemVer(major=0, minor=6, patch=0),
        )
        assert packaging.hash_algorithm == EnumHashAlgorithm.SHA256


@pytest.mark.unit
class TestModelHandlerPackagingSignatureValidation:
    """Tests for signature_reference and signature_algorithm consistency."""

    def test_signature_reference_without_algorithm_rejected(self) -> None:
        """Test signature_reference without signature_algorithm is rejected."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelHandlerPackaging(
                artifact_reference=VALID_HTTPS_ARTIFACT,
                integrity_hash=VALID_SHA256_HASH,
                signature_reference="https://example.com/handler.sig",
                # Missing signature_algorithm
                sandbox_compatibility=ModelSandboxRequirements(),
                min_runtime_version=ModelSemVer(major=0, minor=6, patch=0),
            )
        assert "signature_algorithm is required" in str(exc_info.value)

    def test_signature_algorithm_without_reference_rejected(self) -> None:
        """Test signature_algorithm without signature_reference is rejected."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelHandlerPackaging(
                artifact_reference=VALID_HTTPS_ARTIFACT,
                integrity_hash=VALID_SHA256_HASH,
                signature_algorithm=EnumSignatureAlgorithm.ED25519,
                # Missing signature_reference
                sandbox_compatibility=ModelSandboxRequirements(),
                min_runtime_version=ModelSemVer(major=0, minor=6, patch=0),
            )
        assert "signature_reference is required" in str(exc_info.value)

    def test_ed25519_signature_algorithm_accepted(self) -> None:
        """Test ED25519 signature algorithm is accepted (v1)."""
        packaging = ModelHandlerPackaging(
            artifact_reference=VALID_HTTPS_ARTIFACT,
            integrity_hash=VALID_SHA256_HASH,
            signature_reference="https://example.com/handler.sig",
            signature_algorithm=EnumSignatureAlgorithm.ED25519,
            sandbox_compatibility=ModelSandboxRequirements(),
            min_runtime_version=ModelSemVer(major=0, minor=6, patch=0),
        )
        assert packaging.signature_algorithm == EnumSignatureAlgorithm.ED25519

    def test_non_ed25519_signature_algorithm_rejected(self) -> None:
        """Test non-ED25519 signature algorithms are rejected (v1)."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelHandlerPackaging(
                artifact_reference=VALID_HTTPS_ARTIFACT,
                integrity_hash=VALID_SHA256_HASH,
                signature_reference="https://example.com/handler.sig",
                signature_algorithm=EnumSignatureAlgorithm.RS256,  # Not ED25519
                sandbox_compatibility=ModelSandboxRequirements(),
                min_runtime_version=ModelSemVer(major=0, minor=6, patch=0),
            )
        assert "v1 supports only ED25519" in str(exc_info.value)


@pytest.mark.unit
class TestModelHandlerPackagingVersionValidation:
    """Tests for runtime version validation."""

    def test_min_greater_than_max_rejected(self) -> None:
        """Test min_runtime_version > max_runtime_version is rejected."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelHandlerPackaging(
                artifact_reference=VALID_HTTPS_ARTIFACT,
                integrity_hash=VALID_SHA256_HASH,
                sandbox_compatibility=ModelSandboxRequirements(),
                min_runtime_version=ModelSemVer(major=2, minor=0, patch=0),
                max_runtime_version=ModelSemVer(major=1, minor=0, patch=0),
            )
        assert "min_runtime_version" in str(exc_info.value)

    def test_min_equals_max_accepted(self) -> None:
        """Test min_runtime_version == max_runtime_version is accepted."""
        version = ModelSemVer(major=1, minor=0, patch=0)
        packaging = ModelHandlerPackaging(
            artifact_reference=VALID_HTTPS_ARTIFACT,
            integrity_hash=VALID_SHA256_HASH,
            sandbox_compatibility=ModelSandboxRequirements(),
            min_runtime_version=version,
            max_runtime_version=version,
        )
        assert packaging.min_runtime_version == packaging.max_runtime_version


@pytest.mark.unit
class TestModelHandlerPackagingImmutability:
    """Tests for ModelHandlerPackaging frozen immutability."""

    def test_frozen_immutability_artifact_reference(self) -> None:
        """Test that artifact_reference cannot be modified (frozen model)."""
        packaging = ModelHandlerPackaging(
            artifact_reference=VALID_HTTPS_ARTIFACT,
            integrity_hash=VALID_SHA256_HASH,
            sandbox_compatibility=ModelSandboxRequirements(),
            min_runtime_version=ModelSemVer(major=0, minor=6, patch=0),
        )
        with pytest.raises(ValidationError, match="frozen"):
            packaging.artifact_reference = "oci://other"  # type: ignore[misc]

    def test_frozen_immutability_integrity_hash(self) -> None:
        """Test that integrity_hash cannot be modified (frozen model)."""
        packaging = ModelHandlerPackaging(
            artifact_reference=VALID_HTTPS_ARTIFACT,
            integrity_hash=VALID_SHA256_HASH,
            sandbox_compatibility=ModelSandboxRequirements(),
            min_runtime_version=ModelSemVer(major=0, minor=6, patch=0),
        )
        with pytest.raises(ValidationError, match="frozen"):
            packaging.integrity_hash = "b" * 64  # type: ignore[misc]


@pytest.mark.unit
class TestModelHandlerPackagingExtraFields:
    """Tests for extra field rejection."""

    def test_extra_fields_rejected(self) -> None:
        """Test that extra fields are rejected (extra='forbid')."""
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            ModelHandlerPackaging(
                artifact_reference=VALID_HTTPS_ARTIFACT,
                integrity_hash=VALID_SHA256_HASH,
                sandbox_compatibility=ModelSandboxRequirements(),
                min_runtime_version=ModelSemVer(major=0, minor=6, patch=0),
                extra_field="should_fail",  # type: ignore[call-arg]
            )


@pytest.mark.unit
class TestModelHandlerPackagingSerialization:
    """Tests for ModelHandlerPackaging serialization."""

    def test_model_dump_minimal(self) -> None:
        """Test model_dump with minimal fields."""
        packaging = ModelHandlerPackaging(
            artifact_reference=VALID_HTTPS_ARTIFACT,
            integrity_hash=VALID_SHA256_HASH,
            sandbox_compatibility=ModelSandboxRequirements(),
            min_runtime_version=ModelSemVer(major=0, minor=6, patch=0),
        )
        data = packaging.model_dump()
        assert data["artifact_reference"] == VALID_HTTPS_ARTIFACT
        assert data["integrity_hash"] == VALID_SHA256_HASH
        assert data["hash_algorithm"] == "sha256"
        assert data["signature_reference"] is None
        assert data["signature_algorithm"] is None
        assert data["max_runtime_version"] is None

    def test_model_dump_roundtrip(self) -> None:
        """Test serialization and deserialization roundtrip."""
        original = ModelHandlerPackaging(
            artifact_reference=VALID_OCI_ARTIFACT,
            integrity_hash=VALID_SHA256_HASH,
            signature_reference="https://example.com/handler.sig",
            signature_algorithm=EnumSignatureAlgorithm.ED25519,
            sandbox_compatibility=ModelSandboxRequirements(
                requires_network=True,
                memory_limit_mb=512,
            ),
            min_runtime_version=ModelSemVer(major=0, minor=6, patch=0),
            max_runtime_version=ModelSemVer(major=1, minor=0, patch=0),
        )
        data = original.model_dump()
        restored = ModelHandlerPackaging(**data)

        assert restored.artifact_reference == original.artifact_reference
        assert restored.integrity_hash == original.integrity_hash
        assert restored.signature_reference == original.signature_reference
        assert restored.signature_algorithm == original.signature_algorithm


@pytest.mark.unit
class TestModelHandlerPackagingRepr:
    """Tests for __repr__ output."""

    def test_repr_https_scheme(self) -> None:
        """Test repr shows scheme."""
        packaging = ModelHandlerPackaging(
            artifact_reference=VALID_HTTPS_ARTIFACT,
            integrity_hash=VALID_SHA256_HASH,
            sandbox_compatibility=ModelSandboxRequirements(),
            min_runtime_version=ModelSemVer(major=0, minor=6, patch=0),
        )
        repr_str = repr(packaging)
        assert "scheme=https" in repr_str

    def test_repr_oci_scheme(self) -> None:
        """Test repr shows OCI scheme."""
        packaging = ModelHandlerPackaging(
            artifact_reference=VALID_OCI_ARTIFACT,
            integrity_hash=VALID_SHA256_HASH,
            sandbox_compatibility=ModelSandboxRequirements(),
            min_runtime_version=ModelSemVer(major=0, minor=6, patch=0),
        )
        repr_str = repr(packaging)
        assert "scheme=oci" in repr_str

    def test_repr_signed(self) -> None:
        """Test repr shows signed=True when signature present."""
        packaging = ModelHandlerPackaging(
            artifact_reference=VALID_HTTPS_ARTIFACT,
            integrity_hash=VALID_SHA256_HASH,
            signature_reference="https://example.com/sig",
            signature_algorithm=EnumSignatureAlgorithm.ED25519,
            sandbox_compatibility=ModelSandboxRequirements(),
            min_runtime_version=ModelSemVer(major=0, minor=6, patch=0),
        )
        repr_str = repr(packaging)
        assert "signed=True" in repr_str
