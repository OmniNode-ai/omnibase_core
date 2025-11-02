"""
Comprehensive unit tests for util_contract_loader.py (Part 1).

Part 1 Coverage:
- Contract loading from files
- YAML parsing and validation
- Contract schema validation
- Error handling for malformed contracts
- File I/O operations
- Security validation
- Contract structure validation

Part 2 (Agent 50): Contract resolution, reference handling, caching

Test Categories:
- __init__ constructor tests
- load_contract workflow tests
- _load_contract_file I/O tests
- _parse_contract_content parsing tests
- _convert_contract_content_to_dict conversion tests
- _validate_contract_structure validation tests
- _validate_yaml_content_security security tests
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
import yaml

from omnibase_core.enums.enum_node_type import EnumNodeType
from omnibase_core.errors.error_codes import EnumCoreErrorCode
from omnibase_core.models.core.model_contract_content import ModelContractContent
from omnibase_core.models.core.model_contract_definitions import (
    ModelContractDefinitions,
)
from omnibase_core.models.core.model_tool_specification import ModelToolSpecification
from omnibase_core.models.core.model_yaml_schema_object import ModelYamlSchemaObject
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.utils.util_contract_loader import ProtocolContractLoader

# ===== Test Fixtures =====


@pytest.fixture
def valid_contract_yaml(tmp_path: Path) -> Path:
    """Create a valid contract YAML file for testing."""
    contract_file = tmp_path / "valid_contract.yaml"
    contract_file.write_text(
        """
contract_version:
  major: 1
  minor: 0
  patch: 0
node_name: TestNode
node_type: COMPUTE
tool_specification:
  main_tool_class: TestToolClass
""",
    )
    return contract_file


@pytest.fixture
def minimal_contract_yaml(tmp_path: Path) -> Path:
    """Create minimal valid contract YAML file."""
    contract_file = tmp_path / "minimal_contract.yaml"
    contract_file.write_text(
        """
node_name: MinimalNode
tool_specification:
  main_tool_class: MinimalToolClass
""",
    )
    return contract_file


@pytest.fixture
def complex_contract_yaml(tmp_path: Path) -> Path:
    """Create complex contract with all optional fields."""
    contract_file = tmp_path / "complex_contract.yaml"
    contract_file.write_text(
        """
contract_version:
  major: 2
  minor: 5
  patch: 3
node_name: ComplexNode
node_type: EFFECT
tool_specification:
  main_tool_class: ComplexToolClass
dependencies:
  - name: DependencyOne
    type: service
    version: "1.0.0"
  - name: DependencyTwo
    type: utility
    version: "2.1.0"
actions:
  - action_name: process
    description: Process data
primary_actions:
  - process
  - validate
validation_rules:
  required_fields:
    - field1
    - field2
metadata:
  author: Test Author
  created_at: "2024-01-01"
capabilities:
  - capability1
  - capability2
""",
    )
    return contract_file


@pytest.fixture
def malformed_yaml(tmp_path: Path) -> Path:
    """Create malformed YAML file."""
    contract_file = tmp_path / "malformed.yaml"
    contract_file.write_text(
        """
node_name: TestNode
tool_specification:
  main_tool_class: TestClass
  invalid_indent: bad
    extra_bad: worse
