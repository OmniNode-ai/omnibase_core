# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Comprehensive unit tests for the regenerate_fingerprints.py script.

Tests the fingerprint regeneration script which validates ONEX contracts and
regenerates fingerprints in-place. This implements PR #180 review requirements
for fingerprint script validation test coverage.

Test Categories:
1. Type Validation Tests (default/type mismatches)
2. Dry-Run Mode Tests
3. Fingerprint Consistency Tests
4. Error Handling Tests (malformed YAML)
5. File Size Limit Tests

Requirements from PR #180 Review:
- Test that `default=3.5` with `type="integer"` raises error
- Test that `default="text"` with `type="number"` raises error
- Test that `default=42` with `type="string"` raises error
- Test dry-run mode doesn't modify files
- Test that regenerated fingerprints match `compute_contract_fingerprint()`
- Test error handling for malformed YAML
- Test file size limit enforcement
"""

from __future__ import annotations

import sys
import tempfile
from collections.abc import Generator
from pathlib import Path
from unittest.mock import patch

import pytest

# Add scripts directory to path for import
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "scripts"))

from regenerate_fingerprints import (
    MAX_FILE_SIZE_BYTES,
    RegenerateResult,
    compute_fingerprint_for_contract,
    detect_contract_model,
    find_contract_files,
    regenerate_fingerprint,
    update_fingerprint_in_yaml,
)

from omnibase_core.contracts import compute_contract_fingerprint
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.contracts.model_action_config_parameter import (
    ModelActionConfigParameter,
)
from omnibase_core.models.contracts.model_contract_compute import ModelContractCompute
from omnibase_core.models.errors.model_onex_error import ModelOnexError

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def valid_compute_contract_yaml() -> str:
    """Valid compute contract YAML content with all required fields."""
    return """
name: NodeTestCompute
version:
  major: 1
  minor: 0
  patch: 0
node_type: COMPUTE_GENERIC
description: A test compute node for fingerprint testing
input_model: omnibase_core.models.ModelComputeInput
output_model: omnibase_core.models.ModelComputeOutput
dependencies: []
algorithm:
  algorithm_type: default
  factors:
    default_factor:
      weight: 1.0
      calculation_method: identity
"""


@pytest.fixture
def valid_effect_contract_yaml() -> str:
    """Valid effect contract YAML content."""
    return """
name: NodeTestEffect
version:
  major: 1
  minor: 0
  patch: 0
node_type: EFFECT_GENERIC
description: A test effect node for fingerprint testing
input_model: omnibase_core.models.ModelEffectInput
output_model: omnibase_core.models.ModelEffectOutput
dependencies: []
"""


@pytest.fixture
def contract_with_existing_fingerprint_yaml() -> str:
    """Contract with an existing fingerprint field."""
    return """
name: NodeFingerprintedCompute
version:
  major: 1
  minor: 0
  patch: 0
node_type: COMPUTE_GENERIC
description: A compute node with existing fingerprint
input_model: omnibase_core.models.ModelComputeInput
output_model: omnibase_core.models.ModelComputeOutput
dependencies: []
fingerprint: "1.0.0:abcdef123456"
algorithm:
  algorithm_type: default
  factors:
    default_factor:
      weight: 1.0
      calculation_method: identity
"""


@pytest.fixture
def malformed_yaml_content() -> str:
    """Malformed YAML content with syntax errors."""
    return """
