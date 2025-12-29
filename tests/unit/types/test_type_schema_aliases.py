"""
Unit tests for type_schema_aliases module.

Tests the type aliases defined in omnibase_core.types.type_schema_aliases to verify:
1. All type aliases are importable
2. Type aliases can be used in type annotations
3. No circular import issues exist
4. TYPE_CHECKING guard works correctly at runtime
5. The documented import chain does not create cycles

The file under test uses TYPE_CHECKING guard to avoid circular imports:
    Import Chain to Avoid:
    types.__init__ -> type_schema_aliases -> models.common -> ... -> types.__init__
"""

from typing import get_args, get_origin

import pytest


@pytest.mark.unit
class TestTypeSchemaAliasesImport:
    """Tests for importing type_schema_aliases module."""

    def test_import_schema_dict(self) -> None:
        """Test that SchemaDict can be imported."""
        from omnibase_core.types.type_schema_aliases import SchemaDict

        assert SchemaDict is not None

    def test_import_step_outputs(self) -> None:
        """Test that StepOutputs can be imported."""
        from omnibase_core.types.type_schema_aliases import StepOutputs

        assert StepOutputs is not None

    def test_import_from_types_package(self) -> None:
        """Test that type aliases can be imported from types package."""
        from omnibase_core.types import SchemaDict, StepOutputs

        assert SchemaDict is not None
        assert StepOutputs is not None


@pytest.mark.unit
class TestCircularImportPrevention:
    """Tests verifying no circular import issues exist."""

    def test_import_order_types_first(self) -> None:
        """Verify importing types before models doesn't cause circular dependency."""
        # Order 1: Import types first
        from omnibase_core.models.common import ModelSchemaValue
        from omnibase_core.types import SchemaDict, StepOutputs

        # If we get here without ImportError, the circular import is avoided
        assert SchemaDict is not None
        assert StepOutputs is not None
        assert ModelSchemaValue is not None

    def test_import_order_models_first(self) -> None:
        """Verify importing models before types doesn't cause circular dependency."""
        # Order 2: Import models first
        from omnibase_core.models.common import ModelSchemaValue
        from omnibase_core.types import SchemaDict, StepOutputs

        # If we get here without ImportError, the circular import is avoided
        assert ModelSchemaValue is not None
        assert SchemaDict is not None
        assert StepOutputs is not None

    def test_import_chain_types_init(self) -> None:
        """Test importing types.__init__ doesn't cause circular dependency."""
        import omnibase_core.types

        assert hasattr(omnibase_core.types, "SchemaDict")
        assert hasattr(omnibase_core.types, "StepOutputs")

    def test_import_chain_type_schema_aliases_direct(self) -> None:
        """Test importing type_schema_aliases module directly."""
        import omnibase_core.types.type_schema_aliases

        assert hasattr(omnibase_core.types.type_schema_aliases, "SchemaDict")
        assert hasattr(omnibase_core.types.type_schema_aliases, "StepOutputs")

    def test_import_chain_models_common(self) -> None:
        """Test importing models.common doesn't cause circular dependency."""
        import omnibase_core.models.common

        assert hasattr(omnibase_core.models.common, "ModelSchemaValue")

    def test_full_import_chain_sequence(self) -> None:
        """Test the full import chain sequence doesn't create cycles.

        This tests the documented import chain:
        types.__init__ -> type_schema_aliases -> models.common -> ... -> types.__init__
        """
        # Step 1: Import types.__init__
        # Step 3: Import models.common
        import omnibase_core.models.common
        import omnibase_core.types

        # Step 2: Import type_schema_aliases
        import omnibase_core.types.type_schema_aliases

        # Step 4: Verify all imports succeeded without circular import errors
        assert omnibase_core.types is not None
        assert omnibase_core.types.type_schema_aliases is not None
        assert omnibase_core.models.common is not None

        # Verify we can use the types
        from omnibase_core.models.common import ModelSchemaValue
        from omnibase_core.types import SchemaDict, StepOutputs

        assert SchemaDict is not None
        assert StepOutputs is not None
        assert ModelSchemaValue is not None


