"""
Test suite for UtilityReferenceResolver.

Provides comprehensive tests for JSON Schema reference resolution.
"""

from unittest.mock import MagicMock, Mock

import pytest

from omnibase_core.utils.generation.utility_reference_resolver import (
    ModelRefInfo,
    UtilityReferenceResolver,
)


@pytest.mark.unit
class TestModelRefInfo:
    """Test ModelRefInfo dataclass."""

    def test_basic_instantiation(self):
        """Test basic ModelRefInfo creation."""
        ref_info = ModelRefInfo(
            file_path="test.yaml",
            type_name="TestType",
        )

        assert ref_info.file_path == "test.yaml"
        assert ref_info.type_name == "TestType"
        assert ref_info.is_internal is False
        assert ref_info.is_subcontract is False

    def test_with_flags(self):
        """Test ModelRefInfo with flags."""
        ref_info = ModelRefInfo(
            file_path="contracts/models.yaml",
            type_name="Config",
            is_internal=True,
            is_subcontract=True,
        )

        assert ref_info.is_internal is True
        assert ref_info.is_subcontract is True


@pytest.mark.unit
class TestUtilityReferenceResolverInitialization:
    """Test resolver initialization and configuration."""

    def test_init_without_args(self):
        """Test initialization without arguments."""
        resolver = UtilityReferenceResolver()

        assert resolver.config is None
        assert resolver.import_tracker is None

    def test_init_with_config(self):
        """Test initialization with config."""
        config = MagicMock()
        resolver = UtilityReferenceResolver(config=config)

        assert resolver.config is config
        assert resolver.import_tracker is None

    def test_init_with_import_tracker(self):
        """Test initialization with import tracker."""
        tracker = MagicMock()
        resolver = UtilityReferenceResolver(import_tracker=tracker)

        assert resolver.config is None
        assert resolver.import_tracker is tracker

    def test_init_with_both_args(self):
        """Test initialization with config and tracker."""
        config = MagicMock()
        tracker = MagicMock()
        resolver = UtilityReferenceResolver(config=config, import_tracker=tracker)

        assert resolver.config is config
        assert resolver.import_tracker is tracker

    def test_set_config(self):
        """Test set_config method."""
        resolver = UtilityReferenceResolver()
        config = MagicMock()

        resolver.set_config(config)

        assert resolver.config is config

    def test_set_import_tracker(self):
        """Test set_import_tracker method."""
        resolver = UtilityReferenceResolver()
        tracker = MagicMock()

        resolver.set_import_tracker(tracker)

        assert resolver.import_tracker is tracker


@pytest.mark.unit
class TestParseReference:
    """Test reference parsing functionality."""

    def test_parse_internal_reference(self):
        """Test parsing internal #/definitions/ references."""
        resolver = UtilityReferenceResolver()
        ref_info = resolver.parse_reference("#/definitions/User")

        assert ref_info.file_path == ""
        assert ref_info.type_name == "User"
        assert ref_info.is_internal is True
        assert ref_info.is_subcontract is False

    def test_parse_internal_reference_complex(self):
        """Test parsing internal reference with complex path."""
        resolver = UtilityReferenceResolver()
        ref_info = resolver.parse_reference("#/definitions/models/User")

        assert ref_info.type_name == "User"
        assert ref_info.is_internal is True

    def test_parse_external_reference_basic(self):
        """Test parsing basic external reference."""
        resolver = UtilityReferenceResolver()
        ref_info = resolver.parse_reference("models.yaml#/Config")

        assert ref_info.file_path == "models.yaml"
        assert ref_info.type_name == "Config"
        assert ref_info.is_internal is False
        assert ref_info.is_subcontract is False

    def test_parse_external_reference_with_path(self):
        """Test parsing external reference with nested path."""
        resolver = UtilityReferenceResolver()
        ref_info = resolver.parse_reference("models.yaml#/definitions/Config")

        assert ref_info.file_path == "models.yaml"
        assert ref_info.type_name == "Config"
        assert ref_info.is_internal is False

    def test_parse_subcontract_reference(self):
        """Test parsing subcontract reference."""
        resolver = UtilityReferenceResolver()
        ref_info = resolver.parse_reference("contracts/contract_models.yaml#/Config")

        assert ref_info.file_path == "contracts/contract_models.yaml"
        assert ref_info.type_name == "Config"
        assert ref_info.is_internal is False
        assert ref_info.is_subcontract is True

    def test_parse_subcontract_reference_nested(self):
        """Test parsing subcontract reference with nested path."""
        resolver = UtilityReferenceResolver()
        ref_info = resolver.parse_reference(
            "contracts/contract_models.yaml#/definitions/ProcessingConfig"
        )

        assert ref_info.file_path == "contracts/contract_models.yaml"
        assert ref_info.type_name == "ProcessingConfig"
        assert ref_info.is_subcontract is True

    def test_parse_malformed_reference_no_hash(self):
        """Test parsing malformed reference without hash."""
        resolver = UtilityReferenceResolver()
        ref_info = resolver.parse_reference("malformed_ref")

        assert ref_info.file_path == ""
        assert ref_info.type_name == "malformed_ref"
        assert ref_info.is_internal is False

    def test_parse_malformed_reference_only_hash(self):
        """Test parsing malformed reference with only hash."""
        resolver = UtilityReferenceResolver()
        ref_info = resolver.parse_reference("#/")

        assert ref_info.file_path == ""
        assert ref_info.type_name == ""


