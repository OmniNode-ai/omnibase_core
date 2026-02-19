#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Tests for scripts/validation/validate_naming.py module (NamingConventionValidator).

NOTE: This file tests CLASS naming conventions (e.g., ModelUser, EnumStatus,
ProtocolEventBus). The NamingConventionValidator enforces that:
- Classes in models/ directories should be named Model*
- Classes in enums/ directories should be named Enum*
- Classes in protocols/ directories should be named Protocol*
- etc.

For FILE naming convention tests, see test_checker_naming_convention.py which
tests src/omnibase_core/validation/checker_naming_convention.py. That module
enforces file naming patterns (e.g., model_*.py, enum_*.py) rather than class
naming patterns.

SUMMARY OF NAMING CONVENTION MODULES:
- validate_naming.py (scripts/): CLASS naming (ModelUser, EnumStatus)
- checker_naming_convention.py (src/): FILE naming (model_user.py, enum_status.py)

Tests all aspects of the NamingConventionValidator including:
- Valid naming patterns for all entity types
- Invalid naming patterns that should trigger violations
- Edge cases like empty files, syntax errors
- File organization validation
- Exception patterns that should be ignored
"""

import shutil

# Import the validation module
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(
    0,
    str(Path(__file__).parent.parent.parent.parent / "scripts" / "validation"),
)
from validate_naming import NamingConventionValidator, NamingViolation, main


@pytest.fixture
def temp_repo():
    """Create a temporary repository structure for testing."""
    temp_dir = tempfile.mkdtemp()
    repo_path = Path(temp_dir)

    # Create basic repository structure
    (repo_path / "src" / "omnibase_core").mkdir(parents=True)

    yield repo_path

    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def naming_validator(temp_repo):
    """Create a NamingConventionValidator instance for testing."""
    return NamingConventionValidator(temp_repo)


@pytest.mark.unit
class TestNamingConventionValidator:
    """Test cases for NamingConventionValidator."""

    def test_initialization(self, temp_repo):
        """Test validator initialization."""
        validator = NamingConventionValidator(temp_repo)
        assert validator.repo_path == temp_repo
        assert validator.violations == []

    def test_valid_model_naming(self, temp_repo):
        """Test validation of correctly named model files and classes."""
        models_dir = temp_repo / "src" / "omnibase_core" / "models"
        models_dir.mkdir(parents=True)

        # Create valid model file
        valid_model_content = '''
from pydantic import BaseModel

class ModelUserAuth(BaseModel):
    """User authentication model."""
    user_id: str
    username: str

class ModelUserSession(BaseModel):
    """User session model."""
    session_id: str
    user_id: str
'''
        model_file = models_dir / "model_user_auth.py"
        model_file.write_text(valid_model_content)

        validator = NamingConventionValidator(temp_repo)
        is_valid = validator.validate_naming_conventions()

        # Should pass validation
        error_violations = [v for v in validator.violations if v.severity == "error"]
        assert len(error_violations) == 0
        assert is_valid is True

    def test_invalid_model_naming(self, temp_repo):
        """Test detection of incorrectly named model classes."""
        models_dir = temp_repo / "src" / "omnibase_core" / "models"
        models_dir.mkdir(parents=True)

        # Create invalid model file
        invalid_model_content = '''
from pydantic import BaseModel

class UserAuth(BaseModel):  # Should be ModelUserAuth
    """User authentication model."""
    user_id: str
    username: str

class UserData(BaseModel):  # Should be ModelUserData
    """User data model."""
    name: str
    email: str
'''
        model_file = models_dir / "model_user_auth.py"
        model_file.write_text(invalid_model_content)

        validator = NamingConventionValidator(temp_repo)
        is_valid = validator.validate_naming_conventions()

        # Should detect naming violations
        error_violations = [v for v in validator.violations if v.severity == "error"]
        assert len(error_violations) >= 2
        assert is_valid is False

        # Check specific violations
        violation_classes = [v.class_name for v in error_violations]
        assert "UserAuth" in violation_classes
        assert "UserData" in violation_classes

    def test_valid_enum_naming(self, temp_repo):
        """Test validation of correctly named enum files and classes."""
        enums_dir = temp_repo / "src" / "omnibase_core" / "enums"
        enums_dir.mkdir(parents=True)

        valid_enum_content = '''
from enum import Enum

class EnumWorkflowStatus(str, Enum):
    """Workflow status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"

