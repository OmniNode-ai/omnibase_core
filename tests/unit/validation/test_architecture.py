"""Tests for ONEX architecture validation."""

import ast
import tempfile
from pathlib import Path

import pytest

from omnibase_core.validation.architecture import (
    ModelCounter,
    validate_architecture_directory,
    validate_one_model_per_file,
)


class TestModelCounter:
    """Test ModelCounter AST visitor."""

    def test_count_single_model(self):
        """Test counting a single model."""
        code = """
from pydantic import BaseModel

class ModelUser(BaseModel):
    name: str
"""
        tree = ast.parse(code)
        counter = ModelCounter()
        counter.visit(tree)

        assert len(counter.models) == 1
        assert "ModelUser" in counter.models
        assert len(counter.enums) == 0
        assert len(counter.protocols) == 0

    def test_count_multiple_models(self):
        """Test counting multiple models."""
        code = """
from pydantic import BaseModel

class ModelUser(BaseModel):
    name: str

class ModelPost(BaseModel):
    title: str
"""
        tree = ast.parse(code)
        counter = ModelCounter()
        counter.visit(tree)

        assert len(counter.models) == 2
        assert "ModelUser" in counter.models
        assert "ModelPost" in counter.models

    def test_count_enum(self):
        """Test counting enums."""
        code = """
from enum import Enum

class EnumStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
"""
        tree = ast.parse(code)
        counter = ModelCounter()
        counter.visit(tree)

        assert len(counter.enums) == 1
        assert "EnumStatus" in counter.enums
        assert len(counter.models) == 0

    def test_count_protocol(self):
        """Test counting protocols."""
        code = """
from typing import Protocol

class Serializable(Protocol):
    def serialize(self) -> dict:
        ...
"""
        tree = ast.parse(code)
        counter = ModelCounter()
        counter.visit(tree)

        assert len(counter.protocols) == 1
        assert "Serializable" in counter.protocols
        assert len(counter.models) == 0

    def test_count_mixed_types(self):
        """Test counting mixed types."""
        code = """
from pydantic import BaseModel
from enum import Enum
from typing import Protocol

class ModelUser(BaseModel):
    name: str

class EnumStatus(Enum):
    ACTIVE = "active"

class Serializable(Protocol):
    def serialize(self) -> dict:
        ...
"""
        tree = ast.parse(code)
        counter = ModelCounter()
        counter.visit(tree)

        assert len(counter.models) == 1
        assert len(counter.enums) == 1
        assert len(counter.protocols) == 1

    def test_detect_model_by_naming_pattern(self):
        """Test detecting models by naming pattern."""
        code = """
class ModelCustom:
    pass
"""
        tree = ast.parse(code)
        counter = ModelCounter()
        counter.visit(tree)

        assert len(counter.models) == 1
        assert "ModelCustom" in counter.models

    def test_detect_enum_by_naming_pattern(self):
        """Test detecting enums by naming pattern."""
        code = """
class EnumCustom:
    pass
"""
        tree = ast.parse(code)
        counter = ModelCounter()
        counter.visit(tree)

        assert len(counter.enums) == 1
        assert "EnumCustom" in counter.enums

    def test_detect_pydantic_basemodel_attribute(self):
        """Test detecting pydantic.BaseModel."""
        code = """
import pydantic

class ModelUser(pydantic.BaseModel):
    name: str
"""
        tree = ast.parse(code)
        counter = ModelCounter()
        counter.visit(tree)

        assert len(counter.models) == 1
        assert "ModelUser" in counter.models

    def test_type_alias_detection(self):
        """Test type alias detection."""
        code = """
from typing import TypeAlias

CustomType: TypeAlias = dict[str, str]
"""
        tree = ast.parse(code)
        counter = ModelCounter()
        counter.visit(tree)

        assert len(counter.type_aliases) == 1
        assert "CustomType" in counter.type_aliases


