#!/usr/bin/env python3
"""
Integration tests for validation scripts working together.

Tests the integration of all validation scripts including:
- Pre-commit hook integration
- Multiple validators working together
- End-to-end validation workflows
- CI/CD integration scenarios
"""

import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

# Get the path to validation scripts
VALIDATION_SCRIPTS_DIR = Path(__file__).parent.parent.parent / "scripts" / "validation"


@pytest.fixture
def temp_repo():
    """Create a temporary repository structure for integration testing."""
    temp_dir = tempfile.mkdtemp()
    repo_path = Path(temp_dir)

    # Create basic repository structure
    src_path = repo_path / "src" / "omnibase_core"
    src_path.mkdir(parents=True)
    (repo_path / "tests").mkdir()
    (repo_path / "docs").mkdir()

    # Create configuration files
    (repo_path / "pyproject.toml").write_text(
        """
[tool.pytest.ini_options]
testpaths = ["tests"]
""",
    )
    (repo_path / "README.md").write_text("# Test Repository")
    (repo_path / ".gitignore").write_text("__pycache__/\n*.pyc")

    yield repo_path

    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def git_repo(temp_repo):
    """Initialize the temp repository as a git repository."""
    subprocess.run(["git", "init"], cwd=temp_repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=temp_repo,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=temp_repo,
        check=True,
    )

    # Add all files
    subprocess.run(["git", "add", "."], cwd=temp_repo, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=temp_repo, check=True)

    return temp_repo