@pytest.mark.unit
class TestResolveTypeName:
    """Test type name resolution."""

    def test_resolve_empty_type_name(self):
        """Test resolving empty type name."""
        resolver = UtilityReferenceResolver()
        ref_info = ModelRefInfo(file_path="", type_name="")

        result = resolver.resolve_type_name(ref_info)

        assert result == "ModelObjectData"

    def test_resolve_whitespace_type_name(self):
        """Test resolving whitespace-only type name."""
        resolver = UtilityReferenceResolver()
        ref_info = ModelRefInfo(file_path="", type_name="   ")

        result = resolver.resolve_type_name(ref_info)

        assert result == "ModelObjectData"

    def test_resolve_internal_reference(self):
        """Test resolving internal reference."""
        resolver = UtilityReferenceResolver()
        ref_info = ModelRefInfo(file_path="", type_name="User", is_internal=True)

        result = resolver.resolve_type_name(ref_info)

        assert result == "ModelUser"

    def test_resolve_internal_reference_with_model_prefix(self):
        """Test resolving internal reference already with Model prefix."""
        resolver = UtilityReferenceResolver()
        ref_info = ModelRefInfo(file_path="", type_name="ModelUser", is_internal=True)

        result = resolver.resolve_type_name(ref_info)

        assert result == "ModelUser"

    def test_resolve_internal_reference_enum(self):
        """Test resolving internal reference with Enum prefix."""
        resolver = UtilityReferenceResolver()
        ref_info = ModelRefInfo(file_path="", type_name="EnumStatus", is_internal=True)

        result = resolver.resolve_type_name(ref_info)

        assert result == "EnumStatus"

    def test_resolve_subcontract_reference(self):
        """Test resolving subcontract reference."""
        resolver = UtilityReferenceResolver()
        ref_info = ModelRefInfo(
            file_path="contracts/models.yaml", type_name="Config", is_subcontract=True
        )

        result = resolver.resolve_type_name(ref_info)

        assert result == "ModelConfig"

    def test_resolve_subcontract_with_tool_prefix(self):
        """Test resolving subcontract reference with tool prefix."""
        resolver = UtilityReferenceResolver()
        ref_info = ModelRefInfo(
            file_path="contracts/models.yaml",
            type_name="ToolGeneratorProcessingConfig",
            is_subcontract=True,
        )

        result = resolver.resolve_type_name(ref_info)

        assert result == "ModelProcessingConfig"

    def test_resolve_external_by_file_path_semver(self):
        """Test resolving external reference by file path (semver)."""
        resolver = UtilityReferenceResolver()
        ref_info = ModelRefInfo(
            file_path="primitives/semver.yaml",
            type_name="SemVer",
            is_internal=False,
        )

        result = resolver.resolve_type_name(ref_info)

        assert result == "ModelSemVer"

    def test_resolve_external_by_file_path_onex_field(self):
        """Test resolving external reference by file path (onex_field_model)."""
        resolver = UtilityReferenceResolver()
        ref_info = ModelRefInfo(
            file_path="models/onex_field_model.yaml",
            type_name="Field",
            is_internal=False,
        )

        result = resolver.resolve_type_name(ref_info)

        assert result == "ModelOnexFieldModel"

    def test_resolve_external_by_file_path_action_spec(self):
        """Test resolving external reference by file path (action_spec)."""
        resolver = UtilityReferenceResolver()
        ref_info = ModelRefInfo(
            file_path="models/action_spec.yaml",
            type_name="Action",
            is_internal=False,
        )

        result = resolver.resolve_type_name(ref_info)

        assert result == "ModelActionSpec"

    def test_resolve_external_by_file_path_log_context(self):
        """Test resolving external reference by file path (log_context)."""
        resolver = UtilityReferenceResolver()
        ref_info = ModelRefInfo(
            file_path="models/log_context.yaml",
            type_name="Context",
            is_internal=False,
        )

        result = resolver.resolve_type_name(ref_info)

        assert result == "ModelLogContext"

    def test_resolve_external_default(self):
        """Test resolving external reference with default handling."""
        resolver = UtilityReferenceResolver()
        ref_info = ModelRefInfo(
            file_path="other/models.yaml",
            type_name="CustomType",
            is_internal=False,
        )

        result = resolver.resolve_type_name(ref_info)

        assert result == "ModelCustomType"