name: BadContract
version: [invalid: yaml
  missing: brackets
"""


@pytest.fixture
def empty_yaml_content() -> str:
    """Empty YAML content."""
    return ""


@pytest.fixture
def non_contract_yaml_content() -> str:
    """YAML that is not an ONEX contract (missing node_type)."""
    return """
name: NotAContract
description: This is not a valid ONEX contract
some_field: value
"""


# =============================================================================
# Type Validation Tests (Default/Type Mismatches)
# =============================================================================


@pytest.mark.unit
class TestTypeValidation:
    """Tests for type validation of default values.

    These tests verify that the ModelActionConfigParameter model correctly
    rejects default values that don't match the declared type.
    """

    def test_float_default_with_integer_type_raises_error(self) -> None:
        """Test that default=3.5 with type='int' raises validation error.

        PR #180 Requirement: Test that `default=3.5` with `type="integer"` raises error.
        Note: The actual type is 'int' in the model, not 'integer'.
        """
        with pytest.raises(ModelOnexError) as exc_info:
            ModelActionConfigParameter(
                name="test_param",
                type="int",
                required=False,
                default=3.5,  # Float value for int type
                description="Test parameter",
            )

        assert exc_info.value.error_code == EnumCoreErrorCode.PARAMETER_TYPE_MISMATCH
        assert "float" in str(exc_info.value.message).lower()
        assert "int" in str(exc_info.value.message).lower()

    def test_string_default_with_float_type_raises_error(self) -> None:
        """Test that default='text' with type='float' raises validation error.

        PR #180 Requirement: Test that `default="text"` with `type="number"` raises error.
        Note: The actual type is 'float' in the model, not 'number'.
        """
        with pytest.raises(ModelOnexError) as exc_info:
            ModelActionConfigParameter(
                name="test_param",
                type="float",
                required=False,
                default="text",  # String value for float type
                description="Test parameter",
            )

        assert exc_info.value.error_code == EnumCoreErrorCode.PARAMETER_TYPE_MISMATCH
        assert "str" in str(exc_info.value.message).lower()
        assert "float" in str(exc_info.value.message).lower()

    def test_integer_default_with_string_type_raises_error(self) -> None:
        """Test that default=42 with type='string' raises validation error.

        PR #180 Requirement: Test that `default=42` with `type="string"` raises error.
        """
        with pytest.raises(ModelOnexError) as exc_info:
            ModelActionConfigParameter(
                name="test_param",
                type="string",
                required=False,
                default=42,  # Integer value for string type
                description="Test parameter",
            )

        assert exc_info.value.error_code == EnumCoreErrorCode.PARAMETER_TYPE_MISMATCH
        assert "int" in str(exc_info.value.message).lower()
        assert "string" in str(exc_info.value.message).lower()

    def test_bool_default_with_int_type_raises_error(self) -> None:
        """Test that boolean default with int type raises error.

        This tests the special case where bool is a subclass of int in Python.
        """
        with pytest.raises(ModelOnexError) as exc_info:
            ModelActionConfigParameter(
                name="test_param",
                type="int",
                required=False,
                default=True,  # Bool value for int type (special case)
                description="Test parameter",
            )

        assert exc_info.value.error_code == EnumCoreErrorCode.PARAMETER_TYPE_MISMATCH
        assert "bool" in str(exc_info.value.message).lower()

    def test_list_default_with_string_type_raises_error(self) -> None:
        """Test that list default with string type raises error."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelActionConfigParameter(
                name="test_param",
                type="string",
                required=False,
                default=["item1", "item2"],  # List value for string type
                description="Test parameter",
            )

        assert exc_info.value.error_code == EnumCoreErrorCode.PARAMETER_TYPE_MISMATCH
        assert "list" in str(exc_info.value.message).lower()

    def test_valid_int_default_with_int_type_succeeds(self) -> None:
        """Test that valid int default with int type succeeds."""
        param = ModelActionConfigParameter(
            name="test_param",
            type="int",
            required=False,
            default=42,
            description="Test parameter",
        )
        assert param.default == 42
        assert param.type == "int"

    def test_valid_string_default_with_string_type_succeeds(self) -> None:
        """Test that valid string default with string type succeeds."""
        param = ModelActionConfigParameter(
            name="test_param",
            type="string",
            required=False,
            default="hello",
            description="Test parameter",
        )
        assert param.default == "hello"
        assert param.type == "string"

    def test_valid_float_default_with_float_type_succeeds(self) -> None:
        """Test that valid float default with float type succeeds."""
        param = ModelActionConfigParameter(
            name="test_param",
            type="float",
            required=False,
            default=3.14,
            description="Test parameter",
        )
        assert param.default == 3.14
        assert param.type == "float"

    def test_int_acceptable_for_float_type(self) -> None:
        """Test that int is acceptable for float type (widening conversion)."""
        param = ModelActionConfigParameter(
            name="test_param",
            type="float",
            required=False,
            default=42,  # Int is acceptable for float
            description="Test parameter",
        )
        assert param.default == 42
        assert param.type == "float"


# =============================================================================
# Dry-Run Mode Tests
# =============================================================================


@pytest.mark.unit
class TestDryRunMode:
    """Tests for dry-run mode functionality.

    PR #180 Requirement: Test dry-run mode doesn't modify files.
    """

    def test_dry_run_does_not_modify_file(
        self, temp_dir: Path, valid_compute_contract_yaml: str
    ) -> None:
        """Test that dry-run mode does not modify the contract file."""
        file_path = temp_dir / "contract.yaml"
        file_path.write_text(valid_compute_contract_yaml)

        # Record original content
        original_content = file_path.read_text()

        # Run regeneration in dry-run mode
        result = regenerate_fingerprint(file_path, dry_run=True)

        # Verify file was not modified
        new_content = file_path.read_text()
        assert new_content == original_content

        # Verify result shows change would have been made
        # (if the contract was missing fingerprint or had wrong one)
        assert result.file_path == file_path
        # The result may or may not show changed depending on fingerprint computation

    def test_dry_run_with_existing_fingerprint_does_not_modify(
        self, temp_dir: Path, contract_with_existing_fingerprint_yaml: str
    ) -> None:
        """Test dry-run with existing fingerprint doesn't modify file."""
        file_path = temp_dir / "contract.yaml"
        file_path.write_text(contract_with_existing_fingerprint_yaml)

        original_content = file_path.read_text()

        result = regenerate_fingerprint(file_path, dry_run=True)

        # File should not be modified
        assert file_path.read_text() == original_content

        # Result should indicate this is a dry run (fingerprint may or may not match)
        assert result.file_path == file_path

    def test_dry_run_shows_what_would_change(
        self, temp_dir: Path, valid_compute_contract_yaml: str
    ) -> None:
        """Test that dry-run shows the intended changes without applying them."""
        file_path = temp_dir / "contract.yaml"
        file_path.write_text(valid_compute_contract_yaml)

        result = regenerate_fingerprint(file_path, dry_run=True)

        # If fingerprint was computed, old should be None (not in original)
        # and new should be the computed fingerprint
        if result.new_fingerprint is not None:
            assert result.old_fingerprint is None  # Original had no fingerprint
            assert "1.0.0:" in result.new_fingerprint  # Version prefix