def _get_type_alias_value(type_alias: object) -> object:
    """Get the underlying type from a Python 3.12+ TypeAliasType.

    Python 3.12 introduced the `type` statement which creates TypeAliasType objects.
    To introspect these, we need to access the __value__ attribute.
    """
    if hasattr(type_alias, "__value__"):
        return type_alias.__value__
    return type_alias


@pytest.mark.unit
class TestTypeCheckingGuard:
    """Tests for TYPE_CHECKING guard behavior."""

    def test_type_checking_guard_prevents_runtime_import(self) -> None:
        """Verify TYPE_CHECKING guard works correctly.

        The module should NOT have ModelSchemaValue imported at runtime
        because it's only imported under TYPE_CHECKING.
        """
        import omnibase_core.types.type_schema_aliases as module

        # The module should NOT have ModelSchemaValue as a direct attribute
        # because it's only imported under TYPE_CHECKING (which is False at runtime)
        assert not hasattr(module, "ModelSchemaValue")

    def test_module_does_not_expose_model_schema_value(self) -> None:
        """Verify ModelSchemaValue is not in module's __all__."""
        from omnibase_core.types.type_schema_aliases import __all__

        assert "ModelSchemaValue" not in __all__
        assert "SchemaDict" in __all__
        assert "StepOutputs" in __all__

    def test_type_aliases_use_forward_references(self) -> None:
        """Verify type aliases use string forward references.

        The type aliases should use string forward references like
        'ModelSchemaValue' instead of direct class references.
        """
        import omnibase_core.types.type_schema_aliases as module

        # Get the SchemaDict type alias (Python 3.12+ type statement)
        schema_dict_type = module.SchemaDict

        # For Python 3.12+ TypeAliasType, access __value__ to get underlying type
        underlying_type = _get_type_alias_value(schema_dict_type)

        # The underlying type should be a dict type
        origin = get_origin(underlying_type)
        assert origin is dict

        # Get the value type from the dict type alias
        args = get_args(underlying_type)
        assert len(args) == 2
        assert args[0] is str  # Key type is str

        # Value type should be a forward reference (string)
        # In Python 3.12+ type aliases with forward refs, the value is a string
        value_type = args[1]
        # The value type should reference ModelSchemaValue as a string (forward ref)
        # This confirms it's NOT the actual class (which would indicate runtime import)
        assert value_type == "ModelSchemaValue"


@pytest.mark.unit
class TestSchemaDict:
    """Tests for SchemaDict type alias."""

    def test_schema_dict_is_dict_type(self) -> None:
        """Test that SchemaDict is a dict type alias."""
        from omnibase_core.types import SchemaDict

        # For Python 3.12+ TypeAliasType, access __value__ to get underlying type
        underlying = _get_type_alias_value(SchemaDict)
        origin = get_origin(underlying)
        assert origin is dict

    def test_schema_dict_has_correct_key_type(self) -> None:
        """Test that SchemaDict has str keys."""
        from omnibase_core.types import SchemaDict

        # For Python 3.12+ TypeAliasType, access __value__ to get underlying type
        underlying = _get_type_alias_value(SchemaDict)
        args = get_args(underlying)
        assert len(args) >= 1
        assert args[0] is str

    def test_schema_dict_value_type_references_model_schema_value(self) -> None:
        """Test that SchemaDict value type references ModelSchemaValue."""
        from omnibase_core.types import SchemaDict

        # For Python 3.12+ TypeAliasType, access __value__ to get underlying type
        underlying = _get_type_alias_value(SchemaDict)
        args = get_args(underlying)
        assert len(args) == 2
        # The value type should be a forward reference to ModelSchemaValue
        value_type = args[1]
        assert value_type == "ModelSchemaValue"


@pytest.mark.unit
class TestStepOutputs:
    """Tests for StepOutputs type alias."""

    def test_step_outputs_is_dict_type(self) -> None:
        """Test that StepOutputs is a dict type alias."""
        from omnibase_core.types import StepOutputs

        # For Python 3.12+ TypeAliasType, access __value__ to get underlying type
        underlying = _get_type_alias_value(StepOutputs)
        origin = get_origin(underlying)
        assert origin is dict

    def test_step_outputs_has_correct_key_type(self) -> None:
        """Test that StepOutputs has str keys."""
        from omnibase_core.types import StepOutputs

        # For Python 3.12+ TypeAliasType, access __value__ to get underlying type
        underlying = _get_type_alias_value(StepOutputs)
        args = get_args(underlying)
        assert len(args) >= 1
        assert args[0] is str

    def test_step_outputs_value_is_nested_dict(self) -> None:
        """Test that StepOutputs value type is a nested dict."""
        from omnibase_core.types import StepOutputs

        # For Python 3.12+ TypeAliasType, access __value__ to get underlying type
        underlying = _get_type_alias_value(StepOutputs)
        args = get_args(underlying)
        assert len(args) == 2

        value_type = args[1]
        inner_origin = get_origin(value_type)
        assert inner_origin is dict


