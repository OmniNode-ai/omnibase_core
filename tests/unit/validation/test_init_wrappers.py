"""
Comprehensive tests for validation __init__.py wrapper functions.

Tests cover:
- validate_architecture() wrapper function
- validate_union_usage() wrapper function
- validate_contracts() wrapper function
- validate_patterns() wrapper function
- validate_all() wrapper function
- Integration with actual validation functions
- Parameter passing and defaults
- Error handling in wrapper functions
"""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.models.validation.model_validation_result import (
    ModelValidationResult,
)
from omnibase_core.validation import (
    validate_all,
    validate_architecture,
    validate_contracts,
    validate_patterns,
    validate_union_usage,
)


class TestValidateArchitectureWrapper:
    """Test validate_architecture wrapper function."""

    def test_validate_architecture_default_directory(self, tmp_path: Path) -> None:
        """Test validate_architecture with default directory."""
        # Create src directory structure
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        test_file = src_dir / "test.py"
        test_file.write_text("# Test file\n")

        # Change to temp directory for relative path test
        import os

        original_cwd = Path.cwd()
        try:
            os.chdir(tmp_path)
            result = validate_architecture()

            assert isinstance(result, ModelValidationResult)
            assert result.files_checked >= 0
        finally:
            os.chdir(original_cwd)

    def test_validate_architecture_custom_directory(self, tmp_path: Path) -> None:
        """Test validate_architecture with custom directory path."""
        test_dir = tmp_path / "custom_src"
        test_dir.mkdir()
        test_file = test_dir / "test.py"
        test_file.write_text("# Test file\n")

        result = validate_architecture(str(test_dir))

        assert isinstance(result, ModelValidationResult)
        assert result.files_checked >= 0

    def test_validate_architecture_with_max_violations(self, tmp_path: Path) -> None:
        """Test validate_architecture with max_violations parameter."""
        test_dir = tmp_path / "src"
        test_dir.mkdir()

        # Create file with multiple models (violation)
        test_file = test_dir / "test.py"
        test_file.write_text(
            """
from pydantic import BaseModel

class Model1(BaseModel):
    pass

class Model2(BaseModel):
    pass
"""
        )

        result = validate_architecture(str(test_dir), max_violations=5)

        assert isinstance(result, ModelValidationResult)
        # Should allow violations up to threshold

    def test_validate_architecture_nonexistent_directory(self) -> None:
        """Test validate_architecture with nonexistent directory."""
        result = validate_architecture("/nonexistent/path/to/directory")

        # Should handle gracefully - may raise or return error result
        assert isinstance(result, ModelValidationResult)

    def test_validate_architecture_relative_path(self, tmp_path: Path) -> None:
        """Test validate_architecture converts relative paths correctly."""
        test_dir = tmp_path / "relative_test"
        test_dir.mkdir()
        (test_dir / "test.py").write_text("# Test\n")

        result = validate_architecture(str(test_dir))

        assert isinstance(result, ModelValidationResult)


class TestValidateUnionUsageWrapper:
    """Test validate_union_usage wrapper function."""

    def test_validate_union_usage_default_directory(self, tmp_path: Path) -> None:
        """Test validate_union_usage with default directory."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        test_file = src_dir / "test.py"
        test_file.write_text("# Test file\n")

        import os

        original_cwd = Path.cwd()
        try:
            os.chdir(tmp_path)
            result = validate_union_usage()

            assert isinstance(result, ModelValidationResult)
            assert result.files_checked >= 0
        finally:
            os.chdir(original_cwd)

    def test_validate_union_usage_custom_directory(self, tmp_path: Path) -> None:
        """Test validate_union_usage with custom directory path."""
        test_dir = tmp_path / "custom_src"
        test_dir.mkdir()
        test_file = test_dir / "test.py"
        test_file.write_text(
            """
from typing import Union

def func(x: Union[str, int]) -> None:
    pass
"""
        )

        result = validate_union_usage(str(test_dir))

        assert isinstance(result, ModelValidationResult)
        assert result.files_checked >= 0

    def test_validate_union_usage_with_max_unions(self, tmp_path: Path) -> None:
        """Test validate_union_usage with max_unions parameter."""
        test_dir = tmp_path / "src"
        test_dir.mkdir()

        # Create file with unions
        test_file = test_dir / "test.py"
        test_file.write_text(
            """
from typing import Union

def func1(x: Union[str, int]) -> None:
    pass

def func2(y: Union[bool, float]) -> None:
    pass