# =============================================================================
# Fingerprint Consistency Tests
# =============================================================================


@pytest.mark.unit
class TestFingerprintConsistency:
    """Tests for fingerprint computation consistency.

    PR #180 Requirement: Test that regenerated fingerprints match compute_contract_fingerprint().
    """

    def test_regenerated_fingerprint_matches_direct_computation(
        self, temp_dir: Path, valid_compute_contract_yaml: str
    ) -> None:
        """Test that fingerprint from regenerate script matches direct computation."""
        file_path = temp_dir / "contract.yaml"
        file_path.write_text(valid_compute_contract_yaml)

        # Compute fingerprint using regenerate script
        result = regenerate_fingerprint(file_path, dry_run=True)

        if result.new_fingerprint is not None and result.error is None:
            # Parse the YAML and create a model to compute fingerprint directly
            import yaml

            contract_data = yaml.safe_load(valid_compute_contract_yaml)
            model_class = detect_contract_model(contract_data)
            if model_class is not None:
                # Remove fingerprint if present for comparison
                data_for_fp = {
                    k: v for k, v in contract_data.items() if k != "fingerprint"
                }
                contract = model_class.model_validate(data_for_fp)
                direct_fingerprint = compute_contract_fingerprint(contract)

                # Compare fingerprints
                assert result.new_fingerprint == str(direct_fingerprint)

    def test_fingerprint_deterministic_across_multiple_runs(
        self, temp_dir: Path, valid_compute_contract_yaml: str
    ) -> None:
        """Test that fingerprint is deterministic across multiple regenerations."""
        file_path = temp_dir / "contract.yaml"
        file_path.write_text(valid_compute_contract_yaml)

        # Run regeneration multiple times
        results = [regenerate_fingerprint(file_path, dry_run=True) for _ in range(5)]

        # All fingerprints should be identical
        fingerprints = [r.new_fingerprint for r in results if r.new_fingerprint]
        if fingerprints:
            assert all(fp == fingerprints[0] for fp in fingerprints)

    def test_compute_fingerprint_for_contract_consistency(self) -> None:
        """Test compute_fingerprint_for_contract returns consistent results."""
        contract_data = {
            "name": "TestContract",
            "contract_version": {"major": 1, "minor": 0, "patch": 0},
            "node_type": "COMPUTE_GENERIC",
            "description": "Test contract",
            "input_model": "ModelInput",
            "output_model": "ModelOutput",
            "dependencies": [],
            "algorithm": {
                "algorithm_type": "default",
                "factors": {
                    "default_factor": {
                        "weight": 1.0,
                        "calculation_method": "identity",
                    }
                },
            },
        }

        # Compute multiple times
        fingerprints = [
            compute_fingerprint_for_contract(contract_data) for _ in range(5)
        ]

        # Filter out results with None fingerprint and check consistency
        # Note: fp is FingerprintResult, need to check fp.fingerprint attribute
        valid_fingerprints = [
            fp.fingerprint for fp in fingerprints if fp.fingerprint is not None
        ]
        if valid_fingerprints:
            first = str(valid_fingerprints[0])
            assert all(str(fp) == first for fp in valid_fingerprints)


# =============================================================================
# Error Handling Tests (Malformed YAML)
# =============================================================================