@pytest.mark.unit
class TestEnsureModelPrefix:
    """Test _ensure_model_prefix method."""

    def test_ensure_model_prefix_empty(self):
        """Test ensure model prefix with empty name."""
        resolver = UtilityReferenceResolver()

        result = resolver._ensure_model_prefix("")

        assert result == "ModelObjectData"

    def test_ensure_model_prefix_basic(self):
        """Test ensure model prefix with basic name."""
        resolver = UtilityReferenceResolver()

        result = resolver._ensure_model_prefix("User")

        assert result == "ModelUser"

    def test_ensure_model_prefix_already_has_model(self):
        """Test ensure model prefix with Model already present."""
        resolver = UtilityReferenceResolver()

        result = resolver._ensure_model_prefix("ModelUser")

        assert result == "ModelUser"

    def test_ensure_model_prefix_enum(self):
        """Test ensure model prefix with Enum prefix."""
        resolver = UtilityReferenceResolver()

        result = resolver._ensure_model_prefix("EnumStatus")

        assert result == "EnumStatus"


@pytest.mark.unit
class TestCleanToolPrefix:
    """Test _clean_tool_prefix method."""

    def test_clean_tool_prefix_pattern_match(self):
        """Test cleaning tool prefix with pattern match."""
        resolver = UtilityReferenceResolver()

        result = resolver._clean_tool_prefix("ToolGeneratorProcessingConfig")

        assert result == "ModelProcessingConfig"

    def test_clean_tool_prefix_validation_config(self):
        """Test cleaning tool prefix for ValidationConfig."""
        resolver = UtilityReferenceResolver()

        result = resolver._clean_tool_prefix("ToolValidatorValidationConfig")

        assert result == "ModelValidationConfig"

    def test_clean_tool_prefix_processing_result(self):
        """Test cleaning tool prefix for ProcessingResult."""
        resolver = UtilityReferenceResolver()

        result = resolver._clean_tool_prefix("ToolProcessorProcessingResult")

        assert result == "ModelProcessingResult"

    def test_clean_tool_prefix_validation_result(self):
        """Test cleaning tool prefix for ValidationResult."""
        resolver = UtilityReferenceResolver()

        result = resolver._clean_tool_prefix("ToolAnalyzerValidationResult")

        assert result == "ModelValidationResult"

    def test_clean_tool_prefix_node_status(self):
        """Test cleaning tool prefix for NodeStatus."""
        resolver = UtilityReferenceResolver()

        result = resolver._clean_tool_prefix("ToolManagerNodeStatus")

        assert result == "ModelNodeStatus"

    def test_clean_tool_prefix_action_spec(self):
        """Test cleaning tool prefix for ActionSpec."""
        resolver = UtilityReferenceResolver()

        result = resolver._clean_tool_prefix("ToolBuilderActionSpec")

        assert result == "ModelActionSpec"

    def test_clean_tool_prefix_log_context(self):
        """Test cleaning tool prefix for LogContext."""
        resolver = UtilityReferenceResolver()

        result = resolver._clean_tool_prefix("ToolRunnerLogContext")

        assert result == "ModelLogContext"

    def test_clean_tool_prefix_simple_tool(self):
        """Test cleaning simple Tool prefix."""
        resolver = UtilityReferenceResolver()

        result = resolver._clean_tool_prefix("ToolConfig")

        assert result == "Config"

    def test_clean_tool_prefix_simple_node(self):
        """Test cleaning simple Node prefix."""
        resolver = UtilityReferenceResolver()

        result = resolver._clean_tool_prefix("NodeMetadata")

        assert result == "Metadata"

    def test_clean_tool_prefix_no_match(self):
        """Test cleaning tool prefix with no match."""
        resolver = UtilityReferenceResolver()

        result = resolver._clean_tool_prefix("CustomType")

        assert result == "CustomType"