@pytest.mark.unit
class TestModuleStructure:
    """Tests for module structure and exports."""

    def test_module_has_all_attribute(self) -> None:
        """Test that module has __all__ defined."""
        import omnibase_core.types.type_schema_aliases as module

        assert hasattr(module, "__all__")

    def test_all_exports_correct_items(self) -> None:
        """Test that __all__ exports SchemaDict and StepOutputs."""
        from omnibase_core.types.type_schema_aliases import __all__

        assert set(__all__) == {"SchemaDict", "StepOutputs"}

    def test_module_docstring_exists(self) -> None:
        """Test that module has a docstring."""
        import omnibase_core.types.type_schema_aliases as module

        assert module.__doc__ is not None
        assert "schema" in module.__doc__.lower()

    def test_module_docstring_documents_import_chain(self) -> None:
        """Test that module docstring documents the import chain constraint."""
        import omnibase_core.types.type_schema_aliases as module

        assert module.__doc__ is not None
        assert "Import Chain" in module.__doc__


@pytest.mark.unit
class TestRuntimeUsage:
    """Tests for runtime usage of type aliases."""

    def test_schema_dict_annotation_works(self) -> None:
        """Test that SchemaDict can be used as a type annotation."""
        from omnibase_core.models.common import ModelSchemaValue
        from omnibase_core.types import SchemaDict

        # Create a dictionary that matches SchemaDict type
        metadata: SchemaDict = {
            "version": ModelSchemaValue.from_value("1.0.0"),
            "count": ModelSchemaValue.from_value(42),
        }

        assert isinstance(metadata, dict)
        assert "version" in metadata
        assert "count" in metadata

    def test_step_outputs_annotation_works(self) -> None:
        """Test that StepOutputs can be used as a type annotation."""
        from omnibase_core.models.common import ModelSchemaValue
        from omnibase_core.types import StepOutputs

        # Create a dictionary that matches StepOutputs type
        outputs: StepOutputs = {
            "step_1": {"result": ModelSchemaValue.from_value("success")},
            "step_2": {"count": ModelSchemaValue.from_value(10)},
        }

        assert isinstance(outputs, dict)
        assert "step_1" in outputs
        assert "step_2" in outputs
        assert isinstance(outputs["step_1"], dict)