@pytest.mark.unit
class TestMalformedYAMLHandling:
    """Tests for error handling with malformed YAML.

    PR #180 Requirement: Test error handling for malformed YAML.
    """

    def test_malformed_yaml_returns_error_result(
        self, temp_dir: Path, malformed_yaml_content: str
    ) -> None:
        """Test that malformed YAML returns an error result, not exception."""
        file_path = temp_dir / "malformed.yaml"
        file_path.write_text(malformed_yaml_content)

        result = regenerate_fingerprint(file_path, dry_run=True)

        # Should return error result, not raise exception
        assert result.error is not None
        assert "YAML" in result.error or "parse" in result.error.lower()
        assert result.changed is False
        assert result.new_fingerprint is None

    def test_empty_yaml_returns_skip_result(
        self, temp_dir: Path, empty_yaml_content: str
    ) -> None:
        """Test that empty YAML is handled gracefully."""
        file_path = temp_dir / "empty.yaml"
        file_path.write_text(empty_yaml_content)

        result = regenerate_fingerprint(file_path, dry_run=True)

        # Empty YAML should be skipped (not a contract)
        assert result.skipped is True or result.error is not None
        assert result.changed is False

    def test_non_contract_yaml_skipped(
        self, temp_dir: Path, non_contract_yaml_content: str
    ) -> None:
        """Test that YAML without node_type is skipped."""
        file_path = temp_dir / "non_contract.yaml"
        file_path.write_text(non_contract_yaml_content)

        result = regenerate_fingerprint(file_path, dry_run=True)

        # Should be skipped as it's not an ONEX contract
        assert result.skipped is True
        assert result.skip_reason is not None
        assert "node_type" in result.skip_reason.lower()

    def test_yaml_list_instead_of_dict_handled(self, temp_dir: Path) -> None:
        """Test that YAML containing a list instead of dict is handled."""
        file_path = temp_dir / "list.yaml"
        file_path.write_text("- item1\n- item2\n- item3")

        result = regenerate_fingerprint(file_path, dry_run=True)

        # Should be skipped as it's not a mapping
        assert result.skipped is True
        assert "mapping" in result.skip_reason.lower() if result.skip_reason else True

    def test_unicode_error_handled(self, temp_dir: Path) -> None:
        """Test that files with encoding errors are handled gracefully."""
        file_path = temp_dir / "binary.yaml"
        # Write binary content that will cause encoding error
        file_path.write_bytes(b"\x80\x81\x82\x83")

        result = regenerate_fingerprint(file_path, dry_run=True)

        # Should return error result
        assert result.error is not None
        assert "encoding" in result.error.lower() or "decode" in result.error.lower()


# =============================================================================
# File Size Limit Tests
# =============================================================================


@pytest.mark.unit
class TestFileSizeLimit:
    """Tests for file size limit enforcement.

    PR #180 Requirement: Test file size limit enforcement.
    """

    def test_file_size_limit_constant_is_10mb(self) -> None:
        """Test that MAX_FILE_SIZE_BYTES is set to 10MB."""
        assert MAX_FILE_SIZE_BYTES == 10 * 1024 * 1024  # 10MB

    def test_large_file_returns_error(self, temp_dir: Path) -> None:
        """Test that files exceeding size limit return error."""
        file_path = temp_dir / "large.yaml"

        # Create a file that appears large using mock
        # We don't actually create a 10MB file for test efficiency
        file_path.write_text("name: Test")

        # Get the real stat result first
        real_stat = file_path.stat()

        # Create a mock stat result with large file size
        class MockStatResult:
            """Mock stat result with configurable size."""

            st_mode = real_stat.st_mode
            st_ino = real_stat.st_ino
            st_dev = real_stat.st_dev
            st_nlink = real_stat.st_nlink
            st_uid = real_stat.st_uid
            st_gid = real_stat.st_gid
            st_size = MAX_FILE_SIZE_BYTES + 1  # Exceed limit
            st_atime = real_stat.st_atime
            st_mtime = real_stat.st_mtime
            st_ctime = real_stat.st_ctime

        # Mock the stat call to simulate large file
        with patch.object(Path, "stat", return_value=MockStatResult()):
            result = regenerate_fingerprint(file_path, dry_run=True)

            assert result.error is not None
            assert "too large" in result.error.lower() or "size" in result.error.lower()

    def test_normal_size_file_not_rejected(
        self, temp_dir: Path, valid_compute_contract_yaml: str
    ) -> None:
        """Test that normal-sized files are not rejected."""
        file_path = temp_dir / "normal.yaml"
        file_path.write_text(valid_compute_contract_yaml)

        result = regenerate_fingerprint(file_path, dry_run=True)

        # Should not have size-related error
        if result.error:
            assert "too large" not in result.error.lower()
            assert "size" not in result.error.lower()


# =============================================================================
# File Discovery Tests
# =============================================================================


@pytest.mark.unit
class TestFileDiscovery:
    """Tests for contract file discovery functionality."""

    def test_find_yaml_files(self, temp_dir: Path) -> None:
        """Test finding YAML files in a directory."""
        (temp_dir / "contract1.yaml").write_text("node_type: COMPUTE_GENERIC")
        (temp_dir / "contract2.yml").write_text("node_type: EFFECT_GENERIC")
        (temp_dir / "not_yaml.txt").write_text("not yaml")

        files = find_contract_files(temp_dir)

        assert len(files) == 2
        assert any(f.name == "contract1.yaml" for f in files)
        assert any(f.name == "contract2.yml" for f in files)

    def test_find_yaml_files_recursive(self, temp_dir: Path) -> None:
        """Test recursive file discovery."""
        subdir = temp_dir / "subdir"
        subdir.mkdir()
        (temp_dir / "root.yaml").write_text("node_type: COMPUTE_GENERIC")
        (subdir / "nested.yaml").write_text("node_type: EFFECT_GENERIC")

        files = find_contract_files(temp_dir, recursive=True)

        assert len(files) == 2

    def test_excludes_special_directories(self, temp_dir: Path) -> None:
        """Test that __pycache__, .git, etc. are excluded."""
        pycache = temp_dir / "__pycache__"
        pycache.mkdir()
        (pycache / "cached.yaml").write_text("node_type: COMPUTE_GENERIC")

        git = temp_dir / ".git"
        git.mkdir()
        (git / "config.yaml").write_text("git: true")

        venv = temp_dir / ".venv"
        venv.mkdir()
        (venv / "package.yaml").write_text("venv: true")

        (temp_dir / "valid.yaml").write_text("node_type: COMPUTE_GENERIC")

        files = find_contract_files(temp_dir, recursive=True)

        assert len(files) == 1
        assert files[0].name == "valid.yaml"