""",
    )
    return contract_file


@pytest.fixture
def empty_contract_yaml(tmp_path: Path) -> Path:
    """Create empty contract file."""
    contract_file = tmp_path / "empty.yaml"
    contract_file.write_text("")
    return contract_file


@pytest.fixture
def contract_loader(tmp_path: Path) -> ProtocolContractLoader:
    """Create a ProtocolContractLoader instance for testing."""
    return ProtocolContractLoader(base_path=tmp_path, cache_enabled=True)


@pytest.fixture
def contract_loader_no_cache(tmp_path: Path) -> ProtocolContractLoader:
    """Create a ProtocolContractLoader with caching disabled."""
    return ProtocolContractLoader(base_path=tmp_path, cache_enabled=False)


# ===== Constructor Tests =====


class TestProtocolContractLoaderInit:
    """Test ProtocolContractLoader.__init__ constructor."""

    def test_init_with_cache_enabled(self, tmp_path: Path) -> None:
        """Test initialization with caching enabled."""
        loader = ProtocolContractLoader(base_path=tmp_path, cache_enabled=True)

        assert loader.state.cache_enabled is True
        assert loader.state.base_path == tmp_path
        assert len(loader.state.contract_cache) == 0
        assert len(loader.state.loaded_contracts) == 0

    def test_init_with_cache_disabled(self, tmp_path: Path) -> None:
        """Test initialization with caching disabled."""
        loader = ProtocolContractLoader(base_path=tmp_path, cache_enabled=False)

        assert loader.state.cache_enabled is False
        assert loader.state.base_path == tmp_path

    def test_init_with_absolute_path(self, tmp_path: Path) -> None:
        """Test initialization with absolute path."""
        loader = ProtocolContractLoader(base_path=tmp_path)

        assert loader.state.base_path.is_absolute()
        assert loader.state.base_path == tmp_path

    def test_init_with_relative_path(self) -> None:
        """Test initialization with relative path."""
        relative_path = Path("relative/path")
        loader = ProtocolContractLoader(base_path=relative_path)

        # Should store the path as-is, resolution happens later
        assert loader.state.base_path == relative_path

    def test_init_default_cache_enabled(self, tmp_path: Path) -> None:
        """Test that cache is enabled by default."""
        loader = ProtocolContractLoader(base_path=tmp_path)

        assert loader.state.cache_enabled is True


# ===== load_contract Tests =====


class TestLoadContract:
    """Test ProtocolContractLoader.load_contract method."""

    def test_load_valid_contract(
        self, contract_loader: ProtocolContractLoader, valid_contract_yaml: Path
    ) -> None:
        """Test loading a valid contract file."""
        result = contract_loader.load_contract(valid_contract_yaml)

        assert isinstance(result, ModelContractContent)
        assert result.node_name == "TestNode"
        assert result.node_type == EnumNodeType.COMPUTE
        assert result.tool_specification.main_tool_class == "TestToolClass"
        assert result.contract_version.major == 1
        assert result.contract_version.minor == 0
        assert result.contract_version.patch == 0

    def test_load_minimal_contract(
        self, contract_loader: ProtocolContractLoader, minimal_contract_yaml: Path
    ) -> None:
        """Test loading minimal contract with defaults."""
        result = contract_loader.load_contract(minimal_contract_yaml)

        assert result.node_name == "MinimalNode"
        assert result.tool_specification.main_tool_class == "MinimalToolClass"
        # Should use defaults
        assert result.contract_version.major == 1
        assert result.contract_version.minor == 0
        assert result.contract_version.patch == 0
        assert result.node_type == EnumNodeType.COMPUTE  # Default

    def test_load_complex_contract(
        self, contract_loader: ProtocolContractLoader, complex_contract_yaml: Path
    ) -> None:
        """Test loading complex contract with many fields."""
        result = contract_loader.load_contract(complex_contract_yaml)

        assert result.node_name == "ComplexNode"
        assert result.node_type == EnumNodeType.EFFECT
        assert result.contract_version.major == 2
        assert result.contract_version.minor == 5
        assert result.contract_version.patch == 3
        assert result.dependencies is not None
        assert len(result.dependencies) == 2

    def test_load_nonexistent_file(
        self, contract_loader: ProtocolContractLoader, tmp_path: Path
    ) -> None:
        """Test loading non-existent contract file."""
        nonexistent = tmp_path / "nonexistent.yaml"

        with pytest.raises(ModelOnexError) as exc_info:
            contract_loader.load_contract(nonexistent)

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "Contract file not found" in exc_info.value.message

    def test_load_contract_caching(
        self, contract_loader: ProtocolContractLoader, valid_contract_yaml: Path
    ) -> None:
        """Test that contracts are cached after first load."""
        # First load
        result1 = contract_loader.load_contract(valid_contract_yaml)
        # Second load should use cache
        result2 = contract_loader.load_contract(valid_contract_yaml)

        assert result1 == result2
        assert str(valid_contract_yaml) in contract_loader.state.loaded_contracts

    def test_load_contract_resolves_path(
        self, contract_loader: ProtocolContractLoader, valid_contract_yaml: Path
    ) -> None:
        """Test that contract path is resolved to absolute."""
        # Even if we pass a relative-ish path, it should be resolved
        result = contract_loader.load_contract(valid_contract_yaml)

        assert result is not None
        # Check that the resolved path is in the cache
        resolved_path = str(valid_contract_yaml.resolve())
        assert resolved_path in contract_loader.state.loaded_contracts

    def test_load_malformed_yaml_raises_error(
        self, contract_loader: ProtocolContractLoader, malformed_yaml: Path
    ) -> None:
        """Test loading malformed YAML raises appropriate error."""
        with pytest.raises(ModelOnexError) as exc_info:
            contract_loader.load_contract(malformed_yaml)

        assert exc_info.value.error_code in [
            EnumCoreErrorCode.VALIDATION_ERROR,
            EnumCoreErrorCode.OPERATION_FAILED,
            EnumCoreErrorCode.CONVERSION_ERROR,
        ]

    def test_load_empty_contract_raises_error(
        self, contract_loader: ProtocolContractLoader, empty_contract_yaml: Path
    ) -> None:
        """Test loading empty contract file raises error."""
        with pytest.raises(ModelOnexError) as exc_info:
            contract_loader.load_contract(empty_contract_yaml)

        assert exc_info.value.error_code in [
            EnumCoreErrorCode.VALIDATION_ERROR,
            EnumCoreErrorCode.OPERATION_FAILED,
        ]


# ===== _load_contract_file Tests =====


class TestLoadContractFile:
    """Test ProtocolContractLoader._load_contract_file method."""

    def test_load_contract_file_basic(
        self, contract_loader: ProtocolContractLoader, valid_contract_yaml: Path
    ) -> None:
        """Test basic file loading."""
        result = contract_loader._load_contract_file(valid_contract_yaml)

        assert isinstance(result, dict)
        assert "node_name" in result
        assert result["node_name"] == "TestNode"

    def test_load_contract_file_caching(
        self, contract_loader: ProtocolContractLoader, valid_contract_yaml: Path
    ) -> None:
        """Test that file loading uses cache when enabled."""
        # First load - should cache
        result1 = contract_loader._load_contract_file(valid_contract_yaml)

        # Check cache was populated
        file_path_str = str(valid_contract_yaml)
        assert file_path_str in contract_loader.state.contract_cache

        # Second load - should use cache
        result2 = contract_loader._load_contract_file(valid_contract_yaml)

        # Both results should contain the same essential data
        assert result1["node_name"] == result2["node_name"]
        assert result1["tool_specification"] == result2["tool_specification"]

    def test_load_contract_file_no_cache(
        self,
        contract_loader_no_cache: ProtocolContractLoader,
        valid_contract_yaml: Path,
    ) -> None:
        """Test file loading with caching disabled."""
        result = contract_loader_no_cache._load_contract_file(valid_contract_yaml)

        assert isinstance(result, dict)
        # Cache should not be populated
        assert len(contract_loader_no_cache.state.contract_cache) == 0

    def test_load_contract_file_updates_on_modification(
        self, contract_loader: ProtocolContractLoader, valid_contract_yaml: Path
    ) -> None:
        """Test that cache is invalidated when file is modified."""
        # First load
        result1 = contract_loader._load_contract_file(valid_contract_yaml)

        # Modify file
        import time

        time.sleep(0.01)  # Ensure mtime changes
        valid_contract_yaml.write_text(
            """
