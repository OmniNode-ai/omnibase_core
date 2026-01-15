# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Tests for ModelReference."""

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.contracts.model_reference import ModelReference
from omnibase_core.models.errors.model_onex_error import ModelOnexError


@pytest.mark.unit
class TestModelReference:
    """Tests for ModelReference model."""

    def test_valid_reference(self) -> None:
        """Test creating a valid model reference."""
        ref = ModelReference(
            module="omnibase_core.models.events",
            class_name="ModelEventEnvelope",
        )
        assert ref.module == "omnibase_core.models.events"
        assert ref.class_name == "ModelEventEnvelope"
        assert ref.version is None

    def test_reference_with_version(self) -> None:
        """Test creating a reference with version."""
        ref = ModelReference(
            module="mypackage.models",
            class_name="MyModel",
            version="1.0.0",
        )
        assert ref.version == "1.0.0"

    def test_fully_qualified_name(self) -> None:
        """Test fully qualified name property."""
        ref = ModelReference(
            module="omnibase_core.models.events",
            class_name="ModelEventEnvelope",
        )
        assert (
            ref.fully_qualified_name == "omnibase_core.models.events.ModelEventEnvelope"
        )

    def test_module_required(self) -> None:
        """Test that module is required."""
        with pytest.raises(ValidationError):
            ModelReference(class_name="MyModel")  # type: ignore[call-arg]

    def test_class_name_required(self) -> None:
        """Test that class_name is required."""
        with pytest.raises(ValidationError):
            ModelReference(module="mypackage")  # type: ignore[call-arg]

    def test_empty_module_rejected(self) -> None:
        """Test that empty module is rejected."""
        with pytest.raises(ValidationError):
            ModelReference(module="", class_name="MyModel")

    def test_empty_class_name_rejected(self) -> None:
        """Test that empty class_name is rejected."""
        with pytest.raises(ValidationError):
            ModelReference(module="mypackage", class_name="")

    def test_module_validation_valid_paths(self) -> None:
        """Test module path validation with valid paths."""
        valid_paths = [
            "mypackage",
            "mypackage.module",
            "omnibase_core.models.events",
            "_private.module",
        ]
        for path in valid_paths:
            ref = ModelReference(module=path, class_name="MyModel")
            assert ref.module == path

    def test_module_validation_invalid_paths(self) -> None:
        """Test module path validation with invalid paths."""
        invalid_paths = [
            "123invalid",  # Starts with number
            ".leading.dot",  # Starts with dot
            "trailing.",  # Trailing dot
            "double..dot",  # Double dots
        ]
        for path in invalid_paths:
            with pytest.raises(ValidationError):
                ModelReference(module=path, class_name="MyModel")

    def test_class_name_must_start_uppercase(self) -> None:
        """Test that class name must start with uppercase."""
        with pytest.raises(ValidationError) as exc_info:
            ModelReference(module="mypackage", class_name="lowercase")
        assert "uppercase" in str(exc_info.value).lower()

    def test_valid_class_names(self) -> None:
        """Test valid class name formats."""
        valid_names = [
            "MyModel",
            "ModelEventEnvelope",
            "HTTPClient",
            "Model123",
        ]
        for name in valid_names:
            ref = ModelReference(module="mypackage", class_name=name)
            assert ref.class_name == name

    def test_extra_fields_rejected(self) -> None:
        """Test that extra fields are rejected."""
        with pytest.raises(ValidationError):
            ModelReference(
                module="mypackage",
                class_name="MyModel",
                extra="not_allowed",  # type: ignore[call-arg]
            )

    def test_frozen_model(self) -> None:
        """Test that the model is immutable."""
        ref = ModelReference(module="mypackage", class_name="MyModel")
        with pytest.raises(ValidationError):
            ref.module = "changed"  # type: ignore[misc]

    def test_repr(self) -> None:
        """Test string representation."""
        ref = ModelReference(
            module="mypackage.models",
            class_name="MyModel",
            version="1.0.0",
        )
        repr_str = repr(ref)
        assert "mypackage.models.MyModel" in repr_str
        assert "1.0.0" in repr_str

    def test_repr_without_version(self) -> None:
        """Test string representation without version."""
        ref = ModelReference(module="mypackage", class_name="MyModel")
        repr_str = repr(ref)
        assert "mypackage.MyModel" in repr_str

    def test_equality(self) -> None:
        """Test equality comparison."""
        ref1 = ModelReference(module="mypackage", class_name="MyModel")
        ref2 = ModelReference(module="mypackage", class_name="MyModel")
        ref3 = ModelReference(module="mypackage", class_name="OtherModel")
        assert ref1 == ref2
        assert ref1 != ref3

    def test_from_dict(self) -> None:
        """Test creating from dictionary."""
        data = {
            "module": "mypackage.models",
            "class_name": "MyModel",
            "version": "1.0.0",
        }
        ref = ModelReference.model_validate(data)
        assert ref.module == "mypackage.models"
        assert ref.class_name == "MyModel"
        assert ref.version == "1.0.0"

    def test_whitespace_stripping(self) -> None:
        """Test that whitespace is stripped from module and class_name."""
        ref = ModelReference(
            module="  mypackage.models  ",
            class_name="  MyModel  ",
        )
        assert ref.module == "mypackage.models"
        assert ref.class_name == "MyModel"