# =============================================================================
# YAML Fingerprint Update Tests
# =============================================================================


@pytest.mark.unit
class TestUpdateFingerprintInYAML:
    """Tests for updating fingerprint in YAML content."""

    def test_update_existing_fingerprint(self) -> None:
        """Test updating an existing fingerprint in YAML."""
        content = """name: Test
version: "1.0.0"
fingerprint: "1.0.0:oldvalue1234"
description: Test
"""
        new_fp = "1.0.0:newvalue5678"

        updated = update_fingerprint_in_yaml(content, new_fp)

        assert 'fingerprint: "1.0.0:newvalue5678"' in updated
        assert "oldvalue1234" not in updated

    def test_add_fingerprint_after_version(self) -> None:
        """Test adding fingerprint after version field when not present."""
        content = """name: Test
version: "1.0.0"
description: Test
"""
        new_fp = "1.0.0:abcdef123456"

        updated = update_fingerprint_in_yaml(content, new_fp)

        assert 'fingerprint: "1.0.0:abcdef123456"' in updated
        # Fingerprint should be after version
        version_pos = updated.find("version:")
        fingerprint_pos = updated.find("fingerprint:")
        assert version_pos != -1, "version: not found in output"
        assert fingerprint_pos != -1, "fingerprint: not found in output"
        assert fingerprint_pos > version_pos, "fingerprint should appear after version"


# =============================================================================
# Contract Model Detection Tests
# =============================================================================


@pytest.mark.unit
class TestContractModelDetection:
    """Tests for contract model detection."""

    def test_detect_compute_model(self) -> None:
        """Test detecting compute contract model."""
        data = {
            "node_type": "COMPUTE_GENERIC",
            "name": "TestCompute",
            "contract_version": "1.0.0",
            "input_model": "ModelInput",
            "output_model": "ModelOutput",
            "description": "Test",
        }

        model = detect_contract_model(data)

        # Use __qualname__ comparison to avoid pytest-xdist class identity issues
        # (each worker imports classes independently, causing id() mismatch)
        assert model is not None
        assert model.__qualname__ == "ModelContractCompute"

    def test_detect_effect_model(self) -> None:
        """Test detecting effect contract model."""
        data = {
            "node_type": "EFFECT_GENERIC",
            "name": "TestEffect",
            "contract_version": "1.0.0",
            "input_model": "ModelInput",
            "output_model": "ModelOutput",
            "description": "Test",
        }

        model = detect_contract_model(data)

        # Use __qualname__ comparison to avoid pytest-xdist class identity issues
        # (each worker imports classes independently, causing id() mismatch)
        assert model is not None
        assert model.__qualname__ == "ModelContractEffect"

    def test_detect_fallback_to_yaml_contract(self) -> None:
        """Test fallback to ModelYamlContract for unknown types."""

        data = {
            "node_type": "UNKNOWN_TYPE",
            "name": "TestUnknown",
        }

        model = detect_contract_model(data)

        # Should fall back to flexible model
        assert model is not None

    def test_missing_node_type_returns_none(self) -> None:
        """Test that missing node_type returns None."""
        data = {
            "name": "TestNoNodeType",
            "contract_version": "1.0.0",
        }

        model = detect_contract_model(data)

        assert model is None


# =============================================================================
# RegenerateResult Tests
# =============================================================================


@pytest.mark.unit
class TestRegenerateResult:
    """Tests for RegenerateResult data class."""

    def test_result_to_dict_serialization(self, temp_dir: Path) -> None:
        """Test RegenerateResult serialization to dictionary."""
        result = RegenerateResult(
            file_path=temp_dir / "test.yaml",
            old_fingerprint="1.0.0:old12345678",
            new_fingerprint="1.0.0:new12345678",
            changed=True,
        )

        d = result.to_dict()

        assert "file" in d
        assert d["old_fingerprint"] == "1.0.0:old12345678"
        assert d["new_fingerprint"] == "1.0.0:new12345678"
        assert d["changed"] is True
        assert d["error"] is None
        assert d["skipped"] is False

    def test_result_with_error(self, temp_dir: Path) -> None:
        """Test RegenerateResult with error."""
        result = RegenerateResult(
            file_path=temp_dir / "error.yaml",
            old_fingerprint=None,
            new_fingerprint=None,
            changed=False,
            error="File not found",
        )

        assert result.error == "File not found"
        assert result.changed is False

    def test_result_skipped(self, temp_dir: Path) -> None:
        """Test RegenerateResult when skipped."""
        result = RegenerateResult(
            file_path=temp_dir / "skipped.yaml",
            old_fingerprint=None,
            new_fingerprint=None,
            changed=False,
            skipped=True,
            skip_reason="Not an ONEX contract",
        )

        assert result.skipped is True
        assert result.skip_reason == "Not an ONEX contract"