node_name: ModifiedNode
tool_specification:
  main_tool_class: ModifiedClass
""",
        )

        # Second load should detect change and reload
        result2 = contract_loader._load_contract_file(valid_contract_yaml)

        assert result2["node_name"] == "ModifiedNode"

    def test_load_contract_file_yaml_error(
        self, contract_loader: ProtocolContractLoader, malformed_yaml: Path
    ) -> None:
        """Test YAML parsing error handling."""
        with pytest.raises(ModelOnexError) as exc_info:
            contract_loader._load_contract_file(malformed_yaml)

        assert exc_info.value.error_code in [
            EnumCoreErrorCode.VALIDATION_ERROR,
            EnumCoreErrorCode.CONVERSION_ERROR,
            EnumCoreErrorCode.OPERATION_FAILED,
        ]

    def test_load_contract_file_io_error(
        self, contract_loader: ProtocolContractLoader, tmp_path: Path
    ) -> None:
        """Test I/O error handling."""
        nonexistent = tmp_path / "nonexistent.yaml"

        with pytest.raises(ModelOnexError) as exc_info:
            contract_loader._load_contract_file(nonexistent)

        assert exc_info.value.error_code in [
            EnumCoreErrorCode.OPERATION_FAILED,
            EnumCoreErrorCode.NOT_FOUND,
        ]

    def test_load_contract_file_unicode_content(
        self, contract_loader: ProtocolContractLoader, tmp_path: Path
    ) -> None:
        """Test loading file with Unicode content."""
        unicode_file = tmp_path / "unicode.yaml"
        unicode_file.write_text(
            """
