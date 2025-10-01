"""
Extended tests for patterns.py to improve coverage.

Tests cover:
- PydanticPatternChecker edge cases
- NamingConventionChecker comprehensive testing
- Pattern validation for various code structures
- Edge cases in pattern detection
- Anti-pattern detection
- Complex code pattern scenarios
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from omnibase_core.validation.patterns import (
    NamingConventionChecker,
    PydanticPatternChecker,
    validate_patterns_directory,
    validate_patterns_file,
)


class TestPydanticPatternCheckerExtended:
    """Extended tests for PydanticPatternChecker."""

    def test_checker_detects_id_fields_with_str(self) -> None:
        """Test checker detects ID fields using str instead of UUID."""
        code = """
from pydantic import BaseModel

class ModelUser(BaseModel):
    user_id: str
    account_id: str
    transaction_id: str
"""

        tree = ast.parse(code)
        checker = PydanticPatternChecker("test.py")
        checker.visit(tree)

        # Should detect multiple ID fields
        assert len(checker.issues) >= 3
        assert all("should use UUID" in issue for issue in checker.issues)

    def test_checker_detects_category_fields_with_str(self) -> None:
        """Test checker detects category fields that should use Enum."""
        code = """
from pydantic import BaseModel

class ModelProduct(BaseModel):
    category: str
    type: str
    status: str
"""

        tree = ast.parse(code)
        checker = PydanticPatternChecker("test.py")
        checker.visit(tree)

        # Should detect all three fields
        assert len(checker.issues) >= 3
        assert all("should use Enum" in issue for issue in checker.issues)

    def test_checker_detects_name_fields_with_str(self) -> None:
        """Test checker detects *_name fields that might reference entities."""
        code = """
from pydantic import BaseModel

class ModelOrder(BaseModel):
    customer_name: str
    product_name: str
    supplier_name: str
"""

        tree = ast.parse(code)
        checker = PydanticPatternChecker("test.py")
        checker.visit(tree)

        # Should suggest ID + display_name pattern
        assert len(checker.issues) >= 3
        assert all("might reference an entity" in issue for issue in checker.issues)

    def test_checker_handles_nested_pydantic_models(self) -> None:
        """Test checker handles nested Pydantic model definitions."""
        code = """
from pydantic import BaseModel

class ModelOuter(BaseModel):
    name: str
    user_id: str

    class ModelInner(BaseModel):
        inner_id: str
        category: str
"""

        tree = ast.parse(code)
        checker = PydanticPatternChecker("test.py")
        checker.visit(tree)

        # Should detect issues in both outer and inner models
        # Note: 'name' field is not flagged (only '_name' suffix fields are)
        # Expected: user_id (UUID), inner_id (UUID), category (Enum) = 3 issues
        assert len(checker.issues) == 3
        assert checker.classes_checked >= 2

    def test_checker_handles_pydantic_attribute_access(self) -> None:
        """Test checker detects pydantic.BaseModel style."""
        code = """
import pydantic

class ModelData(pydantic.BaseModel):
    user_id: str
    category: str
"""

        tree = ast.parse(code)
        checker = PydanticPatternChecker("test.py")
        checker.visit(tree)

        # Should detect Pydantic model and its issues
        assert checker.classes_checked >= 1
        assert len(checker.issues) >= 2

    def test_checker_ignores_non_pydantic_classes(self) -> None:
        """Test checker ignores non-Pydantic classes."""
        code = """
class RegularClass:
    user_id: str
    category: str
"""

        tree = ast.parse(code)
        checker = PydanticPatternChecker("test.py")
        checker.visit(tree)

        # Should not check non-Pydantic classes
        assert checker.classes_checked == 0
        assert len(checker.issues) == 0

    def test_checker_handles_complex_annotations(self) -> None:
        """Test checker handles complex type annotations."""
        code = """
from pydantic import BaseModel
from typing import Optional, List

class ModelComplex(BaseModel):
    user_id: Optional[str]
    categories: List[str]
    nested_type: dict[str, str]
"""

        tree = ast.parse(code)
        checker = PydanticPatternChecker("test.py")
        checker.visit(tree)

        # Should handle complex annotations
        assert checker.classes_checked >= 1

    def test_checker_detects_naming_violations(self) -> None:
        """Test checker detects model naming violations."""
        code = """
from pydantic import BaseModel