@pytest.mark.unit
class TestModelReferenceResolveImport:
    """Tests for ModelReference.resolve_import classmethod."""

    def test_resolve_valid_reference(self) -> None:
        """Test resolving a valid module/class reference."""
        # Use a known class from the codebase
        result = ModelReference.resolve_import(
            "omnibase_core.models.contracts.model_reference.ModelReference"
        )
        assert result is ModelReference

    def test_resolve_builtin_types(self) -> None:
        """Test resolving references to trusted omnibase types."""
        # Use an omnibase_core type (pydantic.BaseModel is blocked by allowlist)
        result = ModelReference.resolve_import(
            "omnibase_core.models.errors.model_onex_error.ModelOnexError"
        )
        assert result is ModelOnexError

    def test_resolve_nested_module(self) -> None:
        """Test resolving a class from a nested module."""
        result = ModelReference.resolve_import(
            "omnibase_core.enums.enum_core_error_code.EnumCoreErrorCode"
        )
        assert result is EnumCoreErrorCode

    def test_resolve_nonexistent_module(self) -> None:
        """Test that nonexistent module returns None."""
        result = ModelReference.resolve_import("nonexistent.module.SomeClass")
        assert result is None

    def test_resolve_nonexistent_class(self) -> None:
        """Test that nonexistent class in existing module returns None."""
        result = ModelReference.resolve_import(
            "omnibase_core.models.contracts.model_reference.NonexistentClass"
        )
        assert result is None

    def test_resolve_empty_reference(self) -> None:
        """Test that empty reference returns None."""
        assert ModelReference.resolve_import("") is None

    def test_resolve_no_separator(self) -> None:
        """Test that reference without dot returns None."""
        assert ModelReference.resolve_import("nodot") is None

    def test_resolve_single_module(self) -> None:
        """Test resolving from a nested module with allowed prefix."""
        # Use an omnibase_core enum (os.path is blocked by allowlist)
        result = ModelReference.resolve_import(
            "omnibase_core.enums.enum_core_error_code.EnumCoreErrorCode"
        )
        assert result is EnumCoreErrorCode

    def test_resolve_with_invalid_module_path(self) -> None:
        """Test that malformed module path returns None gracefully."""
        # Double dots, which would cause import errors
        result = ModelReference.resolve_import("omnibase_core..models.SomeClass")
        assert result is None


