"""Tests for pattern validation."""

import ast

import pytest

from omnibase_core.validation.validator_patterns import (
    GenericPatternChecker,
    NamingConventionChecker,
    PydanticPatternChecker,
)


@pytest.mark.unit
class TestPydanticPatternChecker:
    """Test PydanticPatternChecker class."""

    def test_detect_pydantic_model_with_basemodel(self):
        """Test detection of Pydantic models."""
        code = """
from pydantic import BaseModel

class ModelUser(BaseModel):
    name: str
"""
        tree = ast.parse(code)
        checker = PydanticPatternChecker("test.py")
        checker.visit(tree)

        assert checker.classes_checked == 1
        assert len(checker.issues) == 0

    def test_detect_pydantic_model_with_pydantic_prefix(self):
        """Test detection of pydantic.BaseModel."""
        code = """
import pydantic

class ModelUser(pydantic.BaseModel):
    name: str
"""
        tree = ast.parse(code)
        checker = PydanticPatternChecker("test.py")
        checker.visit(tree)

        assert checker.classes_checked == 1

    def test_naming_convention_violation(self):
        """Test detection of naming convention violations."""
        code = """
from pydantic import BaseModel

class UserModel(BaseModel):
    name: str
"""
        tree = ast.parse(code)
        checker = PydanticPatternChecker("test.py")
        checker.visit(tree)

        assert len(checker.issues) > 0
        assert any("should start with 'Model'" in issue for issue in checker.issues)

    def test_str_id_field_violation(self):
        """Test detection of str ID fields."""
        code = """
from pydantic import BaseModel

class ModelUser(BaseModel):
    user_id: str
"""
        tree = ast.parse(code)
        checker = PydanticPatternChecker("test.py")
        checker.visit(tree)

        assert len(checker.issues) > 0
        assert any("should use UUID type" in issue for issue in checker.issues)

    def test_str_status_field_violation(self):
        """Test detection of str status fields."""
        code = """
from pydantic import BaseModel

class ModelUser(BaseModel):
    status: str
"""
        tree = ast.parse(code)
        checker = PydanticPatternChecker("test.py")
        checker.visit(tree)

        assert len(checker.issues) > 0
        assert any("should use Enum" in issue for issue in checker.issues)

    def test_str_category_field_violation(self):
        """Test detection of str category fields."""
        code = """
from pydantic import BaseModel

class ModelUser(BaseModel):
    category: str
"""
        tree = ast.parse(code)
        checker = PydanticPatternChecker("test.py")
        checker.visit(tree)

        assert len(checker.issues) > 0
        assert any("should use Enum" in issue for issue in checker.issues)

    def test_str_type_field_violation(self):
        """Test detection of str type fields."""
        code = """
from pydantic import BaseModel

class ModelUser(BaseModel):
    type: str
"""
        tree = ast.parse(code)
        checker = PydanticPatternChecker("test.py")
        checker.visit(tree)

        assert len(checker.issues) > 0
        assert any("should use Enum" in issue for issue in checker.issues)

    def test_name_field_suggestion(self):
        """Test suggestion for name fields."""
        code = """
from pydantic import BaseModel

class ModelUser(BaseModel):
    user_name: str
"""
        tree = ast.parse(code)
        checker = PydanticPatternChecker("test.py")
        checker.visit(tree)

        assert len(checker.issues) > 0
        assert any("might reference an entity" in issue for issue in checker.issues)

    def test_non_pydantic_class_skipped(self):
        """Test that non-Pydantic classes are skipped."""
        code = """
class RegularClass:
    def __init__(self):
        self.name = "test"
"""
        tree = ast.parse(code)
        checker = PydanticPatternChecker("test.py")
        checker.visit(tree)

        assert checker.classes_checked == 0

    def test_multiple_pydantic_models(self):
        """Test checking multiple Pydantic models."""
        code = """
from pydantic import BaseModel

class ModelUser(BaseModel):
    name: str

class ModelPost(BaseModel):
    title: str
"""
        tree = ast.parse(code)
        checker = PydanticPatternChecker("test.py")
        checker.visit(tree)

        assert checker.classes_checked == 2