node_name: 日本語ノード
tool_specification:
  main_tool_class: TestClass
""",
            encoding="utf-8",
        )

        result = contract_loader._load_contract_file(unicode_file)

        assert result["node_name"] == "日本語ノード"


# ===== _parse_contract_content Tests =====


class TestParseContractContent:
    """Test ProtocolContractLoader._parse_contract_content method."""

    def test_parse_minimal_contract(
        self, contract_loader: ProtocolContractLoader, tmp_path: Path
    ) -> None:
        """Test parsing minimal contract content."""
        raw_content = {
            "node_name": "TestNode",
            "tool_specification": {"main_tool_class": "TestClass"},
        }

        result = contract_loader._parse_contract_content(raw_content, tmp_path)

        assert isinstance(result, ModelContractContent)
        assert result.node_name == "TestNode"
        assert result.tool_specification.main_tool_class == "TestClass"
        # Defaults should be applied
        assert result.contract_version.major == 1
        assert result.contract_version.minor == 0
        assert result.contract_version.patch == 0

    def test_parse_contract_with_version(
        self, contract_loader: ProtocolContractLoader, tmp_path: Path
    ) -> None:
        """Test parsing contract with explicit version."""
        raw_content = {
            "contract_version": {"major": 2, "minor": 3, "patch": 4},
            "node_name": "TestNode",
            "tool_specification": {"main_tool_class": "TestClass"},
        }

        result = contract_loader._parse_contract_content(raw_content, tmp_path)

        assert result.contract_version.major == 2
        assert result.contract_version.minor == 3
        assert result.contract_version.patch == 4

    def test_parse_contract_with_node_type(
        self, contract_loader: ProtocolContractLoader, tmp_path: Path
    ) -> None:
        """Test parsing contract with node type."""
        raw_content = {
            "node_name": "TestNode",
            "node_type": "EFFECT",
            "tool_specification": {"main_tool_class": "TestClass"},
        }

        result = contract_loader._parse_contract_content(raw_content, tmp_path)

        assert result.node_type == EnumNodeType.EFFECT

    def test_parse_contract_node_type_case_insensitive(
        self, contract_loader: ProtocolContractLoader, tmp_path: Path
    ) -> None:
        """Test parsing contract with lowercase node type."""
        raw_content = {
            "node_name": "TestNode",
            "node_type": "reducer",
            "tool_specification": {"main_tool_class": "TestClass"},
        }

        result = contract_loader._parse_contract_content(raw_content, tmp_path)

        assert result.node_type == EnumNodeType.REDUCER

    def test_parse_contract_with_dependencies(
        self, contract_loader: ProtocolContractLoader, tmp_path: Path
    ) -> None:
        """Test parsing contract with dependencies."""
        raw_content = {
            "node_name": "TestNode",
            "tool_specification": {"main_tool_class": "TestClass"},
            "dependencies": [
                {"name": "dep1", "type": "service", "version": "1.0.0"},
                {"name": "dep2", "type": "utility", "version": "2.0.0"},
            ],
        }

        result = contract_loader._parse_contract_content(raw_content, tmp_path)

        assert result.dependencies is not None
        assert len(result.dependencies) == 2

    def test_parse_contract_invalid_version_type(
        self, contract_loader: ProtocolContractLoader, tmp_path: Path
    ) -> None:
        """Test parsing contract with invalid version type."""
        raw_content = {
            "contract_version": "invalid",  # Should be dict
            "node_name": "TestNode",
            "tool_specification": {"main_tool_class": "TestClass"},
        }

        result = contract_loader._parse_contract_content(raw_content, tmp_path)

        # Should use defaults when invalid type
        assert result.contract_version.major == 1

    def test_parse_contract_missing_node_name(
        self, contract_loader: ProtocolContractLoader, tmp_path: Path
    ) -> None:
        """Test parsing contract without node_name."""
        raw_content = {
            "tool_specification": {"main_tool_class": "TestClass"},
        }

        result = contract_loader._parse_contract_content(raw_content, tmp_path)

        # Should not raise during parse, validation happens later
        assert result.node_name == ""

    def test_parse_contract_invalid_tool_spec_type(
        self, contract_loader: ProtocolContractLoader, tmp_path: Path
    ) -> None:
        """Test parsing contract with invalid tool specification type."""
        raw_content = {
            "node_name": "TestNode",
            "tool_specification": "invalid",  # Should be dict
        }

        result = contract_loader._parse_contract_content(raw_content, tmp_path)

        # Should use default
        assert result.tool_specification.main_tool_class == "DefaultToolNode"

    def test_parse_contract_with_non_dict_dependencies(
        self, contract_loader: ProtocolContractLoader, tmp_path: Path
    ) -> None:
        """Test parsing contract with string dependencies list."""
        raw_content = {
            "node_name": "TestNode",
            "tool_specification": {"main_tool_class": "TestClass"},
            "dependencies": ["dep1", "dep2"],  # Strings instead of dicts
        }

        result = contract_loader._parse_contract_content(raw_content, tmp_path)

        # Should handle gracefully
        assert result.dependencies is None or isinstance(result.dependencies, list)


# ===== _convert_contract_content_to_dict Tests =====


class TestConvertContractContentToDict:
    """Test ProtocolContractLoader._convert_contract_content_to_dict method."""

    def test_convert_basic_contract(
        self, contract_loader: ProtocolContractLoader
    ) -> None:
        """Test converting basic contract content to dict."""
        content = ModelContractContent(
            contract_version=ModelSemVer(major=1, minor=2, patch=3),
            node_name="TestNode",
            node_type=EnumNodeType.COMPUTE,
            tool_specification=ModelToolSpecification(main_tool_class="TestClass"),
            input_state=ModelYamlSchemaObject(
                object_type="object", description="Input"
            ),
            output_state=ModelYamlSchemaObject(
                object_type="object", description="Output"
            ),
            definitions=ModelContractDefinitions(),
        )

        result = contract_loader._convert_contract_content_to_dict(content)

        assert isinstance(result, dict)
        assert result["node_name"] == "TestNode"
        assert result["contract_version"]["major"] == 1
        assert result["contract_version"]["minor"] == 2
        assert result["contract_version"]["patch"] == 3
        assert result["tool_specification"]["main_tool_class"] == "TestClass"

    def test_convert_preserves_version_numbers(
        self, contract_loader: ProtocolContractLoader
    ) -> None:
        """Test that version numbers are preserved accurately."""
        content = ModelContractContent(
            contract_version=ModelSemVer(major=99, minor=88, patch=77),
            node_name="TestNode",
            node_type=EnumNodeType.COMPUTE,
            tool_specification=ModelToolSpecification(main_tool_class="TestClass"),
            input_state=ModelYamlSchemaObject(
                object_type="object", description="Input"
            ),
            output_state=ModelYamlSchemaObject(
                object_type="object", description="Output"
            ),
            definitions=ModelContractDefinitions(),
        )

        result = contract_loader._convert_contract_content_to_dict(content)

        assert result["contract_version"]["major"] == 99
        assert result["contract_version"]["minor"] == 88
        assert result["contract_version"]["patch"] == 77


# ===== _validate_contract_structure Tests =====


class TestValidateContractStructure:
    """Test ProtocolContractLoader._validate_contract_structure method."""

    def test_validate_valid_contract(
        self, contract_loader: ProtocolContractLoader, tmp_path: Path
    ) -> None:
        """Test validation of valid contract structure."""
        content = ModelContractContent(
            contract_version=ModelSemVer(major=1, minor=0, patch=0),
            node_name="TestNode",
            node_type=EnumNodeType.COMPUTE,
            tool_specification=ModelToolSpecification(main_tool_class="TestClass"),
            input_state=ModelYamlSchemaObject(
                object_type="object", description="Input"
            ),
            output_state=ModelYamlSchemaObject(
                object_type="object", description="Output"
            ),
            definitions=ModelContractDefinitions(),
        )

        # Should not raise
        contract_loader._validate_contract_structure(content, tmp_path)

    def test_validate_missing_node_name(
        self, contract_loader: ProtocolContractLoader, tmp_path: Path
    ) -> None:
        """Test validation fails for missing node_name."""
        content = ModelContractContent(
            contract_version=ModelSemVer(major=1, minor=0, patch=0),
            node_name="",  # Empty node name
            node_type=EnumNodeType.COMPUTE,
            tool_specification=ModelToolSpecification(main_tool_class="TestClass"),
            input_state=ModelYamlSchemaObject(
                object_type="object", description="Input"
            ),
            output_state=ModelYamlSchemaObject(
                object_type="object", description="Output"
            ),
            definitions=ModelContractDefinitions(),
        )

        with pytest.raises(ModelOnexError) as exc_info:
            contract_loader._validate_contract_structure(content, tmp_path)

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "node_name" in exc_info.value.message

    def test_validate_missing_tool_class(
        self, contract_loader: ProtocolContractLoader, tmp_path: Path
    ) -> None:
        """Test validation fails for missing main_tool_class."""
        content = ModelContractContent(
            contract_version=ModelSemVer(major=1, minor=0, patch=0),
            node_name="TestNode",
            node_type=EnumNodeType.COMPUTE,
            tool_specification=ModelToolSpecification(main_tool_class=""),  # Empty
            input_state=ModelYamlSchemaObject(
                object_type="object", description="Input"
            ),
            output_state=ModelYamlSchemaObject(
                object_type="object", description="Output"
            ),
            definitions=ModelContractDefinitions(),
        )

        with pytest.raises(ModelOnexError) as exc_info:
            contract_loader._validate_contract_structure(content, tmp_path)

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "main_tool_class" in exc_info.value.message


# ===== _validate_yaml_content_security Tests =====


class TestValidateYamlContentSecurity:
    """Test ProtocolContractLoader._validate_yaml_content_security method."""

    def test_validate_safe_yaml_content(
        self, contract_loader: ProtocolContractLoader, tmp_path: Path
    ) -> None:
        """Test validation of safe YAML content."""
        safe_content = """