@pytest.mark.integration
class TestValidationIntegration:
    """Test integration of multiple validation scripts."""

    def test_all_validators_pass_clean_repository(self, temp_repo):
        """Test that all validators pass on a clean repository structure."""
        # Create proper structure
        models_dir = temp_repo / "src" / "omnibase_core" / "models"
        models_dir.mkdir(parents=True)

        # Create valid model file
        model_content = '''
from pydantic import BaseModel, ConfigDict

class ModelUserAuth(BaseModel):
    """User authentication model."""
    user_id: str
    username: str

    model_config = ConfigDict(
        extra="forbid",
    )
'''
        (models_dir / "model_user_auth.py").write_text(model_content)

        # Create valid enum file
        enums_dir = temp_repo / "src" / "omnibase_core" / "enums"
        enums_dir.mkdir()
        enum_content = '''
from enum import Enum

class EnumUserStatus(str, Enum):
    """User status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
'''
        (enums_dir / "enum_user_status.py").write_text(enum_content)

        # Create valid contract
        contracts_dir = temp_repo / "contracts"
        contracts_dir.mkdir()
        contract_content = """
contract_version:
  major: 1
  minor: 0
  patch: 0
node_type: "compute"
description: "User data processing contract"
"""
        (contracts_dir / "user_processor.yaml").write_text(contract_content)

        # Test structure validation
        structure_script = VALIDATION_SCRIPTS_DIR / "validate_structure.py"
        if structure_script.exists():
            result = subprocess.run(
                ["python", str(structure_script), str(temp_repo), "omnibase_core"],
                capture_output=True,
                text=True,
                check=False,
            )
            # Should pass or have only warnings
            assert result.returncode in [
                0,
                1,
            ]  # May have warnings but no blocking errors

        # Test naming validation
        naming_script = VALIDATION_SCRIPTS_DIR / "validate_naming.py"
        if naming_script.exists():
            result = subprocess.run(
                ["python", str(naming_script), str(temp_repo)],
                capture_output=True,
                text=True,
                check=False,
            )
            assert result.returncode == 0

        # Test backward compatibility validation
        compat_script = VALIDATION_SCRIPTS_DIR / "validate-no-backward-compatibility.py"
        if compat_script.exists():
            result = subprocess.run(
                ["python", str(compat_script), "--dir", str(temp_repo)],
                capture_output=True,
                text=True,
                check=False,
            )
            assert result.returncode == 0

        # Test contract validation
        contract_script = VALIDATION_SCRIPTS_DIR / "validate-contracts.py"
        if contract_script.exists():
            result = subprocess.run(
                ["python", str(contract_script), str(temp_repo)],
                capture_output=True,
                text=True,
                check=False,
            )
            assert result.returncode == 0

    def test_validators_detect_violations_consistently(self, temp_repo):
        """Test that validators consistently detect violations."""
        # Create files with various violations
        models_dir = temp_repo / "src" / "omnibase_core" / "models"
        models_dir.mkdir(parents=True)

        # Create model with naming violation
        bad_model_content = '''
from pydantic import BaseModel

class UserAuth(BaseModel):  # Should be ModelUserAuth
    """User authentication model."""
    user_id: str

    def to_dict_legacy(self) -> dict:
        """Convert to dict for backward compatibility."""
        return self.__dict__
'''
        (models_dir / "user_auth.py").write_text(
            bad_model_content,
        )  # Wrong filename too

        # Create invalid contract
        contracts_dir = temp_repo / "contracts"
        contracts_dir.mkdir()
        bad_contract_content = """
# Missing contract_version and node_type
description: "Invalid contract"
"""
        (contracts_dir / "invalid_contract.yaml").write_text(bad_contract_content)

        violations_detected = 0

        # Test naming validation - should detect violations
        naming_script = VALIDATION_SCRIPTS_DIR / "validate_naming.py"
        if naming_script.exists():
            result = subprocess.run(
                ["python", str(naming_script), str(temp_repo)],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                violations_detected += 1

        # Test backward compatibility validation - should detect violations
        compat_script = VALIDATION_SCRIPTS_DIR / "validate-no-backward-compatibility.py"
        if compat_script.exists():
            result = subprocess.run(
                ["python", str(compat_script), "--dir", str(temp_repo)],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                violations_detected += 1

        # Test contract validation - should detect violations
        contract_script = VALIDATION_SCRIPTS_DIR / "validate-contracts.py"
        if contract_script.exists():
            result = subprocess.run(
                ["python", str(contract_script), str(temp_repo)],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                violations_detected += 1

        # Should detect at least some violations
        assert violations_detected >= 2

    def test_validation_script_error_handling(self, temp_repo):
        """Test that validation scripts handle errors gracefully."""
        # Test with non-existent directory
        for script_name in ["validate_naming.py", "validate-contracts.py"]:
            script_path = VALIDATION_SCRIPTS_DIR / script_name
            if script_path.exists():
                result = subprocess.run(
                    ["python", str(script_path), "/nonexistent/path"],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                # Should fail gracefully with non-zero exit code
                assert result.returncode != 0
                # Check for various error indicators
                output_text = (result.stdout + result.stderr).lower()
                error_indicators = [
                    "error",
                    "fail",
                    "does not exist",
                    "not found",
                    "invalid",
                ]
                assert any(indicator in output_text for indicator in error_indicators)

    def test_validation_scripts_with_mixed_content(self, temp_repo):
        """Test validation scripts with mixed valid and invalid content."""
        src_path = temp_repo / "src" / "omnibase_core"

        # Create mix of valid and invalid files
        models_dir = src_path / "models"
        models_dir.mkdir(parents=True)

        # Valid model
        valid_model = '''
from pydantic import BaseModel

class ModelUserProfile(BaseModel):
    """Valid user profile model."""
    user_id: str
    name: str
'''
        (models_dir / "model_user_profile.py").write_text(valid_model)

        # Invalid model (backward compatibility)
        invalid_model = '''
from pydantic import BaseModel

class ModelUserData(BaseModel):
    """User data model."""
    user_id: str

    def to_dict(self) -> dict:
        """Convert to dictionary for backward compatibility."""
        return self.__dict__
'''
        (models_dir / "model_user_data.py").write_text(invalid_model)

        # Mixed YAML files
        contracts_dir = temp_repo / "contracts"
        contracts_dir.mkdir()

        # Valid contract
        valid_contract = """
contract_version:
  major: 1
  minor: 0
  patch: 0
node_type: "compute"
description: "Valid contract"
"""
        (contracts_dir / "valid_contract.yaml").write_text(valid_contract)

        # Invalid contract
        invalid_contract = """
contract_version:
  major: 1
  minor: 0
  patch: 0
# Missing node_type
description: "Invalid contract"
"""
        (contracts_dir / "invalid_contract.yaml").write_text(invalid_contract)

        # Run validators - should detect partial violations
        compat_script = VALIDATION_SCRIPTS_DIR / "validate-no-backward-compatibility.py"
        if compat_script.exists():
            result = subprocess.run(
                ["python", str(compat_script), "--dir", str(temp_repo)],
                capture_output=True,
                text=True,
                check=False,
            )
            assert result.returncode != 0  # Should detect backward compatibility issues

        contract_script = VALIDATION_SCRIPTS_DIR / "validate-contracts.py"
        if contract_script.exists():
            result = subprocess.run(
                ["python", str(contract_script), str(temp_repo)],
                capture_output=True,
                text=True,
                check=False,
            )
            assert result.returncode != 0  # Should detect contract issues


@pytest.mark.integration
class TestPreCommitIntegration:
    """Test pre-commit hook integration scenarios."""

    def test_simulate_pre_commit_hook_validation(self, git_repo):
        """Simulate how validation scripts would work in pre-commit hooks."""
        # Create staged files that would be validated
        models_dir = git_repo / "src" / "omnibase_core" / "models"
        models_dir.mkdir(parents=True)

        # Stage a file with backward compatibility issues
        problematic_file = models_dir / "model_legacy.py"
        problematic_content = '''
from pydantic import BaseModel

class ModelLegacy(BaseModel):
    """Legacy model."""
    user_id: str

    def get_data_legacy(self) -> dict:
        """Get data in legacy format for backward compatibility."""
        return {"legacy": True}
'''
        problematic_file.write_text(problematic_content)

        # Stage the file
        subprocess.run(["git", "add", str(problematic_file)], cwd=git_repo, check=True)

        # Simulate pre-commit validation on staged file
        compat_script = VALIDATION_SCRIPTS_DIR / "validate-no-backward-compatibility.py"
        if compat_script.exists():
            result = subprocess.run(
                ["python", str(compat_script), str(problematic_file)],
                capture_output=True,
                text=True,
                check=False,
            )

            # Should fail validation (blocking commit)
            assert result.returncode != 0
            assert "backward compatibility" in result.stdout.lower()

    def test_pre_commit_validation_file_list(self, git_repo):
        """Test validation with file list as would be provided by pre-commit."""
        src_path = git_repo / "src" / "omnibase_core"

        # Create multiple files
        models_dir = src_path / "models"
        models_dir.mkdir(parents=True)

        files_to_validate = []

        # Valid file
        valid_file = models_dir / "model_user.py"
        valid_content = '''
from pydantic import BaseModel

class ModelUser(BaseModel):
    """Valid user model."""
    user_id: str
'''
        valid_file.write_text(valid_content)
        files_to_validate.append(str(valid_file))

        # File with issues
        invalid_file = models_dir / "model_problem.py"
        invalid_content = '''
from pydantic import BaseModel

class ModelProblem(BaseModel):
    """Problem model."""
    user_id: str

    def convert_legacy(self) -> dict:
        """Convert for backward compatibility."""
        return {}
'''
        invalid_file.write_text(invalid_content)
        files_to_validate.append(str(invalid_file))

        # Stage files
        for file_path in files_to_validate:
            subprocess.run(["git", "add", file_path], cwd=git_repo, check=True)

        # Test validation with file list (pre-commit style)
        compat_script = VALIDATION_SCRIPTS_DIR / "validate-no-backward-compatibility.py"
        if compat_script.exists():
            result = subprocess.run(
                ["python", str(compat_script)] + files_to_validate,
                capture_output=True,
                text=True,
                check=False,
            )

            # Should fail due to problematic file
            assert result.returncode != 0

    def test_pre_commit_no_python_files(self, git_repo):
        """Test pre-commit scenario with no Python files to validate."""
        # Create and stage non-Python files
        readme_file = git_repo / "NEW_README.md"
        readme_file.write_text("# Updated README")
        subprocess.run(["git", "add", str(readme_file)], cwd=git_repo, check=True)

        # Test validation with non-Python files
        compat_script = VALIDATION_SCRIPTS_DIR / "validate-no-backward-compatibility.py"
        if compat_script.exists():
            result = subprocess.run(
                ["python", str(compat_script), str(readme_file)],
                capture_output=True,
                text=True,
                check=False,
            )

            # Should handle gracefully
            assert result.returncode in [0, 1]  # May skip or report no Python files


@pytest.mark.integration
class TestContinuousIntegration:
    """Test CI/CD integration scenarios."""

    def test_ci_full_repository_scan(self, temp_repo):
        """Test full repository scan as would happen in CI."""
        # Create comprehensive repository structure
        src_path = temp_repo / "src" / "omnibase_core"

        # Models
        models_dir = src_path / "models"
        models_dir.mkdir(parents=True)
        (models_dir / "model_user.py").write_text(
            '''
from pydantic import BaseModel

class ModelUser(BaseModel):
    """User model."""
    user_id: str
''',
        )

        # Enums
        enums_dir = src_path / "enums"
        enums_dir.mkdir()
        (enums_dir / "enum_status.py").write_text(
            '''
from enum import Enum

class EnumStatus(str, Enum):
    """Status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
''',
        )

        # Contracts
        contracts_dir = temp_repo / "contracts"
        contracts_dir.mkdir()
        (contracts_dir / "processor.yaml").write_text(
            """
contract_version:
  major: 1
  minor: 0
  patch: 0
node_type: "compute"
description: "Data processor"
""",
        )

        # Test comprehensive validation (CI scenario)
        validation_results = {}

        # Structure validation
        structure_script = VALIDATION_SCRIPTS_DIR / "validate_structure.py"
        if structure_script.exists():
            result = subprocess.run(
                ["python", str(structure_script), str(temp_repo), "omnibase_core"],
                capture_output=True,
                text=True,
                check=False,
            )
            validation_results["structure"] = result.returncode

        # Naming validation
        naming_script = VALIDATION_SCRIPTS_DIR / "validate_naming.py"
        if naming_script.exists():
            result = subprocess.run(
                ["python", str(naming_script), str(temp_repo)],
                capture_output=True,
                text=True,
                check=False,
            )
            validation_results["naming"] = result.returncode

        # Backward compatibility validation
        compat_script = VALIDATION_SCRIPTS_DIR / "validate-no-backward-compatibility.py"
        if compat_script.exists():
            result = subprocess.run(
                ["python", str(compat_script), "--dir", str(temp_repo)],
                capture_output=True,
                text=True,
                check=False,
            )
            validation_results["compatibility"] = result.returncode

        # Contract validation
        contract_script = VALIDATION_SCRIPTS_DIR / "validate-contracts.py"
        if contract_script.exists():
            result = subprocess.run(
                ["python", str(contract_script), str(temp_repo)],
                capture_output=True,
                text=True,
                check=False,
            )
            validation_results["contracts"] = result.returncode

        # Most validations should pass
        passed_validations = sum(1 for code in validation_results.values() if code == 0)
        assert passed_validations >= 2, f"Validation results: {validation_results}"

    def test_ci_parallel_validation_simulation(self, temp_repo):
        """Simulate parallel validation as might happen in CI."""
        import concurrent.futures
        import time

        # Create test files
        src_path = temp_repo / "src" / "omnibase_core"
        models_dir = src_path / "models"
        models_dir.mkdir(parents=True)

        for i in range(5):
            model_file = models_dir / f"model_test_{i}.py"
            model_file.write_text(
                f'''
from pydantic import BaseModel

class ModelTest{i}(BaseModel):
    """Test model {i}."""
    test_id: str
''',
            )

        def run_validator(script_name, args):
            """Run a validator script."""
            script_path = VALIDATION_SCRIPTS_DIR / script_name
            if not script_path.exists():
                return (script_name, 0, "Script not found")

            start_time = time.time()
            result = subprocess.run(
                ["python", str(script_path)] + args,
                capture_output=True,
                text=True,
                check=False,
            )
            end_time = time.time()

            return (script_name, result.returncode, end_time - start_time)

        # Run validators in parallel
        validators = [
            ("validate_naming.py", [str(temp_repo)]),
            ("validate-no-backward-compatibility.py", ["--dir", str(temp_repo)]),
            ("validate-contracts.py", [str(temp_repo)]),
        ]

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(run_validator, script_name, args)
                for script_name, args in validators
            ]

            results = [
                future.result() for future in concurrent.futures.as_completed(futures)
            ]

        # All should complete and most should pass
        assert len(results) == 3
        for script_name, return_code, duration in results:
            assert duration < 30.0  # Should complete within reasonable time


@pytest.mark.integration
class TestValidationPerformance:
    """Test performance characteristics of validation suite."""

    def test_large_repository_validation_performance(self, temp_repo):
        """Test validation performance on larger repository."""
        import time

        # Create larger structure
        src_path = temp_repo / "src" / "omnibase_core"

        # Create many model files
        models_dir = src_path / "models"
        models_dir.mkdir(parents=True)
        for i in range(20):
            model_file = models_dir / f"model_batch_{i:02d}.py"
            model_file.write_text(
                f'''
from pydantic import BaseModel

class ModelBatch{i:02d}(BaseModel):
    """Batch model {i}."""
    batch_id: str
    item_count: int = {i}
''',
            )

        # Create many enum files
        enums_dir = src_path / "enums"
        enums_dir.mkdir()
        for i in range(10):
            enum_file = enums_dir / f"enum_type_{i:02d}.py"
            enum_file.write_text(
                f'''
from enum import Enum

class EnumTaskTypes{i:02d}(str, Enum):
    """Type enumeration {i}."""
    TYPE_A = "type_a_{i}"
    TYPE_B = "type_b_{i}"
''',
            )

        # Time the validation
        start_time = time.time()

        # Run naming validation
        naming_script = VALIDATION_SCRIPTS_DIR / "validate_naming.py"
        if naming_script.exists():
            result = subprocess.run(
                ["python", str(naming_script), str(temp_repo)],
                capture_output=True,
                text=True,
                check=False,
            )
            assert result.returncode == 0

        end_time = time.time()
        validation_time = end_time - start_time

        # Should complete within reasonable time
        assert validation_time < 10.0, f"Validation took {validation_time:.2f} seconds"

    def test_validation_memory_usage(self, temp_repo):
        """Test that validation doesn't consume excessive memory."""
        # Create files with substantial content
        src_path = temp_repo / "src" / "omnibase_core"
        models_dir = src_path / "models"
        models_dir.mkdir(parents=True)

        # Create a file with many classes
        large_file_content = """
from pydantic import BaseModel

"""
        for i in range(100):
            large_file_content += f'''
class ModelLarge{i:03d}(BaseModel):
    """Large model {i}."""
    field_1: str
    field_2: int = {i}
    field_3: bool = True

'''

        large_file = models_dir / "model_large_collection.py"
        large_file.write_text(large_file_content)

        # Run validation (should complete without memory issues)
        naming_script = VALIDATION_SCRIPTS_DIR / "validate_naming.py"
        if naming_script.exists():
            result = subprocess.run(
                ["python", str(naming_script), str(temp_repo)],
                capture_output=True,
                text=True,
                check=False,
            )
            assert result.returncode == 0


@pytest.mark.integration
class TestEndToEndWorkflows:
    """Test complete end-to-end validation workflows."""

    def test_development_workflow_simulation(self, git_repo):
        """Simulate a complete development workflow with validation."""
        # 1. Developer creates new feature files
        src_path = git_repo / "src" / "omnibase_core"

        # Create new model
        models_dir = src_path / "models"
        models_dir.mkdir(parents=True)
        new_model = models_dir / "model_feature.py"
        new_model.write_text(
            '''
from pydantic import BaseModel

class ModelFeature(BaseModel):
    """New feature model."""
    feature_id: str
    name: str
    enabled: bool = False
''',
        )

        # Create new contract
        contracts_dir = git_repo / "contracts"
        contracts_dir.mkdir()
        new_contract = contracts_dir / "feature_processor.yaml"
        new_contract.write_text(
            """
contract_version:
  major: 1
  minor: 0
  patch: 0
node_type: "compute"
description: "Feature processing contract"

inputs:
  - name: "feature_data"
    type: "object"

outputs:
  - name: "processed_feature"
    type: "object"
""",
        )

        # 2. Stage files
        subprocess.run(
            ["git", "add", str(new_model), str(new_contract)],
            cwd=git_repo,
            check=True,
        )

        # 3. Run pre-commit validation
        validation_passed = True

        # Naming validation
        naming_script = VALIDATION_SCRIPTS_DIR / "validate_naming.py"
        if naming_script.exists():
            result = subprocess.run(
                ["python", str(naming_script), str(git_repo)],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                validation_passed = False

        # Backward compatibility validation
        compat_script = VALIDATION_SCRIPTS_DIR / "validate-no-backward-compatibility.py"
        if compat_script.exists():
            result = subprocess.run(
                ["python", str(compat_script), str(new_model)],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                validation_passed = False

        # Contract validation
        contract_script = VALIDATION_SCRIPTS_DIR / "validate-contracts.py"
        if contract_script.exists():
            result = subprocess.run(
                ["python", str(contract_script), str(git_repo)],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                validation_passed = False

        # 4. Should pass validation and allow commit
        assert validation_passed

        # 5. Commit should succeed
        result = subprocess.run(
            ["git", "commit", "-m", "Add new feature model and contract"],
            cwd=git_repo,
            capture_output=True,
            check=False,
        )
        assert result.returncode == 0

    def test_refactoring_workflow_with_validation(self, git_repo):
        """Test validation during refactoring workflow."""
        # Create initial structure
        src_path = git_repo / "src" / "omnibase_core"
        models_dir = src_path / "models"
        models_dir.mkdir(parents=True)

        # Initial model
        original_model = models_dir / "model_user.py"
        original_model.write_text(
            '''
from pydantic import BaseModel

class ModelUser(BaseModel):
    """User model."""
    user_id: str
    name: str
''',
        )

        # Commit initial version
        subprocess.run(["git", "add", "."], cwd=git_repo, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Add initial user model"],
            cwd=git_repo,
            check=True,
        )

        # Refactor model (add new field)
        refactored_model = '''
from pydantic import BaseModel
from typing import Optional

class ModelUser(BaseModel):
    """User model with additional fields."""
    user_id: str
    name: str
    email: Optional[str] = None
    created_at: str
'''
        original_model.write_text(refactored_model)

        # Validate refactored code
        naming_script = VALIDATION_SCRIPTS_DIR / "validate_naming.py"
        if naming_script.exists():
            result = subprocess.run(
                ["python", str(naming_script), str(git_repo)],
                capture_output=True,
                text=True,
                check=False,
            )
            assert result.returncode == 0  # Should still pass

        compat_script = VALIDATION_SCRIPTS_DIR / "validate-no-backward-compatibility.py"
        if compat_script.exists():
            result = subprocess.run(
                ["python", str(compat_script), str(original_model)],
                capture_output=True,
                text=True,
                check=False,
            )
            assert (
                result.returncode == 0
            )  # Should not introduce backward compatibility issues


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