@pytest.mark.unit
class TestModelReferenceResolveImportOrRaise:
    """Tests for ModelReference.resolve_import_or_raise classmethod."""

    def test_resolve_valid_reference(self) -> None:
        """Test resolving a valid reference returns the class."""
        result = ModelReference.resolve_import_or_raise(
            "omnibase_core.models.contracts.model_reference.ModelReference"
        )
        assert result is ModelReference

    def test_resolve_empty_reference_raises(self) -> None:
        """Test that empty reference raises ModelOnexError."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelReference.resolve_import_or_raise("")
        assert exc_info.value.error_code == EnumCoreErrorCode.IMPORT_ERROR
        assert "empty" in exc_info.value.message.lower()

    def test_resolve_no_separator_raises(self) -> None:
        """Test that reference without dot raises ModelOnexError."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelReference.resolve_import_or_raise("nodot")
        assert exc_info.value.error_code == EnumCoreErrorCode.IMPORT_ERROR
        assert "module.class" in exc_info.value.message.lower()

    def test_resolve_nonexistent_module_raises(self) -> None:
        """Test that nonexistent module in allowlist raises with MODULE_NOT_FOUND."""
        # Use a module with allowed prefix that doesn't exist
        with pytest.raises(ModelOnexError) as exc_info:
            ModelReference.resolve_import_or_raise(
                "omnibase_core.nonexistent_module.SomeClass"
            )
        assert exc_info.value.error_code == EnumCoreErrorCode.MODULE_NOT_FOUND
        assert "module not found" in exc_info.value.message.lower()

    def test_resolve_nonexistent_class_raises(self) -> None:
        """Test that nonexistent class raises with IMPORT_ERROR."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelReference.resolve_import_or_raise(
                "omnibase_core.models.contracts.model_reference.NonexistentClass"
            )
        assert exc_info.value.error_code == EnumCoreErrorCode.IMPORT_ERROR
        assert "not found in module" in exc_info.value.message.lower()

    def test_error_context_includes_reference(self) -> None:
        """Test that error context includes the original reference."""
        # Use a module with allowed prefix that doesn't exist
        with pytest.raises(ModelOnexError) as exc_info:
            ModelReference.resolve_import_or_raise(
                "omnibase_core.nonexistent_module.SomeClass"
            )
        # Context is stored in the error's model, check in the serialized form
        error_data = exc_info.value.model_dump()
        assert (
            error_data["context"]["reference"]
            == "omnibase_core.nonexistent_module.SomeClass"
        )
        assert (
            error_data["context"]["module_path"] == "omnibase_core.nonexistent_module"
        )


@pytest.mark.unit
class TestModelReferenceInstanceResolve:
    """Tests for ModelReference instance resolve methods."""

    def test_resolve_valid_instance(self) -> None:
        """Test resolving a valid ModelReference instance."""
        ref = ModelReference(
            module="omnibase_core.models.contracts.model_reference",
            class_name="ModelReference",
        )
        result = ref.resolve()
        assert result is ModelReference

    def test_resolve_invalid_instance(self) -> None:
        """Test that invalid instance returns None."""
        ref = ModelReference(
            module="nonexistent.module",
            class_name="SomeClass",
        )
        result = ref.resolve()
        assert result is None

    def test_resolve_or_raise_valid_instance(self) -> None:
        """Test resolve_or_raise with valid ModelReference instance."""
        ref = ModelReference(
            module="omnibase_core.models.contracts.model_reference",
            class_name="ModelReference",
        )
        result = ref.resolve_or_raise()
        assert result is ModelReference

    def test_resolve_or_raise_invalid_module(self) -> None:
        """Test resolve_or_raise raises for nonexistent module in allowlist."""
        # Use a module with allowed prefix that doesn't exist
        ref = ModelReference(
            module="omnibase_core.nonexistent_module",
            class_name="SomeClass",
        )
        with pytest.raises(ModelOnexError) as exc_info:
            ref.resolve_or_raise()
        assert exc_info.value.error_code == EnumCoreErrorCode.MODULE_NOT_FOUND

    def test_resolve_or_raise_invalid_class(self) -> None:
        """Test resolve_or_raise raises for invalid class in valid module."""
        ref = ModelReference(
            module="omnibase_core.models.contracts.model_reference",
            class_name="NonexistentClass",
        )
        with pytest.raises(ModelOnexError) as exc_info:
            ref.resolve_or_raise()
        assert exc_info.value.error_code == EnumCoreErrorCode.IMPORT_ERROR

    def test_resolve_uses_fully_qualified_name(self) -> None:
        """Test that resolve uses the fully_qualified_name property."""
        # Use an omnibase_core type (pydantic is blocked by allowlist)
        ref = ModelReference(
            module="omnibase_core.models.errors.model_onex_error",
            class_name="ModelOnexError",
        )
        result = ref.resolve()
        assert result is ModelOnexError
        # Verify fully_qualified_name is correct
        assert (
            ref.fully_qualified_name
            == "omnibase_core.models.errors.model_onex_error.ModelOnexError"
        )

    def test_resolve_real_world_model(self) -> None:
        """Test resolving a real-world model from the codebase."""
        ref = ModelReference(
            module="omnibase_core.enums.enum_core_error_code",
            class_name="EnumCoreErrorCode",
        )
        result = ref.resolve()
        assert result is EnumCoreErrorCode

    def test_resolve_with_version_ignores_version(self) -> None:
        """Test that version field does not affect resolution."""
        ref = ModelReference(
            module="omnibase_core.models.contracts.model_reference",
            class_name="ModelReference",
            version="1.0.0",
        )
        result = ref.resolve()
        assert result is ModelReference


@pytest.mark.unit
class TestModelReferenceAllowlistSecurity:
    """Tests for ModelReference allowlist security feature."""

    @pytest.mark.unit
    def test_untrusted_module_returns_none(self) -> None:
        """Test that untrusted modules return None from resolve_import()."""
        # These modules are not in ALLOWED_MODULE_PREFIXES
        untrusted_modules = [
            "os.path",
            "pydantic.BaseModel",
            "sys.exit",
            "subprocess.run",
            "importlib.import_module",
        ]
        for reference in untrusted_modules:
            result = ModelReference.resolve_import(reference)
            assert result is None, f"Expected None for untrusted module: {reference}"

    @pytest.mark.unit
    def test_untrusted_module_raises_import_error(self) -> None:
        """Test that untrusted modules raise IMPORT_ERROR from resolve_import_or_raise()."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelReference.resolve_import_or_raise("os.path.join")
        assert exc_info.value.error_code == EnumCoreErrorCode.IMPORT_ERROR
        assert "not in the allowlist" in exc_info.value.message

    @pytest.mark.unit
    def test_untrusted_instance_resolve_returns_none(self) -> None:
        """Test that ModelReference instance with untrusted module returns None."""
        ref = ModelReference(
            module="pydantic",
            class_name="BaseModel",
        )
        result = ref.resolve()
        assert result is None

    @pytest.mark.unit
    def test_untrusted_instance_resolve_or_raise_raises(self) -> None:
        """Test that ModelReference instance with untrusted module raises IMPORT_ERROR."""
        ref = ModelReference(
            module="pydantic",
            class_name="BaseModel",
        )
        with pytest.raises(ModelOnexError) as exc_info:
            ref.resolve_or_raise()
        assert exc_info.value.error_code == EnumCoreErrorCode.IMPORT_ERROR
        assert "not in the allowlist" in exc_info.value.message

    @pytest.mark.unit
    def test_allowed_prefixes_work(self) -> None:
        """Test that all allowed module prefixes can be resolved."""
        # All ALLOWED_MODULE_PREFIXES should work for valid modules
        from omnibase_core.models.contracts.model_reference import (
            ALLOWED_MODULE_PREFIXES,
        )

        # Test that omnibase_core prefix works (we know this module exists)
        assert "omnibase_core." in ALLOWED_MODULE_PREFIXES
        result = ModelReference.resolve_import(
            "omnibase_core.models.contracts.model_reference.ModelReference"
        )
        assert result is ModelReference

    @pytest.mark.unit
    def test_error_message_includes_allowed_prefixes(self) -> None:
        """Test that error message includes allowed prefixes for debugging."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelReference.resolve_import_or_raise("os.path.join")
        # Error message should help developers understand which prefixes are allowed
        assert "omnibase_core" in exc_info.value.message