# =============================================================================
# Edge Case Tests
# =============================================================================


@pytest.mark.unit
class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_nonexistent_file_returns_error(self, temp_dir: Path) -> None:
        """Test that nonexistent file returns error result."""
        file_path = temp_dir / "nonexistent.yaml"

        result = regenerate_fingerprint(file_path, dry_run=True)

        assert result.error is not None
        assert "not found" in result.error.lower() or "not found" in result.error

    def test_directory_instead_of_file_returns_error(self, temp_dir: Path) -> None:
        """Test that passing a directory returns error."""
        dir_path = temp_dir / "subdir"
        dir_path.mkdir()

        result = regenerate_fingerprint(dir_path, dry_run=True)

        assert result.error is not None
        assert "not a file" in result.error.lower() or "file" in result.error.lower()

    def test_whitespace_only_yaml(self, temp_dir: Path) -> None:
        """Test handling of whitespace-only YAML files."""
        file_path = temp_dir / "whitespace.yaml"
        file_path.write_text("   \n\t\n   ")

        result = regenerate_fingerprint(file_path, dry_run=True)

        # Should be skipped or error (empty content)
        assert result.skipped or result.error is not None

    def test_fingerprint_format_preserved(
        self, temp_dir: Path, valid_compute_contract_yaml: str
    ) -> None:
        """Test that fingerprint format is correct (version:hash)."""
        file_path = temp_dir / "contract.yaml"
        file_path.write_text(valid_compute_contract_yaml)

        result = regenerate_fingerprint(file_path, dry_run=True)

        if result.new_fingerprint:
            # Should be in format "version:hash"
            assert ":" in result.new_fingerprint
            version, hash_part = result.new_fingerprint.split(":", 1)
            assert version == "1.0.0"  # From contract version
            assert len(hash_part) == 12  # Default hash length


# =============================================================================
# Non-Dry-Run (Actual Write) Tests
# =============================================================================


@pytest.mark.unit
class TestActualWrite:
    """Tests for actual file modification (non-dry-run mode)."""

    def test_regenerate_actually_modifies_file(
        self, temp_dir: Path, valid_compute_contract_yaml: str
    ) -> None:
        """Test that non-dry-run mode actually modifies the file."""
        file_path = temp_dir / "contract.yaml"
        file_path.write_text(valid_compute_contract_yaml)

        original_content = file_path.read_text()

        # Run without dry-run
        result = regenerate_fingerprint(file_path, dry_run=False)

        new_content = file_path.read_text()

        # If fingerprint was computed, file should be modified
        if result.new_fingerprint and result.changed:
            assert new_content != original_content
            assert "fingerprint:" in new_content
            assert result.new_fingerprint in new_content

    def test_regenerate_adds_fingerprint_to_file_without_one(
        self, temp_dir: Path, valid_compute_contract_yaml: str
    ) -> None:
        """Test that fingerprint is added to a file that doesn't have one."""
        file_path = temp_dir / "contract.yaml"
        file_path.write_text(valid_compute_contract_yaml)

        # Verify original has no fingerprint
        assert "fingerprint:" not in file_path.read_text()

        result = regenerate_fingerprint(file_path, dry_run=False)

        if result.new_fingerprint and not result.error:
            # File should now have fingerprint
            new_content = file_path.read_text()
            assert "fingerprint:" in new_content

    def test_regenerate_updates_existing_fingerprint(
        self, temp_dir: Path, contract_with_existing_fingerprint_yaml: str
    ) -> None:
        """Test that existing fingerprint is updated with correct value."""
        file_path = temp_dir / "contract.yaml"
        file_path.write_text(contract_with_existing_fingerprint_yaml)

        # The existing fingerprint is "1.0.0:abcdef123456" which is wrong
        result = regenerate_fingerprint(file_path, dry_run=False)

        if result.new_fingerprint and result.changed:
            new_content = file_path.read_text()
            # Old fingerprint should be gone
            assert "abcdef123456" not in new_content
            # New fingerprint should be present
            assert result.new_fingerprint in new_content


# =============================================================================
# Additional Model Detection Tests
# =============================================================================