@pytest.mark.unit
class TestSchemaDictUsagePatterns:
    """Tests for SchemaDict usage patterns with ModelSchemaValue factory methods."""

    def test_type_annotation_with_string_value(self) -> None:
        """Test using SchemaDict with string ModelSchemaValue."""
        from omnibase_core.models.common import ModelSchemaValue
        from omnibase_core.types import SchemaDict

        schema: SchemaDict = {
            "name": ModelSchemaValue.create_string("my_node"),
        }
        assert "name" in schema
        assert schema["name"].is_string()
        assert schema["name"].get_string() == "my_node"

    def test_type_annotation_with_number_value(self) -> None:
        """Test using SchemaDict with number ModelSchemaValue."""
        from omnibase_core.models.common import ModelSchemaValue
        from omnibase_core.types import SchemaDict

        schema: SchemaDict = {
            "count": ModelSchemaValue.create_number(42),
        }
        assert "count" in schema
        assert schema["count"].is_number()
        assert schema["count"].to_value() == 42

    def test_type_annotation_with_boolean_value(self) -> None:
        """Test using SchemaDict with boolean ModelSchemaValue."""
        from omnibase_core.models.common import ModelSchemaValue
        from omnibase_core.types import SchemaDict

        schema: SchemaDict = {
            "enabled": ModelSchemaValue.create_boolean(True),
        }
        assert "enabled" in schema
        assert schema["enabled"].is_boolean()
        assert schema["enabled"].get_boolean() is True

    def test_type_annotation_with_null_value(self) -> None:
        """Test using SchemaDict with null ModelSchemaValue."""
        from omnibase_core.models.common import ModelSchemaValue
        from omnibase_core.types import SchemaDict

        schema: SchemaDict = {
            "nothing": ModelSchemaValue.create_null(),
        }
        assert "nothing" in schema
        assert schema["nothing"].is_null()
        assert schema["nothing"].to_value() is None

    def test_type_annotation_with_array_value(self) -> None:
        """Test using SchemaDict with array ModelSchemaValue."""
        from omnibase_core.models.common import ModelSchemaValue
        from omnibase_core.types import SchemaDict

        schema: SchemaDict = {
            "items": ModelSchemaValue.create_array(["a", "b", "c"]),
        }
        assert "items" in schema
        assert schema["items"].is_array()
        assert schema["items"].to_value() == ["a", "b", "c"]

    def test_type_annotation_with_object_value(self) -> None:
        """Test using SchemaDict with object ModelSchemaValue."""
        from omnibase_core.models.common import ModelSchemaValue
        from omnibase_core.types import SchemaDict

        schema: SchemaDict = {
            "data": ModelSchemaValue.create_object({"key": "value"}),
        }
        assert "data" in schema
        assert schema["data"].is_object()
        assert schema["data"].to_value() == {"key": "value"}

    def test_type_annotation_with_multiple_values(self) -> None:
        """Test using SchemaDict with multiple mixed values."""
        from omnibase_core.models.common import ModelSchemaValue
        from omnibase_core.types import SchemaDict

        schema: SchemaDict = {
            "name": ModelSchemaValue.create_string("my_node"),
            "version": ModelSchemaValue.create_string("1.0.0"),
            "count": ModelSchemaValue.create_number(42),
            "enabled": ModelSchemaValue.create_boolean(True),
            "config": ModelSchemaValue.create_object({"debug": False}),
        }
        assert len(schema) == 5
        assert schema["name"].get_string() == "my_node"
        assert schema["version"].get_string() == "1.0.0"
        assert schema["count"].to_value() == 42
        assert schema["enabled"].get_boolean() is True
        assert schema["config"].to_value() == {"debug": False}

    def test_docstring_example_metadata(self) -> None:
        """Test docstring example: metadata usage."""
        from omnibase_core.models.common import ModelSchemaValue
        from omnibase_core.types import SchemaDict

        metadata: SchemaDict = {
            "version": ModelSchemaValue.create_string("1.0.0"),
            "count": ModelSchemaValue.create_number(42),
        }
        assert metadata["version"].get_string() == "1.0.0"
        assert metadata["count"].to_value() == 42

    def test_edge_case_empty_dict(self) -> None:
        """Test SchemaDict with empty dict value."""
        from omnibase_core.types import SchemaDict

        value: SchemaDict = {}
        assert value == {}
        assert isinstance(value, dict)

    def test_edge_case_numeric_zero(self) -> None:
        """Test SchemaDict with zero value."""
        from omnibase_core.models.common import ModelSchemaValue
        from omnibase_core.types import SchemaDict

        schema: SchemaDict = {
            "zero": ModelSchemaValue.create_number(0),
        }
        assert schema["zero"].to_value() == 0

    def test_edge_case_negative_number(self) -> None:
        """Test SchemaDict with negative number."""
        from omnibase_core.models.common import ModelSchemaValue
        from omnibase_core.types import SchemaDict

        schema: SchemaDict = {
            "negative": ModelSchemaValue.create_number(-42),
        }
        assert schema["negative"].to_value() == -42

    def test_edge_case_float_value(self) -> None:
        """Test SchemaDict with float value."""
        from omnibase_core.models.common import ModelSchemaValue
        from omnibase_core.types import SchemaDict

        schema: SchemaDict = {
            "pi": ModelSchemaValue.create_number(3.14159),
        }
        assert schema["pi"].to_value() == pytest.approx(3.14159)

    def test_edge_case_boolean_false(self) -> None:
        """Test SchemaDict with False boolean."""
        from omnibase_core.models.common import ModelSchemaValue
        from omnibase_core.types import SchemaDict

        schema: SchemaDict = {
            "disabled": ModelSchemaValue.create_boolean(False),
        }
        assert schema["disabled"].get_boolean() is False

    def test_edge_case_empty_array(self) -> None:
        """Test SchemaDict with empty array."""
        from omnibase_core.models.common import ModelSchemaValue
        from omnibase_core.types import SchemaDict

        schema: SchemaDict = {
            "empty_list": ModelSchemaValue.create_array([]),
        }
        assert schema["empty_list"].to_value() == []

    def test_edge_case_empty_object(self) -> None:
        """Test SchemaDict with empty object."""
        from omnibase_core.models.common import ModelSchemaValue
        from omnibase_core.types import SchemaDict

        schema: SchemaDict = {
            "empty_obj": ModelSchemaValue.create_object({}),
        }
        assert schema["empty_obj"].to_value() == {}

    def test_use_case_configuration_parameters(self) -> None:
        """Test SchemaDict for configuration parameters use case."""
        from omnibase_core.models.common import ModelSchemaValue
        from omnibase_core.types import SchemaDict

        config: SchemaDict = {
            "host": ModelSchemaValue.create_string("localhost"),
            "port": ModelSchemaValue.create_number(8080),
            "ssl": ModelSchemaValue.create_boolean(True),
            "timeout_ms": ModelSchemaValue.create_number(5000),
        }
        assert len(config) == 4
        assert config["host"].get_string() == "localhost"
        assert config["port"].to_value() == 8080
        assert config["ssl"].get_boolean() is True