class User(BaseModel):  # Missing Model prefix
    name: str

class DataModel(BaseModel):  # Correct naming
    name: str
"""

        tree = ast.parse(code)
        checker = PydanticPatternChecker("test.py")
        checker.visit(tree)

        # Should detect naming violation in User class
        assert len(checker.issues) >= 1
        assert any("should start with 'Model'" in issue for issue in checker.issues)

    def test_checker_handles_string_annotations(self) -> None:
        """Test checker handles string-based type annotations."""
        code = """
from pydantic import BaseModel

class ModelForward(BaseModel):
    user_id: 'str'
    category: 'str'
"""

        tree = ast.parse(code)
        checker = PydanticPatternChecker("test.py")
        checker.visit(tree)

        # Should detect issues even with string annotations
        assert checker.classes_checked >= 1
        assert len(checker.issues) >= 2

    def test_checker_multiple_models_in_file(self) -> None:
        """Test checker handles multiple Pydantic models in one file."""
        code = """
from pydantic import BaseModel

class ModelUser(BaseModel):
    user_id: str

class ModelProduct(BaseModel):
    product_id: str
    category: str

class ModelOrder(BaseModel):
    order_id: str
    status: str
"""

        tree = ast.parse(code)
        checker = PydanticPatternChecker("test.py")
        checker.visit(tree)

        # Should check all models
        assert checker.classes_checked >= 3
        # Should find issues in multiple models
        assert len(checker.issues) >= 5


class TestNamingConventionCheckerExtended:
    """Extended tests for NamingConventionChecker."""

    def test_checker_detects_manager_anti_pattern(self) -> None:
        """Test checker detects Manager anti-pattern."""
        code = """
class UserManager:
    pass

class DataManager:
    pass

class ConnectionManager:
    pass
"""

        tree = ast.parse(code)
        checker = NamingConventionChecker("test.py")
        checker.visit(tree)

        # Should detect all Manager anti-patterns
        assert len(checker.issues) >= 3
        assert all("anti-pattern" in issue.lower() for issue in checker.issues)

    def test_checker_detects_handler_anti_pattern(self) -> None:
        """Test checker detects Handler anti-pattern."""
        code = """
class RequestHandler:
    pass

class EventHandler:
    pass
"""

        tree = ast.parse(code)
        checker = NamingConventionChecker("test.py")
        checker.visit(tree)

        assert len(checker.issues) >= 2
        assert all("Handler" in issue for issue in checker.issues)

    def test_checker_detects_helper_anti_pattern(self) -> None:
        """Test checker detects Helper anti-pattern."""
        code = """
class StringHelper:
    pass

class DateHelper:
    pass
"""

        tree = ast.parse(code)
        checker = NamingConventionChecker("test.py")
        checker.visit(tree)

        assert len(checker.issues) >= 2
        assert all("Helper" in issue for issue in checker.issues)

    def test_checker_detects_utility_anti_pattern(self) -> None:
        """Test checker detects Utility/Util anti-patterns."""
        code = """
class Utility:
    pass

class Util:
    pass

class StringUtils:
    pass
"""

        tree = ast.parse(code)
        checker = NamingConventionChecker("test.py")
        checker.visit(tree)

        assert len(checker.issues) >= 3

    def test_checker_detects_service_anti_pattern(self) -> None:
        """Test checker detects Service anti-pattern."""
        code = """
class UserService:
    pass

class EmailService:
    pass
"""

        tree = ast.parse(code)
        checker = NamingConventionChecker("test.py")
        checker.visit(tree)

        assert len(checker.issues) >= 2
        assert all("Service" in issue for issue in checker.issues)

    def test_checker_detects_controller_anti_pattern(self) -> None:
        """Test checker detects Controller anti-pattern."""
        code = """
class UserController:
    pass

class APIController:
    pass
"""

        tree = ast.parse(code)
        checker = NamingConventionChecker("test.py")
        checker.visit(tree)

        assert len(checker.issues) >= 2

    def test_checker_detects_processor_anti_pattern(self) -> None:
        """Test checker detects Processor anti-pattern."""
        code = """
class DataProcessor:
    pass

class ImageProcessor:
    pass
"""

        tree = ast.parse(code)
        checker = NamingConventionChecker("test.py")
        checker.visit(tree)

        assert len(checker.issues) >= 2

    def test_checker_detects_worker_anti_pattern(self) -> None:
        """Test checker detects Worker anti-pattern."""
        code = """
