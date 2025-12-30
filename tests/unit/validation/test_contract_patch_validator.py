# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Tests for ContractPatchValidator."""

import tempfile
from pathlib import Path

import pytest
import yaml

from omnibase_core.models.contracts.model_capability_provided import (
    ModelCapabilityProvided,
)
from omnibase_core.models.contracts.model_contract_patch import ModelContractPatch
from omnibase_core.models.contracts.model_dependency import ModelDependency
from omnibase_core.models.contracts.model_descriptor_patch import ModelDescriptorPatch
from omnibase_core.models.contracts.model_handler_spec import ModelHandlerSpec
from omnibase_core.models.contracts.model_profile_reference import ModelProfileReference
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.validation.contract_patch_validator import ContractPatchValidator
from omnibase_core.validation.protocol_patch_validator import ProtocolPatchValidator


class TestContractPatchValidator:
    """Tests for ContractPatchValidator."""

    @pytest.fixture
    def validator(self) -> ContractPatchValidator:
        """Create a validator fixture."""
        return ContractPatchValidator()

    @pytest.fixture
    def profile_ref(self) -> ModelProfileReference:
        """Create a profile reference fixture."""
        return ModelProfileReference(profile="compute_pure", version="1.0.0")

    def test_validate_minimal_patch(
        self, validator: ContractPatchValidator, profile_ref: ModelProfileReference
    ) -> None:
        """Test validating a minimal patch."""
        patch = ModelContractPatch(extends=profile_ref)
        result = validator.validate(patch)
        assert result.is_valid is True
        assert result.error_count == 0

    def test_validate_new_contract_patch(
        self, validator: ContractPatchValidator, profile_ref: ModelProfileReference
    ) -> None:
        """Test validating a new contract patch."""
        patch = ModelContractPatch(
            extends=profile_ref,
            name="my_handler",
            node_version=ModelSemVer(major=1, minor=0, patch=0),
        )
        result = validator.validate(patch)
        assert result.is_valid is True
        # Should have info about new contract identity
        assert any("NEW_CONTRACT_IDENTITY" in str(i.code) for i in result.issues)

    def test_validate_empty_descriptor_warning(
        self, validator: ContractPatchValidator, profile_ref: ModelProfileReference
    ) -> None:
        """Test warning for empty descriptor patch."""
        patch = ModelContractPatch(
            extends=profile_ref,
            descriptor=ModelDescriptorPatch(),  # Empty descriptor
        )
        result = validator.validate(patch)
        assert result.is_valid is True  # Warning, not error
        assert any("EMPTY_DESCRIPTOR_PATCH" in str(i.code) for i in result.issues)

    def test_validate_purity_idempotent_warning(
        self, validator: ContractPatchValidator, profile_ref: ModelProfileReference
    ) -> None:
        """Test warning for pure but not idempotent."""
        patch = ModelContractPatch(
            extends=profile_ref,
            descriptor=ModelDescriptorPatch(
                purity="pure",
                idempotent=False,
            ),
        )
        result = validator.validate(patch)
        assert result.is_valid is True  # Warning, not error
        assert any("PURITY_IDEMPOTENT_MISMATCH" in str(i.code) for i in result.issues)

    def test_validate_conflicting_handlers(
        self, validator: ContractPatchValidator, profile_ref: ModelProfileReference
    ) -> None:
        """Test error for conflicting handler operations."""
        patch = ModelContractPatch(
            extends=profile_ref,
            handlers__add=[
                ModelHandlerSpec(name="test_handler", handler_type="http"),
            ],
            handlers__remove=["test_handler"],
        )
        result = validator.validate(patch)
        assert result.is_valid is False
        assert any("CONFLICTING_LIST_OPERATIONS" in str(i.code) for i in result.issues)

    def test_validate_conflicting_dependencies(
        self, validator: ContractPatchValidator, profile_ref: ModelProfileReference
    ) -> None:
        """Test error for conflicting dependency operations."""
        patch = ModelContractPatch(
            extends=profile_ref,
            dependencies__add=[
                ModelDependency(name="ProtocolLogger"),
            ],
            dependencies__remove=["ProtocolLogger"],
        )
        result = validator.validate(patch)
        assert result.is_valid is False
        assert any("CONFLICTING_LIST_OPERATIONS" in str(i.code) for i in result.issues)

    def test_validate_conflicting_events(
        self, validator: ContractPatchValidator, profile_ref: ModelProfileReference
    ) -> None:
        """Test error for conflicting event operations."""
        patch = ModelContractPatch(
            extends=profile_ref,
            consumed_events__add=["user.created"],
            consumed_events__remove=["user.created"],
        )
        result = validator.validate(patch)
        assert result.is_valid is False
        assert any("CONFLICTING_LIST_OPERATIONS" in str(i.code) for i in result.issues)

    def test_validate_non_standard_profile_warning(
        self, validator: ContractPatchValidator
    ) -> None:
        """Test warning for non-standard profile name."""
        patch = ModelContractPatch(
            extends=ModelProfileReference(
                profile="MyProfile",  # Not lowercase_with_underscores
                version="1.0.0",
            ),
        )
        result = validator.validate(patch)
        assert result.is_valid is True  # Warning, not error
        assert any("NON_STANDARD_PROFILE_NAME" in str(i.code) for i in result.issues)

    def test_validate_non_standard_version_warning(
        self, validator: ContractPatchValidator
    ) -> None:
        """Test warning for non-standard version format."""
        patch = ModelContractPatch(
            extends=ModelProfileReference(
                profile="test",
                version="latest",  # No digits
            ),
        )
        result = validator.validate(patch)
        assert result.is_valid is True  # Warning, not error
        assert any("NON_STANDARD_VERSION_FORMAT" in str(i.code) for i in result.issues)

    def test_validate_dict_valid(self, validator: ContractPatchValidator) -> None:
        """Test validate_dict with valid data."""
        data = {
            "extends": {"profile": "compute_pure", "version": "1.0.0"},
            "name": "my_handler",
            "node_version": {"major": 1, "minor": 0, "patch": 0},
        }
        result = validator.validate_dict(data)
        assert result.is_valid is True
        assert result.validated_value is not None
        assert result.validated_value.name == "my_handler"

    def test_validate_dict_invalid_structure(
        self, validator: ContractPatchValidator
    ) -> None:
        """Test validate_dict with invalid structure."""
        data = {
            "extends": {"profile": "test", "version": "1.0.0"},
            "unknown_field": "not_allowed",  # Extra field
        }
        result = validator.validate_dict(data)
        assert result.is_valid is False
        assert any("PYDANTIC_VALIDATION_ERROR" in str(i.code) for i in result.issues)

    def test_validate_dict_missing_extends(
        self, validator: ContractPatchValidator
    ) -> None:
        """Test validate_dict with missing extends."""
        data = {"name": "test"}
        result = validator.validate_dict(data)
        assert result.is_valid is False

    def test_validate_file_valid(self, validator: ContractPatchValidator) -> None:
        """Test validate_file with valid YAML file."""
        data = {
            "extends": {"profile": "compute_pure", "version": "1.0.0"},
            "name": "my_handler",
            "node_version": {"major": 1, "minor": 0, "patch": 0},
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(data, f)
            f.flush()
            result = validator.validate_file(Path(f.name))

        assert result.is_valid is True
        assert result.validated_value is not None

    def test_validate_file_not_found(self, validator: ContractPatchValidator) -> None:
        """Test validate_file with non-existent file."""
        result = validator.validate_file(Path("/non/existent/file.yaml"))
        assert result.is_valid is False
        assert any("FILE_NOT_FOUND" in str(i.code) for i in result.issues)

    def test_validate_file_wrong_extension_warning(
        self, validator: ContractPatchValidator
    ) -> None:
        """Test validate_file warns about wrong extension."""
        data = {
            "extends": {"profile": "test", "version": "1.0.0"},
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            yaml.dump(data, f)
            f.flush()
            result = validator.validate_file(Path(f.name))

        # Should still validate but warn about extension
        assert any("UNEXPECTED_EXTENSION" in str(i.code) for i in result.issues)

    def test_validate_file_invalid_yaml(
        self, validator: ContractPatchValidator
    ) -> None:
        """Test validate_file with invalid YAML."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("invalid: yaml: content: [")
            f.flush()
            result = validator.validate_file(Path(f.name))

        assert result.is_valid is False
        # Uses load_yaml_content_as_model which wraps errors
        assert any(
            "YAML" in str(i.code) or "VALIDATION" in str(i.code) for i in result.issues
        )

    def test_validate_file_not_dict(self, validator: ContractPatchValidator) -> None:
        """Test validate_file with YAML that's not a dict."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("- item1\n- item2")  # List, not dict
            f.flush()
            result = validator.validate_file(Path(f.name))

        assert result.is_valid is False
        # Uses load_yaml_content_as_model which wraps the error
        assert any(
            "VALIDATION" in str(i.code) or "YAML" in str(i.code) for i in result.issues
        )

    def test_protocol_conformance(self, validator: ContractPatchValidator) -> None:
        """Test that validator conforms to ProtocolPatchValidator."""
        assert isinstance(validator, ProtocolPatchValidator)

    def test_validate_complex_patch(
        self, validator: ContractPatchValidator, profile_ref: ModelProfileReference
    ) -> None:
        """Test validating a complex patch with many fields."""
        patch = ModelContractPatch(
            extends=profile_ref,
            name="comprehensive_handler",
            node_version=ModelSemVer(major=2, minor=0, patch=0),
            description="A comprehensive handler",
            descriptor=ModelDescriptorPatch(
                purity="pure",
                idempotent=True,
                timeout_ms=10000,
            ),
            handlers__add=[
                ModelHandlerSpec(name="http_client", handler_type="http"),
            ],
            dependencies__add=[
                ModelDependency(name="ProtocolLogger"),
            ],
        )
        result = validator.validate(patch)
        assert result.is_valid is True

    def test_validate_duplicate_capability_outputs(
        self, validator: ContractPatchValidator, profile_ref: ModelProfileReference
    ) -> None:
        """Test error for duplicate capability outputs in add list."""
        patch = ModelContractPatch(
            extends=profile_ref,
            capability_outputs__add=[
                ModelCapabilityProvided(name="event_emit"),
                ModelCapabilityProvided(name="http_response"),
                ModelCapabilityProvided(name="event_emit"),  # Duplicate
            ],
        )
        result = validator.validate(patch)
        assert result.is_valid is False
        assert any("DUPLICATE_LIST_ENTRIES" in str(i.code) for i in result.issues)
        assert any("event_emit" in str(i.message) for i in result.issues)

    def test_validate_duplicate_capability_inputs(
        self, validator: ContractPatchValidator, profile_ref: ModelProfileReference
    ) -> None:
        """Test error for duplicate capability inputs in add list."""
        patch = ModelContractPatch(
            extends=profile_ref,
            capability_inputs__add=[
                "http_client",
                "event_bus",
                "http_client",  # Duplicate
            ],
        )
        result = validator.validate(patch)
        assert result.is_valid is False
        assert any("DUPLICATE_LIST_ENTRIES" in str(i.code) for i in result.issues)
        assert any("http_client" in str(i.message) for i in result.issues)

    def test_validate_unique_capability_outputs_passes(
        self, validator: ContractPatchValidator, profile_ref: ModelProfileReference
    ) -> None:
        """Test that unique capability outputs pass validation."""
        patch = ModelContractPatch(
            extends=profile_ref,
            capability_outputs__add=[
                ModelCapabilityProvided(name="event_emit"),
                ModelCapabilityProvided(name="http_response"),
                ModelCapabilityProvided(name="file_write"),
            ],
        )
        result = validator.validate(patch)
        assert result.is_valid is True
        assert not any("DUPLICATE_LIST_ENTRIES" in str(i.code) for i in result.issues)

    def test_validate_unique_capability_inputs_passes(
        self, validator: ContractPatchValidator, profile_ref: ModelProfileReference
    ) -> None:
        """Test that unique capability inputs pass validation."""
        patch = ModelContractPatch(
            extends=profile_ref,
            capability_inputs__add=[
                "http_client",
                "event_bus",
                "logger",
            ],
        )
        result = validator.validate(patch)
        assert result.is_valid is True
        assert not any("DUPLICATE_LIST_ENTRIES" in str(i.code) for i in result.issues)

    def test_validate_multiple_duplicate_capabilities(
        self, validator: ContractPatchValidator, profile_ref: ModelProfileReference
    ) -> None:
        """Test detection of multiple different duplicates."""
        patch = ModelContractPatch(
            extends=profile_ref,
            capability_outputs__add=[
                ModelCapabilityProvided(name="cap_a"),
                ModelCapabilityProvided(name="cap_b"),
                ModelCapabilityProvided(name="cap_a"),  # Duplicate 1
                ModelCapabilityProvided(name="cap_c"),
                ModelCapabilityProvided(name="cap_b"),  # Duplicate 2
            ],
        )
        result = validator.validate(patch)
        assert result.is_valid is False
        assert any("DUPLICATE_LIST_ENTRIES" in str(i.code) for i in result.issues)
        # Both duplicates should be reported
        assert any("cap_a" in str(i.message) for i in result.issues)
        assert any("cap_b" in str(i.message) for i in result.issues)