@pytest.mark.unit
class TestStepOutputsUsagePatterns:
    """Tests for StepOutputs usage patterns with ModelSchemaValue factory methods."""

    def test_type_annotation_with_single_step(self) -> None:
        """Test using StepOutputs with single step output."""
        from omnibase_core.models.common import ModelSchemaValue
        from omnibase_core.types import StepOutputs

        outputs: StepOutputs = {
            "step_1": {"result": ModelSchemaValue.create_string("success")},
        }
        assert "step_1" in outputs
        assert outputs["step_1"]["result"].get_string() == "success"

    def test_type_annotation_with_multiple_steps(self) -> None:
        """Test using StepOutputs with multiple step outputs."""
        from omnibase_core.models.common import ModelSchemaValue
        from omnibase_core.types import StepOutputs

        outputs: StepOutputs = {
            "step_1": {"result": ModelSchemaValue.create_string("success")},
            "step_2": {"count": ModelSchemaValue.create_number(10)},
            "step_3": {"complete": ModelSchemaValue.create_boolean(True)},
        }
        assert len(outputs) == 3
        assert outputs["step_1"]["result"].get_string() == "success"
        assert outputs["step_2"]["count"].to_value() == 10
        assert outputs["step_3"]["complete"].get_boolean() is True

    def test_type_annotation_with_step_multiple_outputs(self) -> None:
        """Test using StepOutputs with multiple outputs per step."""
        from omnibase_core.models.common import ModelSchemaValue
        from omnibase_core.types import StepOutputs

        outputs: StepOutputs = {
            "extract": {
                "data": ModelSchemaValue.create_object({"key": "value"}),
                "count": ModelSchemaValue.create_number(100),
                "status": ModelSchemaValue.create_string("complete"),
            },
        }
        assert "extract" in outputs
        assert len(outputs["extract"]) == 3
        assert outputs["extract"]["count"].to_value() == 100
        assert outputs["extract"]["status"].get_string() == "complete"

    def test_docstring_example_step_outputs(self) -> None:
        """Test docstring example: StepOutputs usage."""
        from omnibase_core.models.common import ModelSchemaValue
        from omnibase_core.types import StepOutputs

        outputs: StepOutputs = {
            "step_1": {"result": ModelSchemaValue.create_string("success")},
            "step_2": {"count": ModelSchemaValue.create_number(10)},
        }
        assert outputs["step_1"]["result"].get_string() == "success"
        assert outputs["step_2"]["count"].to_value() == 10

    def test_docstring_example_extract_transform(self) -> None:
        """Test docstring example: extract-transform pattern."""
        from omnibase_core.models.common import ModelSchemaValue
        from omnibase_core.types import StepOutputs

        step_outputs: StepOutputs = {
            "extract": {
                "data": ModelSchemaValue.create_object({"key": "value"}),
                "count": ModelSchemaValue.create_number(100),
            },
            "transform": {
                "result": ModelSchemaValue.create_array(["a", "b", "c"]),
            },
        }
        assert step_outputs["extract"]["data"].to_value() == {"key": "value"}
        assert step_outputs["extract"]["count"].to_value() == 100
        assert step_outputs["transform"]["result"].to_value() == ["a", "b", "c"]

    def test_edge_case_empty_step_dict(self) -> None:
        """Test StepOutputs with step containing empty dict."""
        from omnibase_core.types import StepOutputs

        outputs: StepOutputs = {
            "empty_step": {},
        }
        assert "empty_step" in outputs
        assert len(outputs["empty_step"]) == 0

    def test_edge_case_uuid_step_name(self) -> None:
        """Test StepOutputs with UUID-like step name."""
        from omnibase_core.models.common import ModelSchemaValue
        from omnibase_core.types import StepOutputs

        outputs: StepOutputs = {
            "550e8400-e29b-41d4-a716-446655440000": {
                "result": ModelSchemaValue.create_string("done")
            },
        }
        assert "550e8400-e29b-41d4-a716-446655440000" in outputs

    def test_use_case_orchestrator_workflow(self) -> None:
        """Test StepOutputs for orchestrator workflow tracking use case."""
        from omnibase_core.models.common import ModelSchemaValue
        from omnibase_core.types import StepOutputs

        workflow_outputs: StepOutputs = {
            "init": {
                "started_at": ModelSchemaValue.create_string("2024-01-01T00:00:00Z"),
                "config": ModelSchemaValue.create_object({"debug": True}),
            },
            "process": {
                "items_processed": ModelSchemaValue.create_number(500),
                "errors": ModelSchemaValue.create_number(0),
            },
            "finalize": {
                "success": ModelSchemaValue.create_boolean(True),
                "output_path": ModelSchemaValue.create_string("/tmp/output.json"),
            },
        }
        assert len(workflow_outputs) == 3
        assert workflow_outputs["init"]["config"].to_value() == {"debug": True}
        assert workflow_outputs["process"]["items_processed"].to_value() == 500
        assert workflow_outputs["finalize"]["success"].get_boolean() is True