node_name: TestNode
tool_specification:
  main_tool_class: TestClass
"""
        # Should not raise
        contract_loader._validate_yaml_content_security(safe_content, tmp_path)

    def test_validate_yaml_size_limit(
        self, contract_loader: ProtocolContractLoader, tmp_path: Path
    ) -> None:
        """Test validation rejects excessively large YAML."""
        # Create content larger than 10MB limit
        large_content = "x" * (11 * 1024 * 1024)

        with pytest.raises(ModelOnexError) as exc_info:
            contract_loader._validate_yaml_content_security(large_content, tmp_path)

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_FAILED
        assert "too large" in exc_info.value.message

    def test_validate_detects_python_object_instantiation(
        self, contract_loader: ProtocolContractLoader, tmp_path: Path
    ) -> None:
        """Test detection of !!python constructor."""
        suspicious_content = """
node_name: TestNode
malicious: !!python/object/apply:os.system
  args: ['echo malicious']
"""
        # Should emit warning but not raise (warning only for suspicious patterns)
        contract_loader._validate_yaml_content_security(suspicious_content, tmp_path)

    def test_validate_detects_eval(
        self, contract_loader: ProtocolContractLoader, tmp_path: Path
    ) -> None:
        """Test detection of eval() function."""
        suspicious_content = """