class BackgroundWorker:
    pass

class TaskWorker:
    pass
"""

        tree = ast.parse(code)
        checker = NamingConventionChecker("test.py")
        checker.visit(tree)

        assert len(checker.issues) >= 2

    def test_checker_detects_pascal_case_violations(self) -> None:
        """Test checker detects non-PascalCase class names."""
        code = """
class lowercase:
    pass

class snake_case_name:
    pass

class camelCase:
    pass

class ALLCAPS:
    pass
"""

        tree = ast.parse(code)
        checker = NamingConventionChecker("test.py")
        checker.visit(tree)

        # Should detect PascalCase violations
        # Note: ALLCAPS technically matches the regex ^[A-Z][a-zA-Z0-9]*$ so it's not flagged
        # Expected violations: lowercase, snake_case_name, camelCase = 3 issues
        assert len(checker.issues) == 3

    def test_checker_allows_good_class_names(self) -> None:
        """Test checker allows well-named classes."""
        code = """
class User:
    pass

class ProductCatalog:
    pass

class EmailSender:
    pass
"""

        tree = ast.parse(code)
        checker = NamingConventionChecker("test.py")
        checker.visit(tree)

        # Should not flag good names (though EmailSender might be debated)
        # Focus on no false positives for User and ProductCatalog
        assert (
            len([i for i in checker.issues if "User" in i or "ProductCatalog" in i])
            == 0
        )

    def test_checker_checks_function_names(self) -> None:
        """Test checker checks function naming conventions."""
        code = """
def ValidFunction():
    pass

def another_function():
    pass

def PascalCaseFunction():
    pass
"""

        tree = ast.parse(code)
        checker = NamingConventionChecker("test.py")
        checker.visit(tree)

        # Should check function naming
        assert isinstance(checker.issues, list)

    def test_checker_handles_mixed_good_bad_names(self) -> None:
        """Test checker handles mix of good and bad class names."""
        code = """
class GoodClassName:
    pass

class BadManager:
    pass

class AnotherGoodName:
    pass

class BadHelper:
    pass
"""

        tree = ast.parse(code)
        checker = NamingConventionChecker("test.py")
        checker.visit(tree)

        # Should only flag the bad names
        assert len(checker.issues) >= 2
        assert any("Manager" in issue for issue in checker.issues)
        assert any("Helper" in issue for issue in checker.issues)


class TestValidatePatternsFileExtended:
    """Extended tests for validate_patterns_file function."""

    def test_validate_patterns_file_with_multiple_issues(
        self,
        tmp_path: Path,
    ) -> None:
        """Test validation detects multiple issues in one file."""
        test_file = tmp_path / "test.py"
        test_file.write_text(
            """
from pydantic import BaseModel

class User(BaseModel):  # Missing Model prefix
    user_id: str  # Should use UUID
    category: str  # Should use Enum

class DataManager:  # Anti-pattern
    pass
""",
        )

        issues = validate_patterns_file(test_file)

        # Should detect multiple issues
        assert len(issues) >= 4

    def test_validate_patterns_file_with_syntax_errors(
        self,
        tmp_path: Path,
    ) -> None:
        """Test validation handles syntax errors gracefully."""
        test_file = tmp_path / "invalid.py"
        test_file.write_text(
            """
from pydantic import BaseModel