@pytest.mark.unit
class TestUsageInFunctionSignatures:
    """Tests for using type aliases in function signatures."""

    def test_function_with_schema_dict_param(self) -> None:
        """Test function that accepts SchemaDict parameter."""
        from omnibase_core.models.common import ModelSchemaValue
        from omnibase_core.types import SchemaDict

        def process_schema(schema: SchemaDict) -> int:
            return len(schema)

        test_schema: SchemaDict = {
            "a": ModelSchemaValue.create_string("A"),
            "b": ModelSchemaValue.create_number(2),
        }
        assert process_schema(test_schema) == 2

    def test_function_with_schema_dict_return(self) -> None:
        """Test function that returns SchemaDict."""
        from omnibase_core.models.common import ModelSchemaValue
        from omnibase_core.types import SchemaDict

        def create_schema() -> SchemaDict:
            return {
                "name": ModelSchemaValue.create_string("test"),
                "version": ModelSchemaValue.create_number(1),
            }

        result = create_schema()
        assert isinstance(result, dict)
        assert result["name"].get_string() == "test"

    def test_function_with_step_outputs_param(self) -> None:
        """Test function that accepts StepOutputs parameter."""
        from omnibase_core.models.common import ModelSchemaValue
        from omnibase_core.types import StepOutputs

        def count_steps(outputs: StepOutputs) -> int:
            return len(outputs)

        test_outputs: StepOutputs = {
            "step1": {"r": ModelSchemaValue.create_string("done")},
            "step2": {"r": ModelSchemaValue.create_string("done")},
            "step3": {"r": ModelSchemaValue.create_string("done")},
        }
        assert count_steps(test_outputs) == 3

    def test_function_with_step_outputs_return(self) -> None:
        """Test function that returns StepOutputs."""
        from omnibase_core.models.common import ModelSchemaValue
        from omnibase_core.types import StepOutputs

        def create_workflow_outputs() -> StepOutputs:
            return {
                "init": {"ready": ModelSchemaValue.create_boolean(True)},
                "run": {"result": ModelSchemaValue.create_string("success")},
            }

        result = create_workflow_outputs()
        assert isinstance(result, dict)
        assert len(result) == 2

    def test_function_modifying_schema_dict(self) -> None:
        """Test function that modifies SchemaDict."""
        from omnibase_core.models.common import ModelSchemaValue
        from omnibase_core.types import SchemaDict

        def add_timestamp(schema: SchemaDict) -> SchemaDict:
            schema["timestamp"] = ModelSchemaValue.create_string("2024-01-01")
            return schema

        original: SchemaDict = {"data": ModelSchemaValue.create_string("test")}
        modified = add_timestamp(original)
        assert "timestamp" in modified
        assert modified["timestamp"].get_string() == "2024-01-01"

    def test_function_extracting_from_step_outputs(self) -> None:
        """Test function that extracts data from StepOutputs."""
        from omnibase_core.models.common import ModelSchemaValue
        from omnibase_core.types import StepOutputs

        def get_final_result(outputs: StepOutputs) -> object:
            if "final" in outputs and "result" in outputs["final"]:
                return outputs["final"]["result"].to_value()
            return None

        test_outputs: StepOutputs = {
            "init": {"status": ModelSchemaValue.create_string("started")},
            "process": {"count": ModelSchemaValue.create_number(100)},
            "final": {"result": ModelSchemaValue.create_object({"success": True})},
        }
        result = get_final_result(test_outputs)
        assert result == {"success": True}


