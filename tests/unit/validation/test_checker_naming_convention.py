"""
Comprehensive tests for checker_naming_convention module.

Tests all aspects of the naming convention checker including:
- File naming validation based on directory-specific prefix rules
- Class naming convention checks (PascalCase, anti-pattern detection)
- Function naming convention checks (snake_case)
- Directory validation with verbose mode
- CLI entry point and exit codes
- Edge cases and error conditions

Ticket: OMN-1224, OMN-1225
"""

import ast
import logging
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from omnibase_core.validation.checker_naming_convention import (
    ALLOWED_FILE_PREFIXES,
    ALLOWED_FILES,
    DIRECTORY_PREFIX_RULES,
    NamingConventionChecker,
    check_file_name,
    main,
    validate_directory,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def temp_omnibase_dir(tmp_path: Path) -> Path:
    """Create a temporary directory structure mimicking omnibase_core."""
    omnibase_dir = tmp_path / "src" / "omnibase_core"
    omnibase_dir.mkdir(parents=True)
    return omnibase_dir


@pytest.fixture
def temp_models_dir(temp_omnibase_dir: Path) -> Path:
    """Create a temporary models directory."""
    models_dir = temp_omnibase_dir / "models"
    models_dir.mkdir(parents=True)
    return models_dir


@pytest.fixture
def temp_enums_dir(temp_omnibase_dir: Path) -> Path:
    """Create a temporary enums directory."""
    enums_dir = temp_omnibase_dir / "enums"
    enums_dir.mkdir(parents=True)
    return enums_dir


@pytest.fixture
def temp_handlers_dir(temp_omnibase_dir: Path) -> Path:
    """Create a temporary handlers directory (for exempt testing)."""
    handlers_dir = temp_omnibase_dir / "handlers"
    handlers_dir.mkdir(parents=True)
    return handlers_dir


@pytest.fixture
def temp_errors_dir(temp_omnibase_dir: Path) -> Path:
    """Create a temporary errors directory."""
    errors_dir = temp_omnibase_dir / "errors"
    errors_dir.mkdir(parents=True)
    return errors_dir


# =============================================================================
# Tests for DIRECTORY_PREFIX_RULES constant
# =============================================================================


@pytest.mark.unit
class TestDirectoryPrefixRules:
    """Test coverage for all directories in DIRECTORY_PREFIX_RULES."""

    def test_rules_contain_expected_directories(self) -> None:
        """Verify all expected directories are covered."""
        expected_dirs = {
            "cli",
            "constants",
            "container",
            "context",
            "contracts",
            "decorators",
            "enums",
            "errors",
            "factories",
            "infrastructure",
            "logging",
            "mixins",
            "models",
            "nodes",
            "pipeline",
            "protocols",
            "resolution",
            "runtime",
            "schemas",
            "services",
            "tools",
            "types",
            "utils",
            "validation",
        }
        assert set(DIRECTORY_PREFIX_RULES.keys()) == expected_dirs

    def test_all_prefixes_are_tuples(self) -> None:
        """Verify all prefix values are tuples of strings."""
        for directory, prefixes in DIRECTORY_PREFIX_RULES.items():
            assert isinstance(prefixes, tuple), f"{directory} prefixes should be tuple"
            for prefix in prefixes:
                assert isinstance(prefix, str), f"Prefix {prefix} should be string"
                assert prefix.endswith("_"), (
                    f"Prefix {prefix} should end with underscore"
                )

    def test_models_directory_prefix(self) -> None:
        """Test models directory requires model_ prefix."""
        assert DIRECTORY_PREFIX_RULES["models"] == ("model_",)

    def test_enums_directory_prefix(self) -> None:
        """Test enums directory requires enum_ prefix."""
        assert DIRECTORY_PREFIX_RULES["enums"] == ("enum_",)

    def test_errors_directory_multiple_prefixes(self) -> None:
        """Test errors directory allows error_ or exception_ prefix."""
        assert DIRECTORY_PREFIX_RULES["errors"] == ("error_", "exception_")

    def test_pipeline_directory_multiple_prefixes(self) -> None:
        """Test pipeline directory allows multiple prefixes."""
        expected = (
            "builder_",
            "runner_",
            "manifest_",
            "composer_",
            "registry_",
            "pipeline_",
            "handler_",
        )
        assert DIRECTORY_PREFIX_RULES["pipeline"] == expected

    def test_validation_directory_prefixes(self) -> None:
        """Test validation directory allows validator_ or checker_ prefix."""
        assert DIRECTORY_PREFIX_RULES["validation"] == ("validator_", "checker_")


# =============================================================================
# Tests for ALLOWED_FILES and ALLOWED_FILE_PREFIXES constants
# =============================================================================


@pytest.mark.unit
class TestAllowedFilesConstants:
    """Test coverage for allowed files constants."""

    def test_allowed_files_contains_init(self) -> None:
        """Test __init__.py is in allowed files."""
        assert "__init__.py" in ALLOWED_FILES

    def test_allowed_files_contains_conftest(self) -> None:
        """Test conftest.py is in allowed files."""
        assert "conftest.py" in ALLOWED_FILES

    def test_allowed_files_contains_py_typed(self) -> None:
        """Test py.typed is in allowed files."""
        assert "py.typed" in ALLOWED_FILES

    def test_allowed_file_prefixes_contains_underscore(self) -> None:
        """Test underscore prefix is allowed for private modules."""
        assert "_" in ALLOWED_FILE_PREFIXES


# =============================================================================
# Tests for check_file_name function
# =============================================================================


@pytest.mark.unit
class TestCheckFileName:
    """Tests for the check_file_name function."""

    # -------------------------------------------------------------------------
    # Valid files tests
    # -------------------------------------------------------------------------

    def test_valid_model_file(self) -> None:
        """Test valid model file passes validation."""
        file_path = Path("src/omnibase_core/models/model_user.py")
        assert check_file_name(file_path) is None

    def test_valid_enum_file(self) -> None:
        """Test valid enum file passes validation."""
        file_path = Path("src/omnibase_core/enums/enum_status.py")
        assert check_file_name(file_path) is None

    def test_valid_protocol_file(self) -> None:
        """Test valid protocol file passes validation."""
        file_path = Path("src/omnibase_core/protocols/protocol_event_bus.py")
        assert check_file_name(file_path) is None

    def test_valid_error_file(self) -> None:
        """Test valid error file passes validation."""
        file_path = Path("src/omnibase_core/errors/error_runtime.py")
        assert check_file_name(file_path) is None

    def test_valid_exception_file(self) -> None:
        """Test valid exception file passes validation."""
        file_path = Path("src/omnibase_core/errors/exception_validation.py")
        assert check_file_name(file_path) is None

    def test_valid_validation_checker_file(self) -> None:
        """Test valid checker file passes validation."""
        file_path = Path("src/omnibase_core/validation/checker_naming_convention.py")
        assert check_file_name(file_path) is None

    def test_valid_validation_validator_file(self) -> None:
        """Test valid validator file passes validation."""
        file_path = Path("src/omnibase_core/validation/validator_contracts.py")
        assert check_file_name(file_path) is None

    # -------------------------------------------------------------------------
    # Invalid files tests
    # -------------------------------------------------------------------------

    def test_invalid_model_file_wrong_prefix(self) -> None:
        """Test invalid model file without prefix returns error."""
        file_path = Path("src/omnibase_core/models/user.py")
        error = check_file_name(file_path)
        assert error is not None
        assert "model_" in error
        assert "models/" in error

    def test_invalid_enum_file_wrong_prefix(self) -> None:
        """Test invalid enum file without prefix returns error."""
        file_path = Path("src/omnibase_core/enums/status.py")
        error = check_file_name(file_path)
        assert error is not None
        assert "enum_" in error

    def test_invalid_protocol_file_wrong_prefix(self) -> None:
        """Test invalid protocol file without prefix returns error."""
        file_path = Path("src/omnibase_core/protocols/event_bus.py")
        error = check_file_name(file_path)
        assert error is not None
        assert "protocol_" in error

    def test_invalid_validation_file_wrong_prefix(self) -> None:
        """Test invalid validation file without prefix returns error."""
        file_path = Path("src/omnibase_core/validation/naming_convention.py")
        error = check_file_name(file_path)
        assert error is not None
        assert "validator_" in error or "checker_" in error

    def test_error_message_format_single_prefix(self) -> None:
        """Test error message format for directory with single prefix."""
        file_path = Path("src/omnibase_core/models/bad_file.py")
        error = check_file_name(file_path)
        assert error is not None
        assert "'model_'" in error  # Single quotes around single prefix

    def test_error_message_format_multiple_prefixes(self) -> None:
        """Test error message format for directory with multiple prefixes."""
        file_path = Path("src/omnibase_core/errors/bad_file.py")
        error = check_file_name(file_path)
        assert error is not None
        assert "one of" in error  # "one of" for multiple prefixes

    # -------------------------------------------------------------------------
    # Allowed exceptions tests
    # -------------------------------------------------------------------------

    def test_init_file_allowed(self) -> None:
        """Test __init__.py is allowed in any directory."""
        file_path = Path("src/omnibase_core/models/__init__.py")
        assert check_file_name(file_path) is None

    def test_conftest_file_allowed(self) -> None:
        """Test conftest.py is allowed in any directory."""
        file_path = Path("src/omnibase_core/models/conftest.py")
        assert check_file_name(file_path) is None

    def test_py_typed_file_allowed(self) -> None:
        """Test py.typed is allowed in any directory."""
        file_path = Path("src/omnibase_core/models/py.typed")
        assert check_file_name(file_path) is None

    # -------------------------------------------------------------------------
    # Private modules tests
    # -------------------------------------------------------------------------

    def test_private_module_allowed(self) -> None:
        """Test private modules starting with underscore are allowed."""
        file_path = Path("src/omnibase_core/models/_internal.py")
        assert check_file_name(file_path) is None

    def test_private_helper_module_allowed(self) -> None:
        """Test private helper modules are allowed."""
        file_path = Path("src/omnibase_core/utils/_helpers.py")
        assert check_file_name(file_path) is None

    # -------------------------------------------------------------------------
    # Non-Python files tests
    # -------------------------------------------------------------------------

    def test_non_python_file_allowed(self) -> None:
        """Test non-Python files are not validated."""
        file_path = Path("src/omnibase_core/models/schema.json")
        assert check_file_name(file_path) is None

    def test_yaml_file_allowed(self) -> None:
        """Test YAML files are not validated."""
        file_path = Path("src/omnibase_core/models/config.yaml")
        assert check_file_name(file_path) is None

    def test_markdown_file_allowed(self) -> None:
        """Test markdown files are not validated."""
        file_path = Path("src/omnibase_core/models/README.md")
        assert check_file_name(file_path) is None

    # -------------------------------------------------------------------------
    # Path structure tests
    # -------------------------------------------------------------------------

    def test_file_outside_omnibase_core(self) -> None:
        """Test files outside omnibase_core are not validated."""
        file_path = Path("some/other/path/models/user.py")
        assert check_file_name(file_path) is None

    def test_nested_directory_inherits_parent_rule(self) -> None:
        """Test nested directories inherit parent's rule."""
        # models/cli/ should use models/ rule (model_*), not cli/ rule
        file_path = Path("src/omnibase_core/models/cli/model_cli.py")
        assert check_file_name(file_path) is None

    def test_nested_directory_invalid_file(self) -> None:
        """Test nested directories enforce parent's rule."""
        # models/cli/cli_commands.py should fail because it needs model_ prefix
        file_path = Path("src/omnibase_core/models/cli/cli_commands.py")
        error = check_file_name(file_path)
        assert error is not None
        assert "model_" in error

    def test_deeply_nested_path(self) -> None:
        """Test deeply nested paths still validate correctly."""
        file_path = Path("src/omnibase_core/models/sub1/sub2/sub3/model_deep.py")
        assert check_file_name(file_path) is None

    def test_deeply_nested_path_invalid(self) -> None:
        """Test deeply nested paths still catch violations."""
        file_path = Path("src/omnibase_core/models/sub1/sub2/sub3/deep.py")
        error = check_file_name(file_path)
        assert error is not None

    def test_absolute_path_valid(self) -> None:
        """Test absolute paths work correctly."""
        file_path = Path("/home/user/project/src/omnibase_core/models/model_user.py")
        assert check_file_name(file_path) is None

    def test_absolute_path_invalid(self) -> None:
        """Test absolute paths catch violations."""
        file_path = Path("/home/user/project/src/omnibase_core/models/user.py")
        error = check_file_name(file_path)
        assert error is not None

    # -------------------------------------------------------------------------
    # Directory coverage tests
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize(
        ("directory", "prefix"),
        [
            ("cli", "cli_"),
            ("constants", "constants_"),
            ("container", "container_"),
            ("context", "context_"),
            ("contracts", "contract_"),
            ("decorators", "decorator_"),
            ("enums", "enum_"),
            ("factories", "factory_"),
            ("logging", "logging_"),
            ("mixins", "mixin_"),
            ("models", "model_"),
            ("nodes", "node_"),
            ("protocols", "protocol_"),
            ("resolution", "resolver_"),
            ("schemas", "schema_"),
            ("services", "service_"),
            ("tools", "tool_"),
            ("utils", "util_"),
        ],
    )
    def test_all_single_prefix_directories_valid(
        self, directory: str, prefix: str
    ) -> None:
        """Test valid files pass for all single-prefix directories."""
        file_path = Path(f"src/omnibase_core/{directory}/{prefix}test.py")
        assert check_file_name(file_path) is None

    @pytest.mark.parametrize(
        ("directory", "prefix"),
        [
            ("cli", "cli_"),
            ("constants", "constants_"),
            ("container", "container_"),
            ("context", "context_"),
            ("contracts", "contract_"),
            ("decorators", "decorator_"),
            ("enums", "enum_"),
            ("factories", "factory_"),
            ("logging", "logging_"),
            ("mixins", "mixin_"),
            ("models", "model_"),
            ("nodes", "node_"),
            ("protocols", "protocol_"),
            ("resolution", "resolver_"),
            ("schemas", "schema_"),
            ("services", "service_"),
            ("tools", "tool_"),
            ("utils", "util_"),
        ],
    )
    def test_all_single_prefix_directories_invalid(
        self, directory: str, prefix: str
    ) -> None:
        """Test invalid files fail for all single-prefix directories."""
        file_path = Path(f"src/omnibase_core/{directory}/wrong_prefix.py")
        error = check_file_name(file_path)
        assert error is not None

    def test_infrastructure_allows_node_prefix(self) -> None:
        """Test infrastructure directory allows node_ prefix."""
        file_path = Path("src/omnibase_core/infrastructure/node_base.py")
        assert check_file_name(file_path) is None

    def test_infrastructure_allows_infra_prefix(self) -> None:
        """Test infrastructure directory allows infra_ prefix."""
        file_path = Path("src/omnibase_core/infrastructure/infra_config.py")
        assert check_file_name(file_path) is None

    def test_runtime_allows_runtime_prefix(self) -> None:
        """Test runtime directory allows runtime_ prefix."""
        file_path = Path("src/omnibase_core/runtime/runtime_config.py")
        assert check_file_name(file_path) is None

    def test_runtime_allows_handler_prefix(self) -> None:
        """Test runtime directory allows handler_ prefix."""
        file_path = Path("src/omnibase_core/runtime/handler_events.py")
        assert check_file_name(file_path) is None

    def test_types_allows_typed_dict_prefix(self) -> None:
        """Test types directory allows typed_dict_ prefix."""
        file_path = Path("src/omnibase_core/types/typed_dict_config.py")
        assert check_file_name(file_path) is None

    def test_types_allows_type_prefix(self) -> None:
        """Test types directory allows type_ prefix."""
        file_path = Path("src/omnibase_core/types/type_compute.py")
        assert check_file_name(file_path) is None

    def test_types_allows_converter_prefix(self) -> None:
        """Test types directory allows converter_ prefix."""
        file_path = Path("src/omnibase_core/types/converter_json.py")
        assert check_file_name(file_path) is None

    def test_pipeline_all_prefixes_valid(self) -> None:
        """Test pipeline directory allows all its prefixes."""
        prefixes = [
            "builder_",
            "runner_",
            "manifest_",
            "composer_",
            "registry_",
            "pipeline_",
            "handler_",
        ]
        for prefix in prefixes:
            file_path = Path(f"src/omnibase_core/pipeline/{prefix}test.py")
            assert check_file_name(file_path) is None, f"Failed for prefix: {prefix}"


# =============================================================================
# Tests for NamingConventionChecker class
# =============================================================================


@pytest.mark.unit
class TestNamingConventionChecker:
    """Tests for the NamingConventionChecker AST visitor."""

    # -------------------------------------------------------------------------
    # Valid class naming tests
    # -------------------------------------------------------------------------

    def test_valid_pascal_case_class(self) -> None:
        """Test valid PascalCase class name passes."""
        source = """
class MyValidClass:
    pass
"""
        tree = ast.parse(source)
        checker = NamingConventionChecker("test.py")
        checker.visit(tree)
        assert len(checker.issues) == 0

    def test_valid_pascal_case_with_numbers(self) -> None:
        """Test valid PascalCase with numbers passes."""
        source = """
class Model2D:
    pass
class Http2Client:
    pass
"""
        tree = ast.parse(source)
        checker = NamingConventionChecker("test.py")
        checker.visit(tree)
        assert len(checker.issues) == 0

    def test_valid_single_letter_class(self) -> None:
        """Test single uppercase letter class passes."""
        source = """
class A:
    pass
"""
        tree = ast.parse(source)
        checker = NamingConventionChecker("test.py")
        checker.visit(tree)
        assert len(checker.issues) == 0

    # -------------------------------------------------------------------------
    # Invalid class naming tests
    # -------------------------------------------------------------------------

    def test_invalid_snake_case_class(self) -> None:
        """Test snake_case class name is flagged."""
        source = """
class my_invalid_class:
    pass
"""
        tree = ast.parse(source)
        checker = NamingConventionChecker("test.py")
        checker.visit(tree)
        assert len(checker.issues) == 1
        assert "PascalCase" in checker.issues[0]

    def test_invalid_camel_case_class(self) -> None:
        """Test camelCase class name is flagged (starts lowercase)."""
        source = """
class myInvalidClass:
    pass
"""
        tree = ast.parse(source)
        checker = NamingConventionChecker("test.py")
        checker.visit(tree)
        assert len(checker.issues) == 1
        assert "PascalCase" in checker.issues[0]

    def test_invalid_class_with_underscore(self) -> None:
        """Test class name with underscore is flagged."""
        source = """
class My_Invalid_Class:
    pass
"""
        tree = ast.parse(source)
        checker = NamingConventionChecker("test.py")
        checker.visit(tree)
        assert len(checker.issues) == 1
        assert "PascalCase" in checker.issues[0]

    def test_invalid_all_caps_class(self) -> None:
        """Test all caps class name with underscore is flagged."""
        source = """
class MY_CONSTANT:
    pass
"""
        tree = ast.parse(source)
        checker = NamingConventionChecker("test.py")
        checker.visit(tree)
        assert len(checker.issues) == 1
        assert "PascalCase" in checker.issues[0]

    # -------------------------------------------------------------------------
    # Anti-pattern detection tests
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize(
        ("class_name", "pattern"),
        [
            ("UserManager", "Manager"),
            ("DataHandler", "Handler"),
            ("StringHelper", "Helper"),
            ("FileUtility", "Utility"),
            ("CacheUtil", "Util"),
            ("AuthService", "Service"),
            ("RequestController", "Controller"),
            ("DataProcessor", "Processor"),
            ("TaskWorker", "Worker"),
        ],
    )
    def test_anti_pattern_detected(self, class_name: str, pattern: str) -> None:
        """Test anti-pattern class names are detected."""
        source = f"""
class {class_name}:
    pass
"""
        tree = ast.parse(source)
        checker = NamingConventionChecker("test.py")
        checker.visit(tree)
        assert len(checker.issues) >= 1
        assert any(pattern in issue for issue in checker.issues)
        assert any("anti-pattern" in issue for issue in checker.issues)

    def test_anti_pattern_case_insensitive(self) -> None:
        """Test anti-pattern detection is case insensitive."""
        source = """
class MYMANAGER:
    pass
"""
        tree = ast.parse(source)
        checker = NamingConventionChecker("test.py")
        checker.visit(tree)
        assert any("Manager" in issue for issue in checker.issues)

    # -------------------------------------------------------------------------
    # Exempt classes tests
    # -------------------------------------------------------------------------

    def test_error_class_exempt_from_anti_patterns(self) -> None:
        """Test Error classes are exempt from anti-pattern checks."""
        source = """
class HandlerConfigurationError:
    pass
class ServiceUnavailableError:
    pass
"""
        tree = ast.parse(source)
        checker = NamingConventionChecker("test.py")
        checker.visit(tree)
        # Should not flag anti-patterns for Error classes
        anti_pattern_issues = [i for i in checker.issues if "anti-pattern" in i]
        assert len(anti_pattern_issues) == 0

    def test_exception_class_exempt_from_anti_patterns(self) -> None:
        """Test Exception classes are exempt from anti-pattern checks."""
        source = """
class HandlerException:
    pass
class ServiceException:
    pass
"""
        tree = ast.parse(source)
        checker = NamingConventionChecker("test.py")
        checker.visit(tree)
        anti_pattern_issues = [i for i in checker.issues if "anti-pattern" in i]
        assert len(anti_pattern_issues) == 0

    def test_handlers_directory_exempt_from_anti_patterns(self) -> None:
        """Test classes in handlers/ directory are exempt from anti-pattern checks."""
        source = """
class RequestHandler:
    pass
"""
        tree = ast.parse(source)
        checker = NamingConventionChecker("src/omnibase_core/handlers/handler_http.py")
        checker.visit(tree)
        anti_pattern_issues = [i for i in checker.issues if "anti-pattern" in i]
        assert len(anti_pattern_issues) == 0

    def test_errors_directory_exempt_from_anti_patterns(self) -> None:
        """Test classes in errors/ directory are exempt from anti-pattern checks."""
        source = """
class ServiceError:
    pass
"""
        tree = ast.parse(source)
        checker = NamingConventionChecker("src/omnibase_core/errors/error_service.py")
        checker.visit(tree)
        anti_pattern_issues = [i for i in checker.issues if "anti-pattern" in i]
        assert len(anti_pattern_issues) == 0

    def test_errors_py_file_exempt_from_anti_patterns(self) -> None:
        """Test classes in errors.py file are exempt from anti-pattern checks."""
        source = """
class ManagerError:
    pass
"""
        tree = ast.parse(source)
        checker = NamingConventionChecker("src/omnibase_core/models/errors.py")
        checker.visit(tree)
        anti_pattern_issues = [i for i in checker.issues if "anti-pattern" in i]
        assert len(anti_pattern_issues) == 0

    # -------------------------------------------------------------------------
    # Function naming tests
    # -------------------------------------------------------------------------

    def test_valid_snake_case_function(self) -> None:
        """Test valid snake_case function passes."""
        source = """
def my_valid_function():
    pass
"""
        tree = ast.parse(source)
        checker = NamingConventionChecker("test.py")
        checker.visit(tree)
        assert len(checker.issues) == 0

    def test_valid_function_with_numbers(self) -> None:
        """Test valid function with numbers passes."""
        source = """
def process_v2_data():
    pass
def get_item_123():
    pass
"""
        tree = ast.parse(source)
        checker = NamingConventionChecker("test.py")
        checker.visit(tree)
        assert len(checker.issues) == 0

    def test_valid_single_underscore_function(self) -> None:
        """Test single underscore prefix passes."""
        source = """
def _private_function():
    pass
"""
        tree = ast.parse(source)
        checker = NamingConventionChecker("test.py")
        checker.visit(tree)
        assert len(checker.issues) == 0

    def test_valid_single_letter_function(self) -> None:
        """Test single lowercase letter function passes."""
        source = """
def a():
    pass
def x():
    pass
"""
        tree = ast.parse(source)
        checker = NamingConventionChecker("test.py")
        checker.visit(tree)
        assert len(checker.issues) == 0

    def test_invalid_camel_case_function(self) -> None:
        """Test camelCase function is flagged."""
        source = """
def myInvalidFunction():
    pass
"""
        tree = ast.parse(source)
        checker = NamingConventionChecker("test.py")
        checker.visit(tree)
        assert len(checker.issues) == 1
        assert "snake_case" in checker.issues[0]

    def test_invalid_pascal_case_function(self) -> None:
        """Test PascalCase function is flagged."""
        source = """
def MyInvalidFunction():
    pass
"""
        tree = ast.parse(source)
        checker = NamingConventionChecker("test.py")
        checker.visit(tree)
        assert len(checker.issues) == 1
        assert "snake_case" in checker.issues[0]

    def test_invalid_mixed_case_function(self) -> None:
        """Test mixed case function with uppercase is flagged."""
        source = """
def get_HTML_content():
    pass
"""
        tree = ast.parse(source)
        checker = NamingConventionChecker("test.py")
        checker.visit(tree)
        assert len(checker.issues) == 1
        assert "snake_case" in checker.issues[0]

    # -------------------------------------------------------------------------
    # Dunder methods tests
    # -------------------------------------------------------------------------

    def test_dunder_methods_skipped(self) -> None:
        """Test dunder methods are skipped."""
        source = """
class MyClass:
    def __init__(self):
        pass
    def __str__(self):
        return ""
    def __repr__(self):
        return ""
    def __eq__(self, other):
        return True
    def __hash__(self):
        return 0
"""
        tree = ast.parse(source)
        checker = NamingConventionChecker("test.py")
        checker.visit(tree)
        assert len(checker.issues) == 0

    def test_dunder_like_not_skipped(self) -> None:
        """Test dunder-like but not actual dunder methods are checked."""
        source = """
def __notDunder(x):
    pass
def notDunder__(x):
    pass
"""
        tree = ast.parse(source)
        checker = NamingConventionChecker("test.py")
        checker.visit(tree)
        # These should be checked (and fail snake_case or be ignored)
        # Actually __notDunder is treated as snake_case starting with underscore
        # notDunder__ has uppercase D so it fails
        issues = [i for i in checker.issues if "snake_case" in i]
        assert len(issues) >= 1

    # -------------------------------------------------------------------------
    # Nested classes and functions tests
    # -------------------------------------------------------------------------

    def test_nested_class_checked(self) -> None:
        """Test nested classes are checked."""
        source = """
class OuterClass:
    class innerClass:
        pass
"""
        tree = ast.parse(source)
        checker = NamingConventionChecker("test.py")
        checker.visit(tree)
        assert len(checker.issues) == 1
        assert "innerClass" in checker.issues[0]

    def test_nested_function_checked(self) -> None:
        """Test nested functions are checked."""
        source = """
def outer_function():
    def innerFunction():
        pass
"""
        tree = ast.parse(source)
        checker = NamingConventionChecker("test.py")
        checker.visit(tree)
        assert len(checker.issues) == 1
        assert "innerFunction" in checker.issues[0]

    def test_method_in_class_checked(self) -> None:
        """Test methods in classes are checked."""
        source = """
class MyClass:
    def validMethod(self):
        pass
"""
        tree = ast.parse(source)
        checker = NamingConventionChecker("test.py")
        checker.visit(tree)
        # validMethod has uppercase M, so it fails snake_case
        assert len(checker.issues) == 1
        assert "snake_case" in checker.issues[0]

    # -------------------------------------------------------------------------
    # Line number tests
    # -------------------------------------------------------------------------

    def test_line_numbers_in_issues(self) -> None:
        """Test line numbers are included in issue messages."""
        source = """
class badClass:
    pass

def BadFunction():
    pass
"""
        tree = ast.parse(source)
        checker = NamingConventionChecker("test.py")
        checker.visit(tree)
        assert len(checker.issues) == 2
        assert "Line 2" in checker.issues[0]
        assert "Line 5" in checker.issues[1]

    # -------------------------------------------------------------------------
    # Multiple issues tests
    # -------------------------------------------------------------------------

    def test_multiple_issues_detected(self) -> None:
        """Test multiple issues are detected in one file."""
        source = """
class bad_class:
    pass

class DataManager:
    pass

def BadFunction():
    pass

def anotherBadFunc():
    pass
"""
        tree = ast.parse(source)
        checker = NamingConventionChecker("test.py")
        checker.visit(tree)
        # Should detect: bad_class (not PascalCase), DataManager (anti-pattern),
        # BadFunction (not snake_case), anotherBadFunc (not snake_case)
        assert len(checker.issues) >= 4


# =============================================================================
# Tests for validate_directory function
# =============================================================================


@pytest.mark.unit
class TestValidateDirectory:
    """Tests for the validate_directory function."""

    def test_empty_directory(self, temp_omnibase_dir: Path) -> None:
        """Test empty directory returns no errors."""
        errors = validate_directory(temp_omnibase_dir)
        assert errors == []

    def test_valid_directory(self, temp_models_dir: Path) -> None:
        """Test directory with valid files returns no errors."""
        (temp_models_dir / "model_user.py").write_text("# Valid file\n")
        (temp_models_dir / "model_auth.py").write_text("# Valid file\n")
        (temp_models_dir / "__init__.py").write_text("# Init file\n")

        parent_dir = temp_models_dir.parent
        errors = validate_directory(parent_dir)
        assert errors == []

    def test_invalid_directory(self, temp_models_dir: Path) -> None:
        """Test directory with invalid files returns errors."""
        (temp_models_dir / "user.py").write_text("# Invalid file\n")
        (temp_models_dir / "auth.py").write_text("# Invalid file\n")

        parent_dir = temp_models_dir.parent
        errors = validate_directory(parent_dir)
        assert len(errors) == 2

    def test_mixed_valid_invalid(self, temp_models_dir: Path) -> None:
        """Test directory with mixed valid/invalid files."""
        (temp_models_dir / "model_valid.py").write_text("# Valid\n")
        (temp_models_dir / "invalid.py").write_text("# Invalid\n")
        (temp_models_dir / "__init__.py").write_text("# Init\n")

        parent_dir = temp_models_dir.parent
        errors = validate_directory(parent_dir)
        assert len(errors) == 1
        assert "invalid.py" in errors[0]

    def test_verbose_mode(
        self, temp_models_dir: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test verbose mode logs checked files."""
        (temp_models_dir / "model_test.py").write_text("# Valid\n")

        parent_dir = temp_models_dir.parent
        with caplog.at_level(logging.DEBUG):
            validate_directory(parent_dir, verbose=True)
            # Note: The logging is at DEBUG level

    def test_recursive_validation(self, temp_models_dir: Path) -> None:
        """Test validation is recursive into subdirectories."""
        subdir = temp_models_dir / "subdir"
        subdir.mkdir()
        (subdir / "model_sub.py").write_text("# Valid\n")
        (subdir / "bad.py").write_text("# Invalid\n")

        parent_dir = temp_models_dir.parent
        errors = validate_directory(parent_dir)
        assert len(errors) == 1
        assert "bad.py" in errors[0]

    def test_nonexistent_directory(self, tmp_path: Path) -> None:
        """Test non-existent directory handling."""
        nonexistent = tmp_path / "nonexistent"
        errors = validate_directory(nonexistent)
        # rglob on non-existent directory returns empty iterator
        assert errors == []

    def test_error_includes_full_path(self, temp_models_dir: Path) -> None:
        """Test errors include the full file path."""
        bad_file = temp_models_dir / "bad_file.py"
        bad_file.write_text("# Invalid\n")

        parent_dir = temp_models_dir.parent
        errors = validate_directory(parent_dir)
        assert len(errors) == 1
        assert str(bad_file) in errors[0]


# =============================================================================
# Tests for main function (CLI)
# =============================================================================


@pytest.mark.unit
class TestMainFunction:
    """Tests for the main CLI entry point."""

    def test_main_returns_zero_on_success(self, temp_omnibase_dir: Path) -> None:
        """Test main returns 0 when all files are valid."""
        models_dir = temp_omnibase_dir / "models"
        models_dir.mkdir()
        (models_dir / "model_test.py").write_text("# Valid\n")

        with patch.object(sys, "argv", ["checker", str(temp_omnibase_dir)]):
            result = main()
            assert result == 0

    def test_main_returns_one_on_violations(self, temp_omnibase_dir: Path) -> None:
        """Test main returns 1 when violations found."""
        models_dir = temp_omnibase_dir / "models"
        models_dir.mkdir()
        (models_dir / "bad_file.py").write_text("# Invalid\n")

        with patch.object(sys, "argv", ["checker", str(temp_omnibase_dir)]):
            result = main()
            assert result == 1

    def test_main_returns_one_for_nonexistent_directory(self) -> None:
        """Test main returns 1 for non-existent directory."""
        with patch.object(sys, "argv", ["checker", "/nonexistent/path"]):
            result = main()
            assert result == 1

    def test_main_verbose_flag(self, temp_omnibase_dir: Path) -> None:
        """Test main accepts verbose flag."""
        with patch.object(sys, "argv", ["checker", str(temp_omnibase_dir), "-v"]):
            result = main()
            assert result == 0

    def test_main_verbose_long_flag(self, temp_omnibase_dir: Path) -> None:
        """Test main accepts --verbose flag."""
        with patch.object(
            sys, "argv", ["checker", str(temp_omnibase_dir), "--verbose"]
        ):
            result = main()
            assert result == 0

    def test_main_default_directory(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test main uses default directory when none specified."""
        # Mock __file__ to control the default directory calculation
        with patch.object(sys, "argv", ["checker"]):
            # The default directory is calculated from __file__ location
            # This test just ensures the function doesn't crash
            result = main()
            # Result depends on actual source tree structure
            assert result in [0, 1]

    def test_main_logs_violations(
        self, temp_omnibase_dir: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test main logs violation messages."""
        models_dir = temp_omnibase_dir / "models"
        models_dir.mkdir()
        (models_dir / "bad_file.py").write_text("# Invalid\n")

        with patch.object(sys, "argv", ["checker", str(temp_omnibase_dir)]):
            with caplog.at_level(logging.WARNING):
                main()
                assert "violation" in caplog.text.lower()

    def test_main_logs_success(
        self, temp_omnibase_dir: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test main logs success message."""
        models_dir = temp_omnibase_dir / "models"
        models_dir.mkdir()
        (models_dir / "model_valid.py").write_text("# Valid\n")

        with patch.object(sys, "argv", ["checker", str(temp_omnibase_dir)]):
            with caplog.at_level(logging.INFO):
                main()
                assert "conform" in caplog.text.lower() or "All files" in caplog.text


# =============================================================================
# Edge case tests
# =============================================================================


@pytest.mark.unit
class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_empty_python_file(self, temp_models_dir: Path) -> None:
        """Test empty Python files are handled."""
        empty_file = temp_models_dir / "model_empty.py"
        empty_file.touch()

        parent_dir = temp_models_dir.parent
        errors = validate_directory(parent_dir)
        assert errors == []

    def test_file_with_only_comments(self, temp_models_dir: Path) -> None:
        """Test Python files with only comments are handled."""
        comment_file = temp_models_dir / "model_comments.py"
        comment_file.write_text("# Just a comment\n# Another comment\n")

        parent_dir = temp_models_dir.parent
        errors = validate_directory(parent_dir)
        assert errors == []

    def test_unicode_in_file_content(self, temp_models_dir: Path) -> None:
        """Test files with Unicode content are handled."""
        unicode_file = temp_models_dir / "model_unicode.py"
        unicode_file.write_text(
            '# -*- coding: utf-8 -*-\n"""Unicode: 中文, emoji, special chars"""\n',
            encoding="utf-8",
        )

        parent_dir = temp_models_dir.parent
        errors = validate_directory(parent_dir)
        assert errors == []

    def test_windows_path_separators(self) -> None:
        """Test path with Windows separators works."""
        # Path() normalizes separators
        file_path = Path("src\\omnibase_core\\models\\model_test.py")
        # This should work regardless of platform
        result = check_file_name(file_path)
        assert result is None

    def test_path_with_dots(self) -> None:
        """Test path with . and .. components."""
        file_path = Path("src/omnibase_core/./models/../models/model_test.py")
        # Path normalization should handle this
        result = check_file_name(file_path)
        assert result is None

    def test_checker_with_empty_file_path(self) -> None:
        """Test NamingConventionChecker with empty file path."""
        source = """
class ValidClass:
    pass
"""
        tree = ast.parse(source)
        checker = NamingConventionChecker("")
        checker.visit(tree)
        assert len(checker.issues) == 0

    def test_ast_parse_preserves_line_numbers(self) -> None:
        """Test AST parsing preserves correct line numbers."""
        source = """
# Line 1
# Line 2
class bad_class:
    pass
"""
        tree = ast.parse(source)
        checker = NamingConventionChecker("test.py")
        checker.visit(tree)
        # bad_class is not PascalCase, so it should be flagged on line 4
        assert len(checker.issues) == 1
        assert "Line 4" in checker.issues[0]

    def test_file_in_omnibase_core_root(self) -> None:
        """Test file directly in omnibase_core (no subdirectory)."""
        file_path = Path("src/omnibase_core/some_file.py")
        # No directory rule applies, so it should pass
        result = check_file_name(file_path)
        assert result is None

    def test_directory_not_in_rules(self) -> None:
        """Test directory not in DIRECTORY_PREFIX_RULES."""
        file_path = Path("src/omnibase_core/unknown_dir/any_file.py")
        # No rule applies, so it should pass
        result = check_file_name(file_path)
        assert result is None

    def test_multiple_classes_with_mixed_validity(self) -> None:
        """Test file with multiple classes, some valid, some invalid."""
        source = """
class ValidClass:
    pass

class invalid_class:
    pass

class AnotherValidClass:
    pass

class DataManager:
    pass
"""
        tree = ast.parse(source)
        checker = NamingConventionChecker("test.py")
        checker.visit(tree)
        # Should have 2 issues: invalid_class (PascalCase), DataManager (anti-pattern)
        assert len(checker.issues) == 2

    def test_class_and_function_with_same_issues(self) -> None:
        """Test both class and function violations in same file."""
        source = """
class badClass:
    def BadMethod(self):
        pass
"""
        tree = ast.parse(source)
        checker = NamingConventionChecker("test.py")
        checker.visit(tree)
        # badClass: PascalCase issue, BadMethod: snake_case issue
        assert len(checker.issues) == 2

    def test_async_function_naming(self) -> None:
        """Test async function naming is NOT currently checked.

        Note: The NamingConventionChecker only handles regular FunctionDef nodes,
        not AsyncFunctionDef nodes. This is a known limitation. If async function
        naming enforcement is needed in the future, add visit_AsyncFunctionDef
        to the NamingConventionChecker class.
        """
        source = """
async def ValidAsyncFunc():
    pass

async def valid_async_func():
    pass
"""
        tree = ast.parse(source)
        checker = NamingConventionChecker("test.py")
        checker.visit(tree)
        # Async functions are NOT currently checked by the naming convention checker
        # This documents the current behavior - async functions bypass validation
        assert len(checker.issues) == 0


# =============================================================================
# Integration tests
# =============================================================================


@pytest.mark.unit
class TestIntegration:
    """Integration tests for the naming convention checker."""

    def test_full_validation_workflow(self, tmp_path: Path) -> None:
        """Test complete validation workflow."""
        # Create directory structure
        omnibase = tmp_path / "src" / "omnibase_core"
        models = omnibase / "models"
        enums = omnibase / "enums"
        models.mkdir(parents=True)
        enums.mkdir(parents=True)

        # Create valid files
        (models / "__init__.py").write_text("")
        (models / "model_user.py").write_text("class ModelUser: pass\n")
        (enums / "__init__.py").write_text("")
        (enums / "enum_status.py").write_text("class EnumStatus: pass\n")

        # Create invalid file
        (models / "bad_name.py").write_text("class BadName: pass\n")

        errors = validate_directory(omnibase)
        assert len(errors) == 1
        assert "bad_name.py" in errors[0]

    def test_real_directory_structure(self, temp_omnibase_dir: Path) -> None:
        """Test with realistic directory structure."""
        # Create multiple directories
        for dir_name in ["models", "enums", "protocols", "services"]:
            (temp_omnibase_dir / dir_name).mkdir()

        # Add valid files
        (temp_omnibase_dir / "models" / "model_base.py").write_text("")
        (temp_omnibase_dir / "enums" / "enum_type.py").write_text("")
        (temp_omnibase_dir / "protocols" / "protocol_event.py").write_text("")
        (temp_omnibase_dir / "services" / "service_auth.py").write_text("")

        # Add init files
        for dir_name in ["models", "enums", "protocols", "services"]:
            (temp_omnibase_dir / dir_name / "__init__.py").write_text("")

        errors = validate_directory(temp_omnibase_dir)
        assert errors == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