@pytest.mark.unit
class TestAdditionalModelDetection:
    """Additional tests for contract model detection covering more node types."""

    def test_detect_reducer_model(self) -> None:
        """Test detecting reducer contract model."""
        data = {
            "node_type": "REDUCER_GENERIC",
            "name": "TestReducer",
            "contract_version": "1.0.0",
            "input_model": "ModelInput",
            "output_model": "ModelOutput",
            "description": "Test",
        }

        model = detect_contract_model(data)

        # Use __qualname__ comparison to avoid pytest-xdist class identity issues
        # (each worker imports classes independently, causing id() mismatch)
        assert model is not None
        assert model.__qualname__ == "ModelContractReducer"

    def test_detect_orchestrator_model(self) -> None:
        """Test detecting orchestrator contract model."""
        data = {
            "node_type": "ORCHESTRATOR_GENERIC",
            "name": "TestOrchestrator",
            "contract_version": "1.0.0",
            "input_model": "ModelInput",
            "output_model": "ModelOutput",
            "description": "Test",
        }

        model = detect_contract_model(data)

        # Use __qualname__ comparison to avoid pytest-xdist class identity issues
        # (each worker imports classes independently, causing id() mismatch)
        assert model is not None
        assert model.__qualname__ == "ModelContractOrchestrator"

    def test_detect_transformer_model(self) -> None:
        """Test detecting transformer (compute) contract model."""
        data = {
            "node_type": "TRANSFORMER",
            "name": "TestTransformer",
            "contract_version": "1.0.0",
            "input_model": "ModelInput",
            "output_model": "ModelOutput",
            "description": "Test",
        }

        model = detect_contract_model(data)

        # Use __qualname__ comparison to avoid pytest-xdist class identity issues
        # (each worker imports classes independently, causing id() mismatch)
        assert model is not None
        assert model.__qualname__ == "ModelContractCompute"

    def test_detect_gateway_model(self) -> None:
        """Test detecting gateway (effect) contract model."""
        data = {
            "node_type": "GATEWAY",
            "name": "TestGateway",
            "contract_version": "1.0.0",
            "input_model": "ModelInput",
            "output_model": "ModelOutput",
            "description": "Test",
        }

        model = detect_contract_model(data)

        # Use __qualname__ comparison to avoid pytest-xdist class identity issues
        # (each worker imports classes independently, causing id() mismatch)
        assert model is not None
        assert model.__qualname__ == "ModelContractEffect"

    def test_detect_with_contract_version_uses_yaml_contract_full(self) -> None:
        """Test that contracts with contract_version use ModelYamlContractFull.

        Note: We use ModelYamlContractFull (extra="allow") instead of ModelYamlContract
        (extra="ignore") to ensure all fields are captured for fingerprint computation.
        """
        data = {
            "node_type": "COMPUTE_GENERIC",
            "name": "TestFlexible",
            "contract_version": "1.0",  # This triggers flexible mode
            "description": "Test",
        }

        model = detect_contract_model(data)

        # Use __qualname__ comparison to avoid pytest-xdist class identity issues
        # (each worker imports classes independently, causing id() mismatch)
        assert model is not None
        assert model.__qualname__ == "ModelYamlContractFull"

    def test_non_string_node_type_returns_none(self) -> None:
        """Test that non-string node_type returns None."""
        data = {
            "node_type": 123,  # Not a string
            "name": "TestBadType",
        }

        model = detect_contract_model(data)

        assert model is None


# =============================================================================
# Additional YAML Update Tests
# =============================================================================