@pytest.mark.unit
class TestTypeAliasRelationships:
    """Tests for relationships between type aliases."""

    def test_schema_dict_is_inner_type_of_step_outputs(self) -> None:
        """Test that SchemaDict is compatible with StepOutputs inner dict."""
        from omnibase_core.models.common import ModelSchemaValue
        from omnibase_core.types import SchemaDict, StepOutputs

        inner: SchemaDict = {
            "result": ModelSchemaValue.create_string("done"),
            "count": ModelSchemaValue.create_number(10),
        }

        outputs: StepOutputs = {
            "step_1": inner,
        }

        assert outputs["step_1"] == inner
        assert outputs["step_1"]["result"].get_string() == "done"

    def test_step_outputs_values_are_schema_dict_compatible(self) -> None:
        """Test that each StepOutputs value works as SchemaDict."""
        from omnibase_core.models.common import ModelSchemaValue
        from omnibase_core.types import SchemaDict, StepOutputs

        outputs: StepOutputs = {
            "step_1": {"a": ModelSchemaValue.create_string("A")},
            "step_2": {"b": ModelSchemaValue.create_number(2)},
        }

        step1_output: SchemaDict = outputs["step_1"]
        step2_output: SchemaDict = outputs["step_2"]

        assert step1_output["a"].get_string() == "A"
        assert step2_output["b"].to_value() == 2

    def test_build_step_outputs_from_schema_dicts(self) -> None:
        """Test building StepOutputs from multiple SchemaDict values."""
        from omnibase_core.models.common import ModelSchemaValue
        from omnibase_core.types import SchemaDict, StepOutputs

        schema1: SchemaDict = {
            "input": ModelSchemaValue.create_string("/path/to/file"),
        }
        schema2: SchemaDict = {
            "processed": ModelSchemaValue.create_boolean(True),
            "output_count": ModelSchemaValue.create_number(42),
        }
        schema3: SchemaDict = {
            "final_status": ModelSchemaValue.create_string("complete"),
        }

        workflow: StepOutputs = {
            "load": schema1,
            "process": schema2,
            "finalize": schema3,
        }

        assert len(workflow) == 3
        assert workflow["load"]["input"].get_string() == "/path/to/file"
        assert workflow["process"]["processed"].get_boolean() is True
        assert workflow["finalize"]["final_status"].get_string() == "complete"