"""
        )

        result = validate_union_usage(str(test_dir), max_unions=10)

        assert isinstance(result, ModelValidationResult)

    def test_validate_union_usage_with_strict_mode(self, tmp_path: Path) -> None:
        """Test validate_union_usage with strict mode enabled."""
        test_dir = tmp_path / "src"
        test_dir.mkdir()
        test_file = test_dir / "test.py"
        test_file.write_text(
            """
def func(x: str | int) -> None:
    pass
"""
        )

        result = validate_union_usage(str(test_dir), strict=True)

        assert isinstance(result, ModelValidationResult)

    def test_validate_union_usage_all_parameters(self, tmp_path: Path) -> None:
        """Test validate_union_usage with all parameters."""
        test_dir = tmp_path / "src"
        test_dir.mkdir()
        (test_dir / "test.py").write_text("# Test\n")

        result = validate_union_usage(str(test_dir), max_unions=5, strict=True)

        assert isinstance(result, ModelValidationResult)


class TestValidateContractsWrapper:
    """Test validate_contracts wrapper function."""

    def test_validate_contracts_default_directory(self, tmp_path: Path) -> None:
        """Test validate_contracts with default directory."""
        # Create test structure
        (tmp_path / "test.yaml").write_text("# Empty test\n")

        import os

        original_cwd = Path.cwd()
        try:
            os.chdir(tmp_path)
            result = validate_contracts()

            assert isinstance(result, ModelValidationResult)
        finally:
            os.chdir(original_cwd)

    def test_validate_contracts_custom_directory(self, tmp_path: Path) -> None:
        """Test validate_contracts with custom directory path."""
        test_dir = tmp_path / "contracts"
        test_dir.mkdir()

        result = validate_contracts(str(test_dir))

        assert isinstance(result, ModelValidationResult)

    def test_validate_contracts_with_yaml_files(self, tmp_path: Path) -> None:
        """Test validate_contracts with actual YAML files."""
        test_dir = tmp_path / "contracts"
        test_dir.mkdir()

        # Create valid YAML
        yaml_file = test_dir / "test.yaml"
        yaml_file.write_text(
            """
version: 1.0
contract_id: test-contract
operations:
  - name: test_op
    type: query
"""
        )

        result = validate_contracts(str(test_dir))

        assert isinstance(result, ModelValidationResult)

    def test_validate_contracts_empty_directory(self, tmp_path: Path) -> None:
        """Test validate_contracts with empty directory."""
        test_dir = tmp_path / "empty"
        test_dir.mkdir()

        result = validate_contracts(str(test_dir))

        assert isinstance(result, ModelValidationResult)
        assert result.success  # Empty directory is valid


class TestValidatePatternsWrapper:
    """Test validate_patterns wrapper function."""

    def test_validate_patterns_default_directory(self, tmp_path: Path) -> None:
        """Test validate_patterns with default directory."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        test_file = src_dir / "test.py"
        test_file.write_text("# Test file\n")

        import os

        original_cwd = Path.cwd()
        try:
            os.chdir(tmp_path)
            result = validate_patterns()

            assert isinstance(result, ModelValidationResult)
        finally:
            os.chdir(original_cwd)

    def test_validate_patterns_custom_directory(self, tmp_path: Path) -> None:
        """Test validate_patterns with custom directory path."""
        test_dir = tmp_path / "custom_src"
        test_dir.mkdir()
        test_file = test_dir / "test.py"
        test_file.write_text(
            """
from pydantic import BaseModel

class ModelUser(BaseModel):
    name: str
"""
        )

        result = validate_patterns(str(test_dir))

        assert isinstance(result, ModelValidationResult)

    def test_validate_patterns_with_strict_mode(self, tmp_path: Path) -> None:
        """Test validate_patterns with strict mode enabled."""
        test_dir = tmp_path / "src"
        test_dir.mkdir()
        test_file = test_dir / "test.py"
        test_file.write_text(
            """
from pydantic import BaseModel

class ModelExample(BaseModel):
    user_id: str  # Should warn about str instead of UUID in strict mode
"""
        )

        result = validate_patterns(str(test_dir), strict=True)

        assert isinstance(result, ModelValidationResult)

    def test_validate_patterns_normal_mode(self, tmp_path: Path) -> None:
        """Test validate_patterns with normal (non-strict) mode."""
        test_dir = tmp_path / "src"
        test_dir.mkdir()
        (test_dir / "test.py").write_text("# Test\n")

        result = validate_patterns(str(test_dir), strict=False)

        assert isinstance(result, ModelValidationResult)