@pytest.mark.unit
class TestNamingConventionChecker:
    """Test NamingConventionChecker class."""

    def test_anti_pattern_manager(self):
        """Test detection of Manager anti-pattern."""
        code = """
class UserManager:
    pass
"""
        tree = ast.parse(code)
        checker = NamingConventionChecker("test.py")
        checker.visit(tree)

        assert len(checker.issues) > 0
        assert any("anti-pattern" in issue.lower() for issue in checker.issues)
        assert any("Manager" in issue for issue in checker.issues)

    def test_anti_pattern_handler(self):
        """Test detection of Handler anti-pattern."""
        code = """
class EventHandler:
    pass
"""
        tree = ast.parse(code)
        checker = NamingConventionChecker("test.py")
        checker.visit(tree)

        assert len(checker.issues) > 0
        assert any("Handler" in issue for issue in checker.issues)

    def test_anti_pattern_helper(self):
        """Test detection of Helper anti-pattern."""
        code = """
class StringHelper:
    pass
"""
        tree = ast.parse(code)
        checker = NamingConventionChecker("test.py")
        checker.visit(tree)

        assert len(checker.issues) > 0
        assert any("Helper" in issue for issue in checker.issues)

    def test_anti_pattern_utility(self):
        """Test detection of Utility anti-pattern."""
        code = """
class DataUtility:
    pass
"""
        tree = ast.parse(code)
        checker = NamingConventionChecker("test.py")
        checker.visit(tree)

        assert len(checker.issues) > 0
        assert any("Utility" in issue for issue in checker.issues)

    def test_class_pascal_case_violation(self):
        """Test detection of non-PascalCase class names."""
        code = """
class invalid_class_name:
    pass
"""
        tree = ast.parse(code)
        checker = NamingConventionChecker("test.py")
        checker.visit(tree)

        assert len(checker.issues) > 0
        assert any("PascalCase" in issue for issue in checker.issues)

    def test_valid_class_name(self):
        """Test that valid class names pass."""
        code = """
class UserProfile:
    pass
"""
        tree = ast.parse(code)
        checker = NamingConventionChecker("test.py")
        checker.visit(tree)

        assert len(checker.issues) == 0

    def test_function_snake_case_violation(self):
        """Test detection of non-snake_case function names."""
        code = """
def InvalidFunctionName():
    pass
"""
        tree = ast.parse(code)
        checker = NamingConventionChecker("test.py")
        checker.visit(tree)

        assert len(checker.issues) > 0
        assert any("snake_case" in issue for issue in checker.issues)

    def test_valid_function_name(self):
        """Test that valid function names pass."""
        code = """
def get_user_profile():
    pass
"""
        tree = ast.parse(code)
        checker = NamingConventionChecker("test.py")
        checker.visit(tree)

        assert len(checker.issues) == 0

    def test_special_methods_skipped(self):
        """Test that special methods are skipped."""
        code = """
class Test:
    def __init__(self):
        pass

    def __str__(self):
        pass
"""
        tree = ast.parse(code)
        checker = NamingConventionChecker("test.py")
        checker.visit(tree)

        # Special methods should not trigger violations
        assert len(checker.issues) == 0

    def test_error_class_with_handler_allowed(self):
        """Test that error classes with 'Handler' in name are allowed."""
        code = """
class HandlerConfigurationError(Exception):
    pass
"""
        tree = ast.parse(code)
        checker = NamingConventionChecker("src/errors/infra_errors.py")
        checker.visit(tree)

        # Error classes should not trigger anti-pattern violations
        assert len(checker.issues) == 0

    def test_error_class_with_service_allowed(self):
        """Test that error classes with 'Service' in name are allowed."""
        code = """
class InfraServiceUnavailableError(Exception):
    pass
"""
        tree = ast.parse(code)
        checker = NamingConventionChecker("test.py")
        checker.visit(tree)

        # Error classes (ending in Error) should not trigger anti-pattern violations
        assert len(checker.issues) == 0

    def test_exception_class_with_handler_allowed(self):
        """Test that exception classes with 'Handler' in name are allowed."""
        code = """
class HandlerInitializationException(Exception):
    pass
"""
        tree = ast.parse(code)
        checker = NamingConventionChecker("test.py")
        checker.visit(tree)

        # Exception classes should not trigger anti-pattern violations
        assert len(checker.issues) == 0

    def test_errors_directory_classes_allowed(self):
        """Test that any class in errors/ directory is allowed anti-pattern names."""
        code = """
class ServiceRegistry:
    pass
"""
        tree = ast.parse(code)
        checker = NamingConventionChecker("src/mypackage/errors/registry.py")
        checker.visit(tree)

        # Classes in errors/ directory should not trigger anti-pattern violations
        assert len(checker.issues) == 0

    def test_handlers_directory_classes_allowed(self):
        """Test that handler classes in handlers/ directory are allowed."""
        code = """
class HandlerHttp:
    pass
"""
        tree = ast.parse(code)
        checker = NamingConventionChecker("src/omnibase_infra/handlers/handler_http.py")
        checker.visit(tree)

        # Classes in handlers/ directory should not trigger anti-pattern violations
        assert len(checker.issues) == 0

    def test_non_error_class_still_flagged(self):
        """Test that non-error classes with anti-patterns are still flagged."""
        code = """
class ServiceRegistry:
    pass
"""
        tree = ast.parse(code)
        checker = NamingConventionChecker("src/mypackage/registry/service_registry.py")
        checker.visit(tree)

        # Non-error classes outside exempt directories should still be flagged
        assert len(checker.issues) > 0
        assert any("Service" in issue for issue in checker.issues)