class EnumPriority(str, Enum):
    """Priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
'''
        enum_file = enums_dir / "enum_workflow_status.py"
        enum_file.write_text(valid_enum_content)

        validator = NamingConventionValidator(temp_repo)
        validator.validate_naming_conventions()

        error_violations = [v for v in validator.violations if v.severity == "error"]
        assert len(error_violations) == 0

    def test_invalid_enum_naming(self, temp_repo):
        """Test detection of incorrectly named enum classes."""
        enums_dir = temp_repo / "src" / "omnibase_core" / "enums"
        enums_dir.mkdir(parents=True)

        invalid_enum_content = '''
from enum import Enum

class WorkflowStatus(str, Enum):  # Should be EnumWorkflowStatus
    """Workflow status enumeration."""
    PENDING = "pending"
    RUNNING = "running"

class StatusType(str, Enum):  # Should be EnumStatusType
    """Status type enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
'''
        enum_file = enums_dir / "enum_workflow_status.py"
        enum_file.write_text(invalid_enum_content)

        validator = NamingConventionValidator(temp_repo)
        is_valid = validator.validate_naming_conventions()

        error_violations = [v for v in validator.violations if v.severity == "error"]
        assert len(error_violations) >= 2
        assert is_valid is False

    def test_valid_protocol_naming(self, temp_repo):
        """Test validation of correctly named protocol files and classes."""
        protocols_dir = temp_repo / "src" / "omnibase_core" / "protocols"
        protocols_dir.mkdir(parents=True)

        valid_protocol_content = '''
from typing import Protocol

class ProtocolEventHandler(Protocol):
    """Event handling protocol."""
    def handle_event(self, event: dict) -> bool: ...

class ProtocolDataProcessor(Protocol):
    """Data processing protocol."""
    def process_data(self, data: dict) -> dict: ...
'''
        protocol_file = protocols_dir / "protocol_event_handler.py"
        protocol_file.write_text(valid_protocol_content)

        validator = NamingConventionValidator(temp_repo)
        validator.validate_naming_conventions()

        error_violations = [v for v in validator.violations if v.severity == "error"]
        assert len(error_violations) == 0

    def test_valid_service_naming(self, temp_repo):
        """Test validation of correctly named service files and classes."""
        services_dir = temp_repo / "src" / "omnibase_core" / "services"
        services_dir.mkdir(parents=True)

        valid_service_content = '''
class ServiceAuth:
    """Authentication service."""
    def authenticate(self, credentials: dict) -> bool:
        return True

class ServiceUserManager:
    """User management service."""
    def create_user(self, user_data: dict) -> str:
        return "user_id"
'''
        service_file = services_dir / "service_auth.py"
        service_file.write_text(valid_service_content)

        validator = NamingConventionValidator(temp_repo)
        validator.validate_naming_conventions()

        error_violations = [v for v in validator.violations if v.severity == "error"]
        assert len(error_violations) == 0

    def test_valid_node_naming(self, temp_repo):
        """Test validation of correctly named node files and classes."""
        nodes_dir = temp_repo / "src" / "omnibase_core" / "nodes"
        nodes_dir.mkdir(parents=True)

        valid_node_content = '''
class NodeUserDataCompute:
    """User data computation node."""
    def compute(self, input_data: dict) -> dict:
        return {"result": "processed"}

class NodeEffectNotification:
    """Notification effect node."""
    def execute_effect(self, data: dict) -> bool:
        return True
'''
        node_file = nodes_dir / "node_user_data_compute.py"
        node_file.write_text(valid_node_content)

        validator = NamingConventionValidator(temp_repo)
        validator.validate_naming_conventions()

        error_violations = [v for v in validator.violations if v.severity == "error"]
        assert len(error_violations) == 0

    def test_exception_patterns_ignored(self, temp_repo):
        """Test that exception patterns are properly ignored."""
        models_dir = temp_repo / "src" / "omnibase_core" / "models"
        models_dir.mkdir(parents=True)

        exception_content = '''
from pydantic import BaseModel

class _PrivateClass:  # Should be ignored (private)
    """Private class."""
    pass