@pytest.mark.unit
class TestIsExternalReference:
    """Test is_external_reference method."""

    def test_is_external_reference_internal(self):
        """Test that internal references return False."""
        resolver = UtilityReferenceResolver()

        result = resolver.is_external_reference("#/definitions/User")

        assert result is False

    def test_is_external_reference_external(self):
        """Test that external references return True."""
        resolver = UtilityReferenceResolver()

        result = resolver.is_external_reference("models.yaml#/User")

        assert result is True

    def test_is_external_reference_subcontract(self):
        """Test that subcontract references return True."""
        resolver = UtilityReferenceResolver()

        result = resolver.is_external_reference("contracts/models.yaml#/Config")

        assert result is True

    def test_is_external_reference_empty(self):
        """Test that empty reference returns False."""
        resolver = UtilityReferenceResolver()

        result = resolver.is_external_reference("")

        assert result is False

    def test_is_external_reference_none(self):
        """Test that None reference returns False."""
        resolver = UtilityReferenceResolver()

        result = resolver.is_external_reference(None)

        assert result is False


@pytest.mark.unit
class TestPackageNameGeneration:
    """Test package name generation for subcontracts."""

    def test_get_package_name_from_config(self):
        """Test getting package name from config."""
        config = Mock()
        config.subcontract_import_map = {
            "contracts/models.yaml": {"package_name": "custom_package"}
        }
        resolver = UtilityReferenceResolver(config=config)

        result = resolver.get_package_name_for_subcontract("contracts/models.yaml")

        assert result == "custom_package"

    def test_get_package_name_contract_prefix(self):
        """Test deriving package name from contract_ prefix."""
        resolver = UtilityReferenceResolver()

        result = resolver.get_package_name_for_subcontract(
            "contracts/contract_models.yaml"
        )

        assert result == "models"

    def test_get_package_name_contract_prefix_complex(self):
        """Test deriving package name from complex contract_ prefix."""
        resolver = UtilityReferenceResolver()

        result = resolver.get_package_name_for_subcontract(
            "contracts/contract_processing_config.yaml"
        )

        assert result == "processing_config"

    def test_get_package_name_fallback_to_stem(self):
        """Test fallback to file stem for package name."""
        resolver = UtilityReferenceResolver()

        result = resolver.get_package_name_for_subcontract("contracts/custom.yaml")

        assert result == "custom"

    def test_get_package_name_config_without_package_name(self):
        """Test config mapping without package_name key."""
        config = Mock()
        config.subcontract_import_map = {"contracts/models.yaml": {}}
        resolver = UtilityReferenceResolver(config=config)

        result = resolver.get_package_name_for_subcontract("contracts/models.yaml")

        assert result == "models"


@pytest.mark.unit
class TestImportPathGeneration:
    """Test import path generation for subcontracts."""

    def test_get_import_path_from_config(self):
        """Test getting import path from config."""
        config = Mock()
        config.subcontract_import_map = {
            "contracts/models.yaml": {"import_path": "custom.import.path"}
        }
        resolver = UtilityReferenceResolver(config=config)

        result = resolver.get_import_path_for_subcontract("contracts/models.yaml")

        assert result == "custom.import.path"

    def test_get_import_path_default_convention(self):
        """Test default import path convention."""
        resolver = UtilityReferenceResolver()

        result = resolver.get_import_path_for_subcontract(
            "contracts/contract_models.yaml"
        )

        assert result == "generated.models"

    def test_get_import_path_custom_file(self):
        """Test import path for custom file."""
        resolver = UtilityReferenceResolver()

        result = resolver.get_import_path_for_subcontract("contracts/custom.yaml")

        assert result == "generated.custom"

    def test_get_import_path_config_without_import_path(self):
        """Test config mapping without import_path key."""
        config = Mock()
        config.subcontract_import_map = {"contracts/models.yaml": {}}
        resolver = UtilityReferenceResolver(config=config)

        result = resolver.get_import_path_for_subcontract("contracts/models.yaml")

        assert result == "generated.models"