@pytest.mark.unit
class TestGenericPatternChecker:
    """Test GenericPatternChecker class."""

    def test_generic_function_name_process(self):
        """Test detection of generic function name 'process'."""
        code = """
def process(data):
    return data
"""
        tree = ast.parse(code)
        checker = GenericPatternChecker("test.py")
        checker.visit(tree)

        assert len(checker.issues) > 0
        assert any("too generic" in issue for issue in checker.issues)

    def test_generic_function_name_handle(self):
        """Test detection of generic function name 'handle'."""
        code = """
def handle(event):
    pass
"""
        tree = ast.parse(code)
        checker = GenericPatternChecker("test.py")
        checker.visit(tree)

        assert len(checker.issues) > 0
        assert any("too generic" in issue for issue in checker.issues)

    def test_generic_function_name_execute(self):
        """Test detection of generic function name 'execute'."""
        code = """
def execute(command):
    pass
"""
        tree = ast.parse(code)
        checker = GenericPatternChecker("test.py")
        checker.visit(tree)

        assert len(checker.issues) > 0

    def test_too_many_parameters(self):
        """Test detection of functions with too many parameters."""
        code = """
def complex_function(a, b, c, d, e, f):
    pass
"""
        tree = ast.parse(code)
        checker = GenericPatternChecker("test.py")
        checker.visit(tree)

        assert len(checker.issues) > 0
        assert any("6 parameters" in issue for issue in checker.issues)

    def test_acceptable_parameter_count(self):
        """Test that functions with acceptable parameters pass."""
        code = """
def good_function(a, b, c):
    pass
"""
        tree = ast.parse(code)
        checker = GenericPatternChecker("test.py")
        checker.visit(tree)

        # Should not trigger parameter count violation
        # but may trigger other checks if function name is generic
        issues_about_params = [i for i in checker.issues if "parameters" in i]
        assert len(issues_about_params) == 0

    def test_specific_function_name(self):
        """Test that specific function names pass."""
        code = """
def calculate_user_balance(user_id, account_type):
    pass
"""
        tree = ast.parse(code)
        checker = GenericPatternChecker("test.py")
        checker.visit(tree)

        assert len(checker.issues) == 0

    def test_multiple_violations(self):
        """Test detection of multiple violations in one file."""
        code = """
def process(a, b, c, d, e, f, g):
    pass

def handle(data):
    pass
"""
        tree = ast.parse(code)
        checker = GenericPatternChecker("test.py")
        checker.visit(tree)

        # Should detect both generic name and parameter count
        assert len(checker.issues) >= 2