@pytest.mark.unit
class TestUserModel:  # Should be ignored (test class)
    """Test class."""
    pass

class UserModelTest:  # Should be ignored (test class)
    """Test class."""
    pass

class ModelUser(BaseModel):  # Should be detected as valid
    """Proper model."""
    user_id: str
'''
        model_file = models_dir / "model_user.py"
        model_file.write_text(exception_content)

        validator = NamingConventionValidator(temp_repo)
        validator.validate_naming_conventions()

        # Should not flag exception patterns
        error_violations = [v for v in validator.violations if v.severity == "error"]
        violation_classes = [v.class_name for v in error_violations]

        assert "_PrivateClass" not in violation_classes
        assert "TestUserModel" not in violation_classes
        assert "UserModelTest" not in violation_classes

    def test_file_naming_validation(self, temp_repo):
        """Test validation of file naming conventions."""
        models_dir = temp_repo / "src" / "omnibase_core" / "models"
        models_dir.mkdir(parents=True)

        # Create file with incorrect name but valid class
        model_content = '''
from pydantic import BaseModel

class ModelUserAuth(BaseModel):
    """User authentication model."""
    user_id: str
'''
        # File should be named model_*.py
        bad_file = models_dir / "user_auth.py"
        bad_file.write_text(model_content)

        validator = NamingConventionValidator(temp_repo)
        validator.validate_naming_conventions()

        # Should warn about file naming
        warning_violations = [
            v for v in validator.violations if v.severity == "warning"
        ]
        file_naming_warnings = [
            v for v in warning_violations if "(file name)" in v.class_name
        ]
        assert len(file_naming_warnings) >= 1

    def test_directory_organization_validation(self, temp_repo):
        """Test validation of directory organization."""
        # Create class in wrong directory
        wrong_dir = temp_repo / "src" / "omnibase_core" / "utils"
        wrong_dir.mkdir(parents=True)

        model_content = '''
from pydantic import BaseModel

class ModelUserAuth(BaseModel):  # Model class but not in models/ directory
    """User authentication model."""
    user_id: str
'''
        model_file = wrong_dir / "model_user_auth.py"
        model_file.write_text(model_content)

        validator = NamingConventionValidator(temp_repo)
        validator.validate_naming_conventions()

        # Should warn about wrong directory
        warning_violations = [
            v for v in validator.violations if v.severity == "warning"
        ]
        directory_warnings = [
            v for v in warning_violations if "directory" in v.description.lower()
        ]
        assert len(directory_warnings) >= 1


@pytest.mark.unit
class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_file_handling(self, temp_repo):
        """Test handling of empty files."""
        models_dir = temp_repo / "src" / "omnibase_core" / "models"
        models_dir.mkdir(parents=True)

        # Create empty file
        empty_file = models_dir / "model_empty.py"
        empty_file.touch()

        validator = NamingConventionValidator(temp_repo)
        validator.validate_naming_conventions()

        # Should not crash and should not generate violations for empty files
        error_violations = [v for v in validator.violations if v.severity == "error"]
        empty_file_violations = [
            v for v in error_violations if "model_empty.py" in v.file_path
        ]
        assert len(empty_file_violations) == 0

    def test_syntax_error_handling(self, temp_repo):
        """Test handling of files with syntax errors."""
        models_dir = temp_repo / "src" / "omnibase_core" / "models"
        models_dir.mkdir(parents=True)

        # Create file with syntax error
        syntax_error_content = """
from pydantic import BaseModel

class ModelUser(BaseModel:  # Missing closing parenthesis
    user_id: str
    # Missing closing quote and other syntax errors
    name: str = "default
"""
        error_file = models_dir / "model_syntax_error.py"
        error_file.write_text(syntax_error_content)

        validator = NamingConventionValidator(temp_repo)
        # Should not raise exception
        validator.validate_naming_conventions()

        # May or may not generate violations, but should not crash
        assert isinstance(validator.violations, list)

    def test_unicode_file_handling(self, temp_repo):
        """Test handling of files with various Unicode characters."""
        models_dir = temp_repo / "src" / "omnibase_core" / "models"
        models_dir.mkdir(parents=True)

        unicode_content = '''# -*- coding: utf-8 -*-
"""Model with Unicode characters: 中文, emoji 🚀, special chars ñáéíóú"""