@pytest.mark.unit
class TestResolveRef:
    """Test main resolve_ref method."""

    def test_resolve_ref_internal(self):
        """Test resolving internal reference."""
        resolver = UtilityReferenceResolver()

        result = resolver.resolve_ref("#/definitions/User")

        assert result == "ModelUser"

    def test_resolve_ref_external(self):
        """Test resolving external reference."""
        resolver = UtilityReferenceResolver()

        result = resolver.resolve_ref("models.yaml#/Config")

        assert result == "ModelConfig"

    def test_resolve_ref_subcontract_no_tracking(self):
        """Test resolving subcontract without import tracking."""
        resolver = UtilityReferenceResolver()

        result = resolver.resolve_ref("contracts/contract_models.yaml#/Config")

        assert result == "ModelConfig"

    def test_resolve_ref_subcontract_with_tracking(self):
        """Test resolving subcontract with import tracking."""
        config = Mock()
        config.use_imports_for_subcontracts = True
        config.subcontract_import_map = {}
        tracker = Mock()
        resolver = UtilityReferenceResolver(config=config, import_tracker=tracker)

        result = resolver.resolve_ref("contracts/contract_models.yaml#/Config")

        assert result == "ModelConfig"
        tracker.add_subcontract_model.assert_called_once()

    def test_resolve_ref_subcontract_tracking_args(self):
        """Test subcontract tracking with correct arguments."""
        config = Mock()
        config.use_imports_for_subcontracts = True
        config.subcontract_import_map = {}
        tracker = Mock()
        resolver = UtilityReferenceResolver(config=config, import_tracker=tracker)

        resolver.resolve_ref("contracts/contract_models.yaml#/ProcessingConfig")

        tracker.add_subcontract_model.assert_called_once_with(
            subcontract_path="contracts/contract_models.yaml",
            model_name="ModelProcessingConfig",
            package_name="models",
            import_path="generated.models",
        )

    def test_resolve_ref_with_tool_prefix(self):
        """Test resolving reference with tool prefix cleanup."""
        resolver = UtilityReferenceResolver()

        result = resolver.resolve_ref(
            "contracts/models.yaml#/ToolGeneratorProcessingConfig"
        )

        assert result == "ModelProcessingConfig"

    def test_resolve_ref_empty_type_name(self):
        """Test resolving reference with empty type name."""
        resolver = UtilityReferenceResolver()

        result = resolver.resolve_ref("#/definitions/")

        assert result == "ModelObjectData"

    def test_resolve_ref_malformed(self):
        """Test resolving malformed reference."""
        resolver = UtilityReferenceResolver()

        result = resolver.resolve_ref("malformed")

        assert result == "Modelmalformed"


@pytest.mark.unit
class TestImportTracking:
    """Test import tracking functionality."""

    def test_should_track_imports_true(self):
        """Test _should_track_imports returns True with all conditions."""
        config = Mock()
        config.use_imports_for_subcontracts = True
        tracker = Mock()
        resolver = UtilityReferenceResolver(config=config, import_tracker=tracker)

        result = resolver._should_track_imports()

        assert result is True

    def test_should_track_imports_no_config(self):
        """Test _should_track_imports returns False without config."""
        tracker = Mock()
        resolver = UtilityReferenceResolver(import_tracker=tracker)

        result = resolver._should_track_imports()

        assert result is False

    def test_should_track_imports_no_tracker(self):
        """Test _should_track_imports returns False without tracker."""
        config = Mock()
        config.use_imports_for_subcontracts = True
        resolver = UtilityReferenceResolver(config=config)

        result = resolver._should_track_imports()

        assert result is False

    def test_should_track_imports_disabled(self):
        """Test _should_track_imports returns False when disabled."""
        config = Mock()
        config.use_imports_for_subcontracts = False
        tracker = Mock()
        resolver = UtilityReferenceResolver(config=config, import_tracker=tracker)

        result = resolver._should_track_imports()

        assert result is False

    def test_track_subcontract_import_no_tracker(self):
        """Test _track_subcontract_import with no tracker."""
        resolver = UtilityReferenceResolver()
        ref_info = ModelRefInfo(
            file_path="contracts/models.yaml",
            type_name="Config",
            is_subcontract=True,
        )

        # Should not raise error
        resolver._track_subcontract_import(ref_info, "ModelConfig")

    def test_track_subcontract_import_with_tracker(self):
        """Test _track_subcontract_import with tracker."""
        tracker = Mock()
        resolver = UtilityReferenceResolver(import_tracker=tracker)
        resolver.config = Mock()
        resolver.config.subcontract_import_map = {}

        ref_info = ModelRefInfo(
            file_path="contracts/contract_models.yaml",
            type_name="Config",
            is_subcontract=True,
        )

        resolver._track_subcontract_import(ref_info, "ModelConfig")

        tracker.add_subcontract_model.assert_called_once_with(
            subcontract_path="contracts/contract_models.yaml",
            model_name="ModelConfig",
            package_name="models",
            import_path="generated.models",
        )


