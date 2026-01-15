"""
Test suite for validation package __init__.py.

Tests that all validators and related models are properly exported
and accessible from the package level.
"""

import pytest


@pytest.mark.unit
class TestValidationPackageExports:
    """Test validation package exports."""

    def test_circular_import_validator_export(self) -> None:
        """Test that CircularImportValidator is exported."""
        from omnibase_core.validation import CircularImportValidator

        assert CircularImportValidator is not None
        assert hasattr(CircularImportValidator, "__init__")
        assert hasattr(CircularImportValidator, "validate")

    def test_model_validation_result_export(self) -> None:
        """Test that ModelImportValidationResult is exported (for circular import validation)."""
        import dataclasses

        from omnibase_core.validation import ModelImportValidationResult

        assert ModelImportValidationResult is not None
        # Verify it's a dataclass
        assert dataclasses.is_dataclass(ModelImportValidationResult)
        # Verify it has expected fields for circular import validation
        field_names = [f.name for f in dataclasses.fields(ModelImportValidationResult)]
        assert "total_files" in field_names
        # Verify it has expected methods
        assert hasattr(ModelImportValidationResult, "add_result")

    def test_general_validation_result_export(self) -> None:
        """Test that ModelValidationResult is exported (for general validation)."""
        from pydantic import BaseModel

        from omnibase_core.validation import ModelValidationResult

        assert ModelValidationResult is not None
        # Verify it's a Pydantic BaseModel
        assert issubclass(ModelValidationResult, BaseModel)
        # Verify it has expected fields for general validation
        assert hasattr(ModelValidationResult, "model_fields")
        field_names = list(ModelValidationResult.model_fields.keys())
        assert "is_valid" in field_names
        assert "errors" in field_names
        assert "summary" in field_names

    def test_model_module_import_result_export(self) -> None:
        """Test that ModelModuleImportResult is exported."""
        import dataclasses

        from omnibase_core.validation import ModelModuleImportResult

        assert ModelModuleImportResult is not None
        # Verify it's a dataclass
        assert dataclasses.is_dataclass(ModelModuleImportResult)
        # Verify it has expected fields
        field_names = [f.name for f in dataclasses.fields(ModelModuleImportResult)]
        assert "module_name" in field_names
        assert "status" in field_names

    def test_enum_import_status_export(self) -> None:
        """Test that EnumImportStatus is exported."""
        from omnibase_core.validation import EnumImportStatus

        assert EnumImportStatus is not None
        # Verify it has expected enum values
        assert hasattr(EnumImportStatus, "SUCCESS")
        assert hasattr(EnumImportStatus, "CIRCULAR_IMPORT")
        assert hasattr(EnumImportStatus, "IMPORT_ERROR")

    def test_all_exports_list(self) -> None:
        """Test that __all__ contains expected exports."""
        from omnibase_core import validation

        expected_exports = [
            "CircularImportValidator",
            "ModelValidationResult",
            "ModelModuleImportResult",
            "EnumImportStatus",
        ]

        assert hasattr(validation, "__all__")
        # CircularImportValidator should be in the validation __all__ list
        assert "CircularImportValidator" in validation.__all__
        # Check that all expected exports are in __all__
        for export in expected_exports:
            assert export in validation.__all__, (
                f"{export} not found in validation.__all__"
            )

    def test_package_imports_work(self) -> None:
        """Test that package-level imports work correctly."""
        # Test wildcard import pattern
        from omnibase_core.validation import (
            CircularImportValidator,
            EnumImportStatus,
            ModelModuleImportResult,
            ModelValidationResult,
        )

        # Verify all imports succeeded
        assert CircularImportValidator is not None
        assert EnumImportStatus is not None
        assert ModelModuleImportResult is not None
        assert ModelValidationResult is not None

    def test_validator_instantiation_from_package(self, tmp_path) -> None:
        """Test that validator can be instantiated from package import."""
        from omnibase_core.validation import CircularImportValidator

        # Should be able to create instance
        validator = CircularImportValidator(source_path=tmp_path)
        assert validator is not None
        assert validator.source_path == tmp_path