from pydantic import BaseModel

class ModelUserProfile(BaseModel):
    """User profile with Unicode support."""
    name: str  # Can contain: José, 北京, 🎉
    description: str
'''
        unicode_file = models_dir / "model_unicode.py"
        unicode_file.write_text(unicode_content, encoding="utf-8")

        validator = NamingConventionValidator(temp_repo)
        # Should handle Unicode properly
        validator.validate_naming_conventions()

        error_violations = [v for v in validator.violations if v.severity == "error"]
        unicode_violations = [
            v for v in error_violations if "model_unicode.py" in v.file_path
        ]
        assert len(unicode_violations) == 0

    def test_large_file_performance(self, temp_repo):
        """Test performance with large files."""
        import time

        models_dir = temp_repo / "src" / "omnibase_core" / "models"
        models_dir.mkdir(parents=True)

        # Create large file with many classes
        large_content = """
from pydantic import BaseModel

"""
        # Add many valid model classes
        for i in range(50):
            large_content += f'''
class ModelTest{i:03d}(BaseModel):
    """Test model {i}."""
    field_{i}: str
    data_{i}: int = {i}

'''

        large_file = models_dir / "model_large.py"
        large_file.write_text(large_content)

        start_time = time.time()
        validator = NamingConventionValidator(temp_repo)
        validator.validate_naming_conventions()
        end_time = time.time()

        # Should complete within reasonable time (less than 5 seconds)
        assert end_time - start_time < 5.0

        # Should not generate errors for valid classes
        error_violations = [v for v in validator.violations if v.severity == "error"]
        large_file_errors = [
            v for v in error_violations if "model_large.py" in v.file_path
        ]
        assert len(large_file_errors) == 0

    def test_nonexistent_repository(self):
        """Test behavior with non-existent repository path."""
        nonexistent_path = Path("/nonexistent/path")
        validator = NamingConventionValidator(nonexistent_path)

        # Should not crash
        validator.validate_naming_conventions()
        assert isinstance(validator.violations, list)

    def test_permission_error_handling(self, temp_repo):
        """Test handling of permission errors."""
        with patch("builtins.open", side_effect=PermissionError("Permission denied")):
            validator = NamingConventionValidator(temp_repo)
            # Should not crash
            validator.validate_naming_conventions()
            assert isinstance(validator.violations, list)


@pytest.mark.unit
class TestPatternMatching:
    """Test pattern matching logic."""

    def test_should_match_pattern_heuristics(self, naming_validator):
        """Test the heuristic logic for determining if a class should match patterns."""
        # Test model heuristics
        assert naming_validator._should_match_pattern("UserModel", "models")
        assert naming_validator._should_match_pattern("DataSchema", "models")
        assert naming_validator._should_match_pattern("UserEntity", "models")

        # Test enum heuristics
        assert naming_validator._should_match_pattern("StatusEnum", "enums")
        assert naming_validator._should_match_pattern("WorkflowType", "enums")
        assert naming_validator._should_match_pattern("PriorityChoice", "enums")

        # Test protocol heuristics
        assert naming_validator._should_match_pattern("EventInterface", "protocols")
        assert naming_validator._should_match_pattern("DataContract", "protocols")

        # Test service heuristics
        assert naming_validator._should_match_pattern("AuthManager", "services")
        assert naming_validator._should_match_pattern("DataProcessor", "services")

        # Test node heuristics
        assert naming_validator._should_match_pattern("ComputeNode", "nodes")
        assert naming_validator._should_match_pattern("EffectHandler", "nodes")
        assert naming_validator._should_match_pattern("DataReducer", "nodes")

        # Test negative cases
        assert not naming_validator._should_match_pattern("RandomClass", "models")
        assert not naming_validator._should_match_pattern("UtilityHelper", "enums")

    def test_exception_class_detection(self, naming_validator):
        """Test detection of exception patterns."""
        # Private classes
        assert naming_validator._is_exception_class("_PrivateClass")
        assert naming_validator._is_exception_class("_internal_helper")

        # Test classes
        assert naming_validator._is_exception_class("TestUserModel")
        assert naming_validator._is_exception_class("UserModelTest")
        assert naming_validator._is_exception_class("TestCase")

        # Normal classes
        assert not naming_validator._is_exception_class("ModelUser")
        assert not naming_validator._is_exception_class("EnumStatus")
        assert not naming_validator._is_exception_class("ServiceAuth")


@pytest.mark.unit
class TestReportGeneration:
    """Test report generation functionality."""

    def test_generate_report_no_violations(self, naming_validator):
        """Test report generation with no violations."""
        report = naming_validator.generate_report()
        assert "All naming conventions are compliant" in report

    def test_generate_report_with_violations(self, temp_repo):
        """Test report generation with violations."""
        # Create violations
        validator = NamingConventionValidator(temp_repo)
        validator.violations = [
            NamingViolation(
                file_path="test/file.py",
                line_number=10,
                class_name="BadClass",
                expected_pattern="^Model.*$",
                description="Test violation",
                severity="error",
            ),
            NamingViolation(
                file_path="test/file2.py",
                line_number=20,
                class_name="WarningClass",
                expected_pattern="^Model.*$",
                description="Test warning",
                severity="warning",
            ),
        ]

        report = validator.generate_report()
        assert "NAMING ERRORS" in report
        assert "NAMING WARNINGS" in report
        assert "BadClass" in report
        assert "WarningClass" in report
        assert "NAMING CONVENTION REFERENCE" in report

    def test_report_includes_reference(self, naming_validator):
        """Test that report includes naming convention reference."""
        # Add a violation to trigger full report
        naming_validator.violations = [
            NamingViolation(
                file_path="test.py",
                line_number=1,
                class_name="Test",
                expected_pattern="^Model.*$",
                description="Test",
                severity="error",
            ),
        ]

        report = naming_validator.generate_report()
        assert "NAMING CONVENTION REFERENCE" in report
        assert "Models:" in report
        assert "Protocols:" in report
        assert "Enums:" in report


@pytest.mark.unit
class TestMainFunction:
    """Test the main function and CLI interface."""

    def test_main_with_valid_repository(self, temp_repo):
        """Test main function with a valid repository."""
        with patch("sys.argv", ["validate_naming.py", str(temp_repo)]):
            try:
                result = main()
                assert result in [0, 1]  # Valid exit codes
            except SystemExit as e:
                assert e.code in [0, 1]

    def test_main_with_nonexistent_repository(self):
        """Test main function with non-existent repository."""
        with patch("sys.argv", ["validate_naming.py", "/nonexistent/path"]):
            try:
                result = main()
                assert result == 1  # Should fail
            except SystemExit as e:
                assert e.code == 1

    def test_main_with_verbose_output(self, temp_repo):
        """Test main function with verbose output."""
        with patch("sys.argv", ["validate_naming.py", str(temp_repo), "--verbose"]):
            with patch("builtins.print") as mock_print:
                try:
                    main()
                except SystemExit:
                    pass

                # Should have printed something (exact content may vary)
                assert mock_print.called


@pytest.mark.unit
class TestFixtureValidation:
    """Test validation using our test fixtures."""

    def test_valid_fixtures_pass_naming_validation(self):
        """Test that valid fixtures pass naming validation."""
        fixtures_dir = Path(__file__).parent.parent.parent / "fixtures" / "validation"

        if fixtures_dir.exists():
            # Test with valid fixtures
            valid_fixtures = fixtures_dir / "valid"
            if valid_fixtures.exists():
                validator = NamingConventionValidator(fixtures_dir)
                validator.validate_naming_conventions()

                # Filter violations to only those from valid fixtures
                valid_violations = [
                    v
                    for v in validator.violations
                    if v.severity == "error" and "/valid/" in v.file_path
                ]
                assert len(valid_violations) == 0

    def test_invalid_fixtures_trigger_violations(self):
        """Test that invalid fixtures trigger naming violations."""
        fixtures_dir = Path(__file__).parent.parent.parent / "fixtures" / "validation"

        if fixtures_dir.exists():
            # Test with invalid fixtures
            invalid_fixtures = fixtures_dir / "invalid"
            if invalid_fixtures.exists():
                validator = NamingConventionValidator(fixtures_dir)
                validator.validate_naming_conventions()

                # Should find violations in invalid fixtures
                invalid_violations = [
                    v
                    for v in validator.violations
                    if v.severity == "error" and "/invalid/" in v.file_path
                ]
                assert len(invalid_violations) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
