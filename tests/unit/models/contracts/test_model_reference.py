# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Tests for ModelReference."""

import pytest
from pydantic import ValidationError

from omnibase_core.models.contracts.model_reference import ModelReference


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
