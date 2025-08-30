"""
Tests for ContractLoader security validation functionality.

These tests address the security validation requirements identified in the PR review
for YAML contract loading.
"""

import tempfile
from pathlib import Path

import pytest

from omnibase_core.core.contracts.contract_loader import ContractLoader
from omnibase_core.core.errors.core_errors import CoreErrorCode, OnexError


class TestContractLoaderSecurity:
    """Test cases for ContractLoader security validation."""

    def test_yaml_size_validation_success(self):
        """Test that normal-sized YAML files load successfully."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(
                """
contract_name: test_contract
description: A test contract
schema:
  properties:
    name:
      type: string
      description: Name field
"""
            )
            f.flush()
            temp_path = Path(f.name)

        try:
            loader = ContractLoader(temp_path.parent)
            # This should not raise an exception
            loader._validate_yaml_content_security(temp_path.read_text(), temp_path)
        finally:
            temp_path.unlink()

    def test_yaml_size_validation_failure(self):
        """Test that excessively large YAML files are rejected."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            # Create content larger than 10MB
            large_content = "data: " + "x" * (11 * 1024 * 1024)
            f.write(large_content)
            f.flush()
            temp_path = Path(f.name)

        try:
            loader = ContractLoader(temp_path.parent)

            with pytest.raises(OnexError) as exc_info:
                loader._validate_yaml_content_security(temp_path.read_text(), temp_path)

            assert exc_info.value.error_code == CoreErrorCode.VALIDATION_FAILED
            assert "too large" in str(exc_info.value)
        finally:
            temp_path.unlink()

    def test_suspicious_pattern_detection(self):
        """Test detection of suspicious YAML patterns."""
        suspicious_patterns = [
            "!!python/object/apply:os.system",
            "!!map",
            "!!omap",
            "!!python",
            "__import__('os')",
            "eval('malicious code')",
            "exec('dangerous code')",
        ]

        loader = ContractLoader(Path("/tmp"))
        test_file = Path("/tmp/test.yaml")

        for pattern in suspicious_patterns:
            yaml_content = f"""
contract_name: test
data: {pattern}
"""
            # This should complete without raising (warnings only)
            # but we check that the validation method runs
            loader._validate_yaml_content_security(yaml_content, test_file)

    def test_yaml_nesting_validation_success(self):
        """Test that normally nested YAML structures are accepted."""
        yaml_content = """
contract_name: test
data:
  level1:
    level2:
      level3:
        level4: value
"""

        loader = ContractLoader(Path("/tmp"))
        test_file = Path("/tmp/test.yaml")

        # This should not raise an exception
        loader._validate_yaml_content_security(yaml_content, test_file)

    def test_yaml_nesting_validation_failure(self):
        """Test that excessively nested YAML structures are rejected."""
        # Create deeply nested structure (more than 50 levels)
        nested_content = "data: " + "{nested: " * 60 + "value" + "}" * 60

        loader = ContractLoader(Path("/tmp"))
        test_file = Path("/tmp/test.yaml")

        with pytest.raises(OnexError) as exc_info:
            loader._validate_yaml_content_security(nested_content, test_file)

        assert exc_info.value.error_code == CoreErrorCode.VALIDATION_FAILED
        assert "nesting too deep" in str(exc_info.value)

    def test_contract_loading_with_security_validation(self):
        """Test that contract loading includes security validation."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(
                """
contract_name: secure_contract
node_name: test_node
description: A secure test contract
input_schema:
  properties:
    message:
      type: string
      description: Input message
output_schema:
  properties:
    result:
      type: string
      description: Output result
"""
            )
            f.flush()
            temp_path = Path(f.name)

        try:
            loader = ContractLoader(temp_path.parent)

            # This should load successfully with security validation
            contract_dict = loader.load_contract(temp_path)

            assert contract_dict is not None
            assert contract_dict.get("contract_name") == "secure_contract"
            assert contract_dict.get("node_name") == "test_node"
        finally:
            temp_path.unlink()

    def test_empty_yaml_handling(self):
        """Test that empty YAML files are handled gracefully."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("")  # Empty file
            f.flush()
            temp_path = Path(f.name)

        try:
            loader = ContractLoader(temp_path.parent)

            # Empty content should be validated successfully
            loader._validate_yaml_content_security("", temp_path)

            # Loading should return empty dict
            contract_dict = loader.load_contract(temp_path)
            assert contract_dict == {}
        finally:
            temp_path.unlink()


if __name__ == "__main__":
    pytest.main([__file__])