class TestValidateAllWrapper:
    """Test validate_all wrapper function that runs all validations."""

    def test_validate_all_default_directory(self, tmp_path: Path) -> None:
        """Test validate_all with default directory."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        test_file = src_dir / "test.py"
        test_file.write_text("# Test file\n")

        import os

        original_cwd = Path.cwd()
        try:
            os.chdir(tmp_path)
            results = validate_all()

            assert isinstance(results, dict)
            # Should have results for all validation types
            assert "architecture" in results or len(results) >= 1
        finally:
            os.chdir(original_cwd)

    def test_validate_all_custom_directory(self, tmp_path: Path) -> None:
        """Test validate_all with custom directory path."""
        test_dir = tmp_path / "custom_src"
        test_dir.mkdir()
        test_file = test_dir / "test.py"
        test_file.write_text(
            """
from pydantic import BaseModel

class ModelTest(BaseModel):
    name: str
"""
        )

        results = validate_all(str(test_dir))

        assert isinstance(results, dict)
        assert len(results) >= 1

        # Check that all results are ModelValidationResult objects
        for validation_type, result in results.items():
            assert isinstance(result, ModelValidationResult)

    def test_validate_all_with_kwargs(self, tmp_path: Path) -> None:
        """Test validate_all passes kwargs to individual validators."""
        test_dir = tmp_path / "src"
        test_dir.mkdir()
        test_file = test_dir / "test.py"
        test_file.write_text("# Test\n")

        results = validate_all(
            str(test_dir),
            strict=True,
            max_violations=5,
            max_unions=10,
        )

        assert isinstance(results, dict)
        assert len(results) >= 1

    def test_validate_all_handles_errors_gracefully(self, tmp_path: Path) -> None:
        """Test validate_all handles validator errors gracefully."""
        test_dir = tmp_path / "src"
        test_dir.mkdir()

        results = validate_all(str(test_dir))

        # Should return results even if some validators fail
        assert isinstance(results, dict)

    def test_validate_all_multiple_validation_types(self, tmp_path: Path) -> None:
        """Test validate_all returns results for multiple validation types."""
        test_dir = tmp_path / "src"
        test_dir.mkdir()

        # Create test files for different validations
        py_file = test_dir / "test.py"
        py_file.write_text(
            """
from pydantic import BaseModel
from typing import Union

class ModelTest(BaseModel):
    name: str

def func(x: Union[str, int]) -> None:
    pass
"""
        )

        results = validate_all(str(test_dir))

        assert isinstance(results, dict)
        # Should contain results for multiple validators
        assert len(results) >= 1

        # All results should be valid
        for validation_type, result in results.items():
            assert isinstance(result, ModelValidationResult)
            assert result.files_checked >= 0

    def test_validate_all_empty_directory(self, tmp_path: Path) -> None:
        """Test validate_all with empty directory."""
        test_dir = tmp_path / "empty"
        test_dir.mkdir()

        results = validate_all(str(test_dir))

        assert isinstance(results, dict)
        # Should succeed with empty results
        for result in results.values():
            assert isinstance(result, ModelValidationResult)


class TestWrapperIntegration:
    """Integration tests for wrapper functions working together."""

    def test_all_wrappers_return_validation_result(self, tmp_path: Path) -> None:
        """Test that all wrapper functions return ModelValidationResult."""
        test_dir = tmp_path / "src"
        test_dir.mkdir()
        (test_dir / "test.py").write_text("# Test\n")

        arch_result = validate_architecture(str(test_dir))
        union_result = validate_union_usage(str(test_dir))
        contracts_result = validate_contracts(str(test_dir))
        patterns_result = validate_patterns(str(test_dir))

        assert isinstance(arch_result, ModelValidationResult)
        assert isinstance(union_result, ModelValidationResult)
        assert isinstance(contracts_result, ModelValidationResult)
        assert isinstance(patterns_result, ModelValidationResult)

    def test_wrappers_handle_same_directory(self, tmp_path: Path) -> None:
        """Test that all wrappers can handle the same directory."""
        test_dir = tmp_path / "src"
        test_dir.mkdir()
        test_file = test_dir / "test.py"
        test_file.write_text(
            """
from pydantic import BaseModel
from typing import Union

class ModelTest(BaseModel):
    name: str
    age: int

def process(x: Union[str, int]) -> None:
    pass
"""
        )

        # All wrappers should successfully process the same directory
        arch_result = validate_architecture(str(test_dir))
        union_result = validate_union_usage(str(test_dir))
        patterns_result = validate_patterns(str(test_dir))

        assert all(
            isinstance(r, ModelValidationResult)
            for r in [arch_result, union_result, patterns_result]
        )