class TestValidateOneModelPerFile:
    """Test validate_one_model_per_file function."""

    def test_single_model_passes(self, tmp_path: Path):
        """Test single model file passes validation."""
        test_file = tmp_path / "model_user.py"
        test_file.write_text(
            """
from pydantic import BaseModel

class ModelUser(BaseModel):
    name: str
"""
        )

        errors = validate_one_model_per_file(test_file)
        assert len(errors) == 0

    def test_multiple_models_fails(self, tmp_path: Path):
        """Test multiple models fail validation."""
        test_file = tmp_path / "models.py"
        test_file.write_text(
            """
from pydantic import BaseModel

class ModelUser(BaseModel):
    name: str

class ModelPost(BaseModel):
    title: str
"""
        )

        errors = validate_one_model_per_file(test_file)
        assert len(errors) > 0
        assert any("2 models" in error for error in errors)

    def test_multiple_enums_fails(self, tmp_path: Path):
        """Test multiple enums fail validation."""
        test_file = tmp_path / "enums.py"
        test_file.write_text(
            """
from enum import Enum

class EnumStatus(Enum):
    ACTIVE = "active"

class EnumType(Enum):
    USER = "user"
"""
        )

        errors = validate_one_model_per_file(test_file)
        assert len(errors) > 0
        assert any("2 enums" in error for error in errors)

    def test_multiple_protocols_fails(self, tmp_path: Path):
        """Test multiple protocols fail validation."""
        test_file = tmp_path / "protocols.py"
        test_file.write_text(
            """
from typing import Protocol

class Serializable(Protocol):
    def serialize(self) -> dict:
        ...

class Validatable(Protocol):
    def validate(self) -> bool:
        ...
"""
        )

        errors = validate_one_model_per_file(test_file)
        assert len(errors) > 0
        assert any("2 protocols" in error for error in errors)

    def test_mixed_types_fails(self, tmp_path: Path):
        """Test mixed types fail validation."""
        test_file = tmp_path / "mixed.py"
        test_file.write_text(
            """
from pydantic import BaseModel
from enum import Enum

class ModelUser(BaseModel):
    name: str

class EnumStatus(Enum):
    ACTIVE = "active"
"""
        )

        errors = validate_one_model_per_file(test_file)
        assert len(errors) > 0
        assert any("Mixed types" in error for error in errors)

    def test_typeddict_with_model_allowed(self, tmp_path: Path):
        """Test TypedDict with model is allowed."""
        test_file = tmp_path / "model_with_typeddict.py"
        test_file.write_text(
            """
from typing import TypedDict
from pydantic import BaseModel

class UserData(TypedDict):
    name: str
    age: int

class ModelUser(BaseModel):
    data: UserData
"""
        )

        errors = validate_one_model_per_file(test_file)
        # TypedDict + Model is allowed
        assert len(errors) == 0

    def test_syntax_error_handling(self, tmp_path: Path):
        """Test handling of syntax errors."""
        test_file = tmp_path / "invalid.py"
        test_file.write_text(
            """
class Invalid(
    # Syntax error - unclosed parenthesis
"""
        )

        errors = validate_one_model_per_file(test_file)
        assert len(errors) > 0
        assert any("Syntax error" in error for error in errors)


class TestValidateArchitectureDirectory:
    """Test validate_architecture_directory function."""

    def test_empty_directory(self, tmp_path: Path):
        """Test validation of empty directory."""
        result = validate_architecture_directory(tmp_path)

        assert result.success is True
        assert result.files_checked == 0
        assert len(result.errors) == 0

    def test_directory_with_valid_files(self, tmp_path: Path):
        """Test directory with all valid files."""
        # Create valid files
        (tmp_path / "model_user.py").write_text(
            """
from pydantic import BaseModel

class ModelUser(BaseModel):
    name: str
"""
        )

        (tmp_path / "enum_status.py").write_text(
            """
from enum import Enum

class EnumStatus(Enum):
    ACTIVE = "active"
"""
        )

        result = validate_architecture_directory(tmp_path)

        assert result.success is True
        assert result.files_checked == 2
        assert len(result.errors) == 0

    def test_directory_with_violations(self, tmp_path: Path):
        """Test directory with violations."""
        # Create file with violations
        (tmp_path / "models.py").write_text(
            """
from pydantic import BaseModel

class ModelUser(BaseModel):
    name: str

class ModelPost(BaseModel):
    title: str
"""
        )

        result = validate_architecture_directory(tmp_path, max_violations=0)

        assert result.success is False
        assert result.files_checked == 1
        assert len(result.errors) > 0
        assert result.violations_found > 0

    def test_directory_with_allowed_violations(self, tmp_path: Path):
        """Test directory with violations within threshold."""
        # Create file with violations
        (tmp_path / "models.py").write_text(
            """
from pydantic import BaseModel

class ModelUser(BaseModel):
    name: str

class ModelPost(BaseModel):
    title: str
"""
        )

        result = validate_architecture_directory(tmp_path, max_violations=10)

        assert result.success is True
        assert result.files_checked == 1
        assert len(result.errors) > 0
        assert result.violations_found > 0

    def test_skips_init_files(self, tmp_path: Path):
        """Test that __init__.py files are skipped."""
        # Create __init__.py with multiple exports
        (tmp_path / "__init__.py").write_text(
            """
from .model_user import ModelUser
from .model_post import ModelPost
"""
        )

        result = validate_architecture_directory(tmp_path)

        assert result.success is True
        assert result.files_checked == 0

    def test_skips_pycache(self, tmp_path: Path):
        """Test that __pycache__ is skipped."""
        pycache_dir = tmp_path / "__pycache__"
        pycache_dir.mkdir()
        (pycache_dir / "test.py").write_text("# cached file")

        result = validate_architecture_directory(tmp_path)

        assert result.success is True
        assert result.files_checked == 0

    def test_metadata_populated(self, tmp_path: Path):
        """Test that metadata is properly populated."""
        (tmp_path / "models.py").write_text(
            """
from pydantic import BaseModel

class ModelUser(BaseModel):
    pass

class ModelPost(BaseModel):
    pass
"""
        )

        result = validate_architecture_directory(tmp_path)

        assert "validation_type" in result.metadata
        assert result.metadata["validation_type"] == "architecture"
        assert "max_violations" in result.metadata
        assert "files_with_violations" in result.metadata