@pytest.mark.unit
class TestIntegrationWithModelSchemaValue:
    """Integration tests with ModelSchemaValue factory methods."""

    def test_all_factory_methods_in_schema_dict(self) -> None:
        """Test all ModelSchemaValue factory methods in SchemaDict."""
        from omnibase_core.models.common import ModelSchemaValue
        from omnibase_core.types import SchemaDict

        schema: SchemaDict = {
            "string": ModelSchemaValue.create_string("hello"),
            "number": ModelSchemaValue.create_number(42),
            "boolean": ModelSchemaValue.create_boolean(True),
            "null": ModelSchemaValue.create_null(),
            "array": ModelSchemaValue.create_array([1, 2, 3]),
            "object": ModelSchemaValue.create_object({"key": "val"}),
        }
        assert schema["string"].get_string() == "hello"
        assert schema["number"].to_value() == 42
        assert schema["boolean"].get_boolean() is True
        assert schema["null"].is_null()
        assert schema["array"].to_value() == [1, 2, 3]
        assert schema["object"].to_value() == {"key": "val"}

    def test_all_factory_methods_in_step_outputs(self) -> None:
        """Test all ModelSchemaValue factory methods in StepOutputs."""
        from omnibase_core.models.common import ModelSchemaValue
        from omnibase_core.types import StepOutputs

        outputs: StepOutputs = {
            "step_string": {"value": ModelSchemaValue.create_string("hello")},
            "step_number": {"value": ModelSchemaValue.create_number(42)},
            "step_boolean": {"value": ModelSchemaValue.create_boolean(True)},
            "step_null": {"value": ModelSchemaValue.create_null()},
            "step_array": {"value": ModelSchemaValue.create_array([1, 2, 3])},
            "step_object": {"value": ModelSchemaValue.create_object({"key": "val"})},
        }
        assert outputs["step_string"]["value"].get_string() == "hello"
        assert outputs["step_number"]["value"].to_value() == 42
        assert outputs["step_boolean"]["value"].get_boolean() is True
        assert outputs["step_null"]["value"].is_null()
        assert outputs["step_array"]["value"].to_value() == [1, 2, 3]
        assert outputs["step_object"]["value"].to_value() == {"key": "val"}

    def test_from_value_factory_in_schema_dict(self) -> None:
        """Test using SchemaDict with ModelSchemaValue.from_value()."""
        from omnibase_core.models.common import ModelSchemaValue
        from omnibase_core.types import SchemaDict

        schema: SchemaDict = {
            "string": ModelSchemaValue.from_value("hello"),
            "number": ModelSchemaValue.from_value(123),
            "float": ModelSchemaValue.from_value(3.14),
            "boolean": ModelSchemaValue.from_value(False),
            "null": ModelSchemaValue.from_value(None),
            "array": ModelSchemaValue.from_value([1, 2, 3]),
            "object": ModelSchemaValue.from_value({"nested": "value"}),
        }
        assert schema["string"].to_value() == "hello"
        assert schema["number"].to_value() == 123
        assert schema["float"].to_value() == pytest.approx(3.14)
        assert schema["boolean"].to_value() is False
        assert schema["null"].to_value() is None
        assert schema["array"].to_value() == [1, 2, 3]
        assert schema["object"].to_value() == {"nested": "value"}

    def test_complex_workflow_pattern(self) -> None:
        """Test complex workflow pattern from docstring examples."""
        from omnibase_core.models.common import ModelSchemaValue
        from omnibase_core.types import SchemaDict, StepOutputs

        metadata: SchemaDict = {
            "version": ModelSchemaValue.create_string("1.0.0"),
            "count": ModelSchemaValue.create_number(42),
        }

        outputs: StepOutputs = {
            "step_1": {"result": ModelSchemaValue.create_string("success")},
            "step_2": {"count": ModelSchemaValue.create_number(10)},
        }

        assert metadata["version"].get_string() == "1.0.0"
        assert metadata["count"].to_value() == 42
        assert outputs["step_1"]["result"].get_string() == "success"
        assert outputs["step_2"]["count"].to_value() == 10

    def test_extract_transform_load_pattern(self) -> None:
        """Test ETL workflow pattern."""
        from omnibase_core.models.common import ModelSchemaValue
        from omnibase_core.types import StepOutputs

        step_outputs: StepOutputs = {
            "extract": {
                "data": ModelSchemaValue.create_object({"key": "value"}),
                "count": ModelSchemaValue.create_number(100),
            },
            "transform": {
                "result": ModelSchemaValue.create_array(["a", "b", "c"]),
            },
        }

        assert step_outputs["extract"]["count"].to_value() == 100
        result = step_outputs["transform"]["result"].to_value()
        assert isinstance(result, list)
        assert len(result) == 3