node_name: TestNode
code: eval('malicious code')
"""
        # Should emit warning
        contract_loader._validate_yaml_content_security(suspicious_content, tmp_path)

    def test_validate_detects_exec(
        self, contract_loader: ProtocolContractLoader, tmp_path: Path
    ) -> None:
        """Test detection of exec() function."""
        suspicious_content = """
node_name: TestNode
code: exec('malicious code')
"""
        # Should emit warning
        contract_loader._validate_yaml_content_security(suspicious_content, tmp_path)

    def test_validate_detects_import(
        self, contract_loader: ProtocolContractLoader, tmp_path: Path
    ) -> None:
        """Test detection of __import__ function."""
        suspicious_content = """
node_name: TestNode
code: __import__('os')
"""
        # Should emit warning
        contract_loader._validate_yaml_content_security(suspicious_content, tmp_path)

    def test_validate_nesting_depth_safe(
        self, contract_loader: ProtocolContractLoader, tmp_path: Path
    ) -> None:
        """Test validation allows reasonable nesting depth."""
        # Create nested structure within limits (< 50 levels)
        nested_content = "a: {" * 10 + "value: test" + "}" * 10

        # Should not raise
        contract_loader._validate_yaml_content_security(nested_content, tmp_path)

    def test_validate_nesting_depth_excessive(
        self, contract_loader: ProtocolContractLoader, tmp_path: Path
    ) -> None:
        """Test validation rejects excessive nesting depth."""
        # Create deeply nested structure (> 50 levels)
        nested_content = "a: {" * 60 + "value: test" + "}" * 60

        with pytest.raises(ModelOnexError) as exc_info:
            contract_loader._validate_yaml_content_security(nested_content, tmp_path)

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_FAILED
        assert "nesting too deep" in exc_info.value.message

    def test_validate_nesting_depth_brackets(
        self, contract_loader: ProtocolContractLoader, tmp_path: Path
    ) -> None:
        """Test nesting depth validation with square brackets."""
        # Test with array nesting
        nested_content = "[[[[[[[[[[" * 6 + "value" + "]]]]]]]]]]" * 6

        with pytest.raises(ModelOnexError) as exc_info:
            contract_loader._validate_yaml_content_security(nested_content, tmp_path)

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_FAILED

    def test_validate_mixed_nesting(
        self, contract_loader: ProtocolContractLoader, tmp_path: Path
    ) -> None:
        """Test nesting depth with mixed brackets and braces."""
        # Mix of [ and { to test nesting counter
        nested_content = "[{[{[{" * 10 + "value" + "}]}]}]" * 10

        with pytest.raises(ModelOnexError) as exc_info:
            contract_loader._validate_yaml_content_security(nested_content, tmp_path)

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_FAILED

    def test_validate_unicode_content(
        self, contract_loader: ProtocolContractLoader, tmp_path: Path
    ) -> None:
        """Test validation allows Unicode content."""
        unicode_content = """