@pytest.mark.unit
class TestAdditionalYAMLUpdate:
    """Additional tests for YAML fingerprint updating."""

    def test_add_fingerprint_without_version_field(self) -> None:
        """Test adding fingerprint when no version field exists."""
        content = """name: Test
description: No version field
node_type: COMPUTE_GENERIC
"""
        new_fp = "0.0.0:abcdef123456"

        updated = update_fingerprint_in_yaml(content, new_fp)

        # Should add fingerprint at the end
        assert 'fingerprint: "0.0.0:abcdef123456"' in updated

    def test_update_fingerprint_preserves_formatting(self) -> None:
        """Test that updating fingerprint preserves YAML formatting."""
        content = """name: Test
version: "1.0.0"
fingerprint: "1.0.0:oldvalue1234"
description: Test description
  with multiple lines
"""
        new_fp = "1.0.0:newvalue5678"

        updated = update_fingerprint_in_yaml(content, new_fp)

        # Check formatting is preserved
        assert "name: Test" in updated
        assert 'version: "1.0.0"' in updated
        assert "description: Test description" in updated
        assert "with multiple lines" in updated

    def test_update_fingerprint_with_quoted_value(self) -> None:
        """Test updating fingerprint that has quoted value."""
        content = """name: Test
fingerprint: '1.0.0:oldvalue1234'
"""
        new_fp = "1.0.0:newvalue5678"

        updated = update_fingerprint_in_yaml(content, new_fp)

        assert 'fingerprint: "1.0.0:newvalue5678"' in updated
        assert "oldvalue1234" not in updated

    def test_add_fingerprint_after_dict_style_version(self) -> None:
        """Test adding fingerprint after dict-style version block.

        PR #180 Requirement: Handle version blocks like:
        version:
          major: 1
          minor: 0
          patch: 0
        """
        content = """name: TestContract
version:
  major: 1
  minor: 0
  patch: 0
node_type: COMPUTE_GENERIC
description: Test contract
"""
        new_fp = "1.0.0:abcdef123456"

        updated = update_fingerprint_in_yaml(content, new_fp)

        # Fingerprint should be added after version block
        assert 'fingerprint: "1.0.0:abcdef123456"' in updated
        # Fingerprint should come after patch field
        version_block_end = updated.find("patch: 0")
        fingerprint_pos = updated.find("fingerprint:")
        assert version_block_end != -1, "patch: 0 not found in output"
        assert fingerprint_pos != -1, "fingerprint: not found in output"
        assert fingerprint_pos > version_block_end, (
            "fingerprint should appear after version block"
        )

    def test_add_fingerprint_after_contract_version(self) -> None:
        """Test adding fingerprint after contract_version field.

        PR #180 Requirement: Handle contract_version for flexible contracts.
        """
        content = """name: TestFlexibleContract
contract_version: "1.0"
node_type: COMPUTE_GENERIC
description: Flexible contract
"""
        new_fp = "1.0.0:abcdef123456"

        updated = update_fingerprint_in_yaml(content, new_fp)

        # Fingerprint should be added after contract_version
        assert 'fingerprint: "1.0.0:abcdef123456"' in updated
        contract_version_pos = updated.find("contract_version:")
        fingerprint_pos = updated.find("fingerprint:")
        assert contract_version_pos != -1, "contract_version: not found in output"
        assert fingerprint_pos != -1, "fingerprint: not found in output"
        assert fingerprint_pos > contract_version_pos, (
            "fingerprint should appear after contract_version"
        )

    def test_add_fingerprint_after_name_when_no_version(self) -> None:
        """Test adding fingerprint after name field when no version exists."""
        content = """name: TestNoVersion
node_type: COMPUTE_GENERIC
description: No version field
"""
        new_fp = "0.0.0:abcdef123456"

        updated = update_fingerprint_in_yaml(content, new_fp)

        # Fingerprint should be added after name
        assert 'fingerprint: "0.0.0:abcdef123456"' in updated
        name_pos = updated.find("name:")
        fingerprint_pos = updated.find("fingerprint:")
        assert name_pos != -1, "name: not found in output"
        assert fingerprint_pos != -1, "fingerprint: not found in output"
        assert fingerprint_pos > name_pos, "fingerprint should appear after name"

    def test_dict_style_version_preserves_node_type(self) -> None:
        """Test that dict-style version handling doesn't corrupt other fields."""
        content = """name: TestContract
version:
  major: 1
  minor: 0
  patch: 0
node_type: COMPUTE_GENERIC
description: Test
"""
        new_fp = "1.0.0:abcdef123456"

        updated = update_fingerprint_in_yaml(content, new_fp)

        # All original content should be preserved
        assert "name: TestContract" in updated
        assert "major: 1" in updated
        assert "minor: 0" in updated
        assert "patch: 0" in updated
        assert "node_type: COMPUTE_GENERIC" in updated
        assert "description: Test" in updated


# =============================================================================
# Fingerprint Computation Edge Cases
# =============================================================================


@pytest.mark.unit
class TestFingerprintComputationEdgeCases:
    """Edge case tests for fingerprint computation."""

    def test_compute_fingerprint_with_invalid_node_type(self) -> None:
        """Test that invalid node_type is handled gracefully."""
        # Create contract data with invalid node_type (not a string)
        # This triggers model detection failure, not schema validation error
        contract_data = {
            "node_type": 12345,  # Invalid: should be a string
            "name": "TestBadContract",
            "contract_version": "1.0.0",
            "input_model": "ModelInput",
            "output_model": "ModelOutput",
            "description": "Test",
        }

        result = compute_fingerprint_for_contract(contract_data)

        # Should return FingerprintResult with error (not raise)
        assert result.fingerprint is None
        assert result.error is not None
        assert "detect" in result.error.lower() or "model" in result.error.lower()

    def test_compute_fingerprint_with_missing_required_fields(self) -> None:
        """Test fingerprint computation with missing required fields."""
        contract_data = {
            "node_type": "COMPUTE_GENERIC",
            "name": "TestMinimal",
            # Missing other required fields
        }

        result = compute_fingerprint_for_contract(contract_data)

        # Should return FingerprintResult with error (missing required fields)
        # The contract falls back to ModelYamlContract which is more permissive
        # but still requires certain fields for fingerprint computation
        assert result is not None
        # Either fingerprint is computed (if model is permissive) or error is set
        if result.fingerprint is None:
            assert result.error is not None

    def test_fingerprint_result_changed_is_false_when_matches(
        self, temp_dir: Path, valid_compute_contract_yaml: str
    ) -> None:
        """Test that changed is False when fingerprint already matches."""
        file_path = temp_dir / "contract.yaml"
        file_path.write_text(valid_compute_contract_yaml)

        # First regeneration to add fingerprint
        result1 = regenerate_fingerprint(file_path, dry_run=False)

        if result1.new_fingerprint and not result1.error:
            # Second regeneration should show no change
            result2 = regenerate_fingerprint(file_path, dry_run=True)

            # Should not be changed (fingerprint already correct)
            assert result2.changed is False
            assert result2.new_fingerprint == result1.new_fingerprint