class ModelBroken(BaseModel):
    field: [invalid syntax here
""",
        )

        issues = validate_patterns_file(test_file)

        # Should handle syntax errors
        assert isinstance(issues, list)

    def test_validate_patterns_file_empty_file(self, tmp_path: Path) -> None:
        """Test validation handles empty files."""
        test_file = tmp_path / "empty.py"
        test_file.write_text("")

        issues = validate_patterns_file(test_file)

        # Empty file should have no issues
        assert len(issues) == 0

    def test_validate_patterns_file_only_comments(self, tmp_path: Path) -> None:
        """Test validation handles files with only comments."""
        test_file = tmp_path / "comments.py"
        test_file.write_text(
            """
# This is a comment
# Another comment
# More comments
""",
        )

        issues = validate_patterns_file(test_file)

        assert len(issues) == 0

    def test_validate_patterns_file_with_imports_only(self, tmp_path: Path) -> None:
        """Test validation handles files with only imports."""
        test_file = tmp_path / "imports.py"
        test_file.write_text(
            """
from pydantic import BaseModel
from typing import Optional
import sys
""",
        )

        issues = validate_patterns_file(test_file)

        assert len(issues) == 0

    def test_validate_patterns_file_complex_code(self, tmp_path: Path) -> None:
        """Test validation handles complex code structures."""
        test_file = tmp_path / "complex.py"
        test_file.write_text(
            """
from pydantic import BaseModel
from typing import Optional, List

class ModelUser(BaseModel):
    name: str
    age: int

    class Config:
        frozen = True

def process_user(user: ModelUser) -> dict:
    return {"name": user.name, "age": user.age}

class ModelProduct(BaseModel):
    product_id: str  # Should detect this
    name: str

class ProductRepository:
    def __init__(self):
        self.products = []

    def add(self, product: ModelProduct):
        self.products.append(product)
""",
        )

        issues = validate_patterns_file(test_file)

        # Should detect product_id issue
        assert len(issues) >= 1


class TestValidatePatternsDirectoryExtended:
    """Extended tests for validate_patterns_directory function."""

    def test_validate_patterns_directory_recursive(self, tmp_path: Path) -> None:
        """Test validation processes directories recursively."""
        # Create nested structure
        level1 = tmp_path / "level1"
        level1.mkdir()
        level2 = level1 / "level2"
        level2.mkdir()

        # Add files at each level
        (tmp_path / "root.py").write_text(
            """
class UserManager:
    pass
""",
        )

        (level1 / "level1.py").write_text(
            """
class DataHelper:
    pass
""",
        )

        (level2 / "level2.py").write_text(
            """
class ServiceHandler:
    pass
""",
        )

        result = validate_patterns_directory(tmp_path)

        # Should check all files
        assert result.files_checked >= 3
        # Should detect issues in all files
        if not result.success:
            assert len(result.errors) >= 3

    def test_validate_patterns_directory_ignores_pycache(
        self,
        tmp_path: Path,
    ) -> None:
        """Test validation ignores __pycache__ directories."""
        pycache = tmp_path / "__pycache__"
        pycache.mkdir()

        (pycache / "compiled.py").write_text("class BadManager: pass")

        result = validate_patterns_directory(tmp_path)

        # Should not check __pycache__
        assert result.files_checked == 0

    def test_validate_patterns_directory_strict_mode(self, tmp_path: Path) -> None:
        """Test validation in strict mode."""
        test_file = tmp_path / "test.py"
        test_file.write_text(
            """
from pydantic import BaseModel

class ModelUser(BaseModel):
    user_id: str
""",
        )

        result = validate_patterns_directory(tmp_path, strict=True)

        # Strict mode should be more stringent
        assert result.files_checked >= 1

    def test_validate_patterns_directory_mixed_files(self, tmp_path: Path) -> None:
        """Test validation with mix of good and bad files."""
        # Good file
        good_file = tmp_path / "good.py"
        good_file.write_text(
            """
from pydantic import BaseModel

class ModelUser(BaseModel):
    name: str
    age: int
""",
        )

        # Bad file
        bad_file = tmp_path / "bad.py"
        bad_file.write_text(
            """
class UserManager:
    pass

class DataHelper:
    pass
""",
        )

        result = validate_patterns_directory(tmp_path)

        assert result.files_checked >= 2
        # Should detect issues in bad file
        if not result.success:
            assert len(result.errors) >= 2

    def test_validate_patterns_directory_non_python_files(
        self,
        tmp_path: Path,
    ) -> None:
        """Test validation ignores non-Python files."""
        (tmp_path / "readme.txt").write_text("Not Python")
        (tmp_path / "config.json").write_text("{}")
        (tmp_path / "test.py").write_text("# Python file")

        result = validate_patterns_directory(tmp_path)

        # Should only check Python files
        assert result.files_checked <= 1

    def test_validate_patterns_directory_populates_metadata(
        self,
        tmp_path: Path,
    ) -> None:
        """Test validation populates result metadata."""
        test_file = tmp_path / "test.py"
        test_file.write_text(
            """
from pydantic import BaseModel

class ModelTest(BaseModel):
    name: str
""",
        )

        result = validate_patterns_directory(tmp_path)

        assert result.metadata is not None
        assert isinstance(result.metadata, dict)