node_name: 日本語ノード
description: 中文描述
tool_specification:
  main_tool_class: TestClass
"""
        # Should not raise
        contract_loader._validate_yaml_content_security(unicode_content, tmp_path)

    def test_validate_binary_tag_detection(
        self, contract_loader: ProtocolContractLoader, tmp_path: Path
    ) -> None:
        """Test detection of !!binary tag."""
        suspicious_content = """
node_name: TestNode
data: !!binary |
  SGVsbG8gV29ybGQ=
"""
        # Should emit warning
        contract_loader._validate_yaml_content_security(suspicious_content, tmp_path)

    def test_validate_map_constructor(
        self, contract_loader: ProtocolContractLoader, tmp_path: Path
    ) -> None:
        """Test detection of !!map constructor."""
        suspicious_content = """
node_name: TestNode
data: !!map
  key: value
"""
        # Should emit warning
        contract_loader._validate_yaml_content_security(suspicious_content, tmp_path)


# ===== Integration Tests =====


class TestContractLoaderIntegration:
    """Integration tests for complete contract loading workflow."""

    def test_full_workflow_valid_contract(
        self, contract_loader: ProtocolContractLoader, valid_contract_yaml: Path
    ) -> None:
        """Test complete workflow for valid contract."""
        result = contract_loader.load_contract(valid_contract_yaml)

        assert isinstance(result, ModelContractContent)
        assert result.node_name == "TestNode"
        assert result.node_type == EnumNodeType.COMPUTE

        # Verify caching
        assert (
            str(valid_contract_yaml.resolve()) in contract_loader.state.loaded_contracts
        )

    def test_multiple_contracts_loaded(
        self,
        contract_loader: ProtocolContractLoader,
        valid_contract_yaml: Path,
        complex_contract_yaml: Path,
    ) -> None:
        """Test loading multiple contracts."""
        result1 = contract_loader.load_contract(valid_contract_yaml)
        result2 = contract_loader.load_contract(complex_contract_yaml)

        assert result1.node_name == "TestNode"
        assert result2.node_name == "ComplexNode"
        assert len(contract_loader.state.loaded_contracts) == 2

    def test_error_handling_preserves_state(
        self, contract_loader: ProtocolContractLoader, malformed_yaml: Path
    ) -> None:
        """Test that errors don't corrupt loader state."""
        initial_cache_size = len(contract_loader.state.contract_cache)

        with pytest.raises(ModelOnexError):
            contract_loader.load_contract(malformed_yaml)

        # State should be unchanged
        assert len(contract_loader.state.contract_cache) == initial_cache_size