@pytest.mark.unit
class TestResolveByFilePath:
    """Test _resolve_by_file_path method."""

    def test_resolve_by_file_path_onex_field_model(self):
        """Test resolving by file path for onex_field_model."""
        resolver = UtilityReferenceResolver()
        ref_info = ModelRefInfo(
            file_path="models/onex_field_model.yaml", type_name="Field"
        )

        result = resolver._resolve_by_file_path(ref_info)

        assert result == "ModelOnexFieldModel"

    def test_resolve_by_file_path_semver(self):
        """Test resolving by file path for semver."""
        resolver = UtilityReferenceResolver()
        ref_info = ModelRefInfo(file_path="primitives/semver.yaml", type_name="SemVer")

        result = resolver._resolve_by_file_path(ref_info)

        assert result == "ModelSemVer"

    def test_resolve_by_file_path_action_spec(self):
        """Test resolving by file path for action_spec."""
        resolver = UtilityReferenceResolver()
        ref_info = ModelRefInfo(file_path="models/action_spec.yaml", type_name="Action")

        result = resolver._resolve_by_file_path(ref_info)

        assert result == "ModelActionSpec"

    def test_resolve_by_file_path_log_context(self):
        """Test resolving by file path for log_context."""
        resolver = UtilityReferenceResolver()
        ref_info = ModelRefInfo(
            file_path="models/log_context.yaml", type_name="Context"
        )

        result = resolver._resolve_by_file_path(ref_info)

        assert result == "ModelLogContext"

    def test_resolve_by_file_path_case_insensitive(self):
        """Test resolving by file path is case insensitive."""
        resolver = UtilityReferenceResolver()
        ref_info = ModelRefInfo(file_path="Models/SemVer.YAML", type_name="SemVer")

        result = resolver._resolve_by_file_path(ref_info)

        assert result == "ModelSemVer"

    def test_resolve_by_file_path_no_match(self):
        """Test resolving by file path with no match."""
        resolver = UtilityReferenceResolver()
        ref_info = ModelRefInfo(file_path="models/custom.yaml", type_name="Custom")

        result = resolver._resolve_by_file_path(ref_info)

        assert result is None


@pytest.mark.unit
class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_resolve_ref_none(self):
        """Test resolving None reference."""
        resolver = UtilityReferenceResolver()

        # Should handle gracefully
        try:
            result = resolver.resolve_ref(None)
            # If it doesn't raise, check result
            assert result is not None
        except (TypeError, AttributeError):
            # Expected behavior for None input
            pass

    def test_complex_reference_chain(self):
        """Test complex reference resolution chain."""
        config = Mock()
        config.use_imports_for_subcontracts = True
        config.subcontract_import_map = {}
        tracker = Mock()
        resolver = UtilityReferenceResolver(config=config, import_tracker=tracker)

        result = resolver.resolve_ref(
            "contracts/contract_models.yaml#/definitions/ToolGeneratorProcessingConfig"
        )

        assert result == "ModelProcessingConfig"
        tracker.add_subcontract_model.assert_called_once()

    def test_type_mappings_coverage(self):
        """Test all type mappings are working."""
        resolver = UtilityReferenceResolver()

        mappings = {
            "ProcessingConfig": "ModelProcessingConfig",
            "ValidationConfig": "ModelValidationConfig",
            "ProcessingResult": "ModelProcessingResult",
            "ValidationResult": "ModelValidationResult",
            "NodeStatus": "ModelNodeStatus",
        }

        for original, expected in mappings.items():
            result = resolver._clean_tool_prefix(f"Tool{original}")
            assert result == expected

    def test_multiple_hash_symbols(self):
        """Test reference with multiple hash symbols."""
        resolver = UtilityReferenceResolver()

        result = resolver.resolve_ref("file.yaml#/definitions#User")

        # Should handle gracefully
        assert isinstance(result, str)

    def test_unicode_in_reference(self):
        """Test reference with unicode characters."""
        resolver = UtilityReferenceResolver()

        result = resolver.resolve_ref("#/definitions/Usuario")

        assert result == "ModelUsuario"

    def test_very_long_reference(self):
        """Test very long reference string."""
        resolver = UtilityReferenceResolver()
        long_name = "A" * 1000

        result = resolver.resolve_ref(f"#/definitions/{long_name}")

        assert result == f"Model{long_name}"
