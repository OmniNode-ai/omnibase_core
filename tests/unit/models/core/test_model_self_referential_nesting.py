"""
Tests for self-referential model nesting.

These tests verify that models with self-referential fields can be instantiated
with nested data without causing RecursionError. This is a regression test for
the fix in PR #358 (OMN-1264).
"""

import pytest

from omnibase_core.enums.enum_yaml_value_type import EnumYamlValueType
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.core.model_action_category import ModelActionCategory
from omnibase_core.models.security.model_mask_data import ModelMaskData
from omnibase_core.models.utils.model_yaml_value import ModelYamlValue


@pytest.mark.unit
class TestSelfReferentialNesting:
    """Test self-referential model nesting to prevent RecursionError regression."""

    # -------------------------------------------------------------------------
    # ModelMaskData Tests
    # -------------------------------------------------------------------------

    def test_model_mask_data_single_level_nesting(self) -> None:
        """Test ModelMaskData with single level of nesting."""
        inner = ModelMaskData(string_data={"key": "value"})
        outer = ModelMaskData(nested_data={"child": inner})

        assert outer.nested_data["child"].string_data["key"] == "value"
        assert isinstance(outer.nested_data["child"], ModelMaskData)

    def test_model_mask_data_multi_level_nesting(self) -> None:
        """Test ModelMaskData with multiple levels of nesting."""
        level3 = ModelMaskData(string_data={"deep": "data"})
        level2 = ModelMaskData(
            nested_data={"level3": level3},
            integer_data={"count": 42},
        )
        level1 = ModelMaskData(
            nested_data={"level2": level2},
            boolean_data={"active": True},
        )

        # Verify deep access
        assert (
            level1.nested_data["level2"].nested_data["level3"].string_data["deep"]
            == "data"
        )
        assert level1.nested_data["level2"].integer_data["count"] == 42
        assert level1.boolean_data["active"] is True

    def test_model_mask_data_sibling_nesting(self) -> None:
        """Test ModelMaskData with multiple siblings at same level."""
        child1 = ModelMaskData(string_data={"name": "first"})
        child2 = ModelMaskData(string_data={"name": "second"})
        parent = ModelMaskData(nested_data={"child1": child1, "child2": child2})

        assert parent.nested_data["child1"].string_data["name"] == "first"
        assert parent.nested_data["child2"].string_data["name"] == "second"
        assert len(parent.nested_data) == 2

    def test_model_mask_data_to_dict_with_nesting(self) -> None:
        """Test ModelMaskData.to_dict() with nested data."""
        inner = ModelMaskData(string_data={"inner_key": "inner_value"})
        outer = ModelMaskData(
            string_data={"outer_key": "outer_value"},
            nested_data={"child": inner},
        )

        result = outer.to_dict()
        assert result["outer_key"] == "outer_value"
        assert isinstance(result["child"], dict)
        assert result["child"]["inner_key"] == "inner_value"

    def test_model_mask_data_from_dict_with_nesting(self) -> None:
        """Test ModelMaskData.from_dict() with nested dictionaries."""
        data = {
            "name": "parent",
            "nested": {
                "name": "child",
                "count": 10,
            },
        }

        result = ModelMaskData.from_dict(data)
        assert result.string_data["name"] == "parent"
        assert result.nested_data["nested"].string_data["name"] == "child"
        assert result.nested_data["nested"].integer_data["count"] == 10

    # -------------------------------------------------------------------------
    # ModelYamlValue Tests
    # -------------------------------------------------------------------------

    def test_model_yaml_value_dict_nesting(self) -> None:
        """Test ModelYamlValue with nested dict_value."""
        inner_value = ModelYamlValue(
            value_type=EnumYamlValueType.SCHEMA_VALUE,
            schema_value=ModelSchemaValue.from_value("nested_string"),
        )
        outer_value = ModelYamlValue(
            value_type=EnumYamlValueType.DICT,
            dict_value={"inner": inner_value},
        )

        assert outer_value.dict_value is not None
        assert "inner" in outer_value.dict_value
        assert (
            outer_value.dict_value["inner"].value_type == EnumYamlValueType.SCHEMA_VALUE
        )

    def test_model_yaml_value_list_nesting(self) -> None:
        """Test ModelYamlValue with nested list_value."""
        item1 = ModelYamlValue(
            value_type=EnumYamlValueType.SCHEMA_VALUE,
            schema_value=ModelSchemaValue.from_value("item1"),
        )
        item2 = ModelYamlValue(
            value_type=EnumYamlValueType.SCHEMA_VALUE,
            schema_value=ModelSchemaValue.from_value("item2"),
        )
        list_value = ModelYamlValue(
            value_type=EnumYamlValueType.LIST,
            list_value=[item1, item2],
        )

        assert list_value.list_value is not None
        assert len(list_value.list_value) == 2
        assert list_value.list_value[0].value_type == EnumYamlValueType.SCHEMA_VALUE
        assert list_value.list_value[1].value_type == EnumYamlValueType.SCHEMA_VALUE

    def test_model_yaml_value_deeply_nested(self) -> None:
        """Test ModelYamlValue with deeply nested structure."""
        # Create a deep structure: dict -> list -> dict -> schema_value
        schema_val = ModelYamlValue(
            value_type=EnumYamlValueType.SCHEMA_VALUE,
            schema_value=ModelSchemaValue.from_value("deep_value"),
        )
        inner_dict = ModelYamlValue(
            value_type=EnumYamlValueType.DICT,
            dict_value={"data": schema_val},
        )
        list_container = ModelYamlValue(
            value_type=EnumYamlValueType.LIST,
            list_value=[inner_dict],
        )
        outer_dict = ModelYamlValue(
            value_type=EnumYamlValueType.DICT,
            dict_value={"items": list_container},
        )

        # Verify deep access
        assert outer_dict.dict_value is not None
        items = outer_dict.dict_value["items"]
        assert items.list_value is not None
        inner = items.list_value[0]
        assert inner.dict_value is not None
        data = inner.dict_value["data"]
        assert data.value_type == EnumYamlValueType.SCHEMA_VALUE

    def test_model_yaml_value_to_serializable_nested(self) -> None:
        """Test ModelYamlValue.to_serializable() with nested values."""
        inner = ModelYamlValue(
            value_type=EnumYamlValueType.SCHEMA_VALUE,
            schema_value=ModelSchemaValue.from_value("inner"),
        )
        outer = ModelYamlValue(
            value_type=EnumYamlValueType.DICT,
            dict_value={"nested": inner},
        )

        result = outer.to_serializable()
        assert isinstance(result, dict)

    def test_model_yaml_value_from_dict_data(self) -> None:
        """Test ModelYamlValue.from_dict_data() creates nested structure."""
        data = {
            "key1": ModelSchemaValue.from_value("value1"),
            "key2": ModelSchemaValue.from_value(42),
        }
        result = ModelYamlValue.from_dict_data(data)

        assert result.value_type == EnumYamlValueType.DICT
        assert result.dict_value is not None
        assert len(result.dict_value) == 2
        assert result.dict_value["key1"].value_type == EnumYamlValueType.SCHEMA_VALUE

    def test_model_yaml_value_from_list(self) -> None:
        """Test ModelYamlValue.from_list() creates nested structure."""
        items = [
            ModelSchemaValue.from_value("a"),
            ModelSchemaValue.from_value("b"),
            ModelSchemaValue.from_value("c"),
        ]
        result = ModelYamlValue.from_list(items)

        assert result.value_type == EnumYamlValueType.LIST
        assert result.list_value is not None
        assert len(result.list_value) == 3

    # -------------------------------------------------------------------------
    # ModelActionCategory Tests
    # -------------------------------------------------------------------------

    def test_model_action_category_registry_multiple(self) -> None:
        """Test ModelActionCategory registry with multiple categories."""
        # Create test categories with unique names to avoid collision
        cat1 = ModelActionCategory(
            name="test_compute_ops",
            display_name="Compute Operations",
            description="Computational operations category",
        )
        cat2 = ModelActionCategory(
            name="test_io_ops",
            display_name="I/O Operations",
            description="Input/output operations category",
        )
        cat3 = ModelActionCategory(
            name="test_transform_ops",
            display_name="Transform Operations",
            description="Data transformation category",
        )

        # Register categories
        ModelActionCategory.register(cat1)
        ModelActionCategory.register(cat2)
        ModelActionCategory.register(cat3)

        # Verify retrieval
        retrieved1 = ModelActionCategory.get_by_name("test_compute_ops")
        assert retrieved1.display_name == "Compute Operations"

        retrieved2 = ModelActionCategory.get_by_name("test_io_ops")
        assert retrieved2.display_name == "I/O Operations"

        retrieved3 = ModelActionCategory.get_by_name("test_transform_ops")
        assert retrieved3.display_name == "Transform Operations"

        # Verify all are in registry
        all_registered = ModelActionCategory.get_all_registered()
        names = [cat.name for cat in all_registered]
        assert "test_compute_ops" in names
        assert "test_io_ops" in names
        assert "test_transform_ops" in names

    def test_model_action_category_equality(self) -> None:
        """Test ModelActionCategory equality with registry values."""
        cat = ModelActionCategory(
            name="test_equality_cat",
            display_name="Equality Test",
            description="Testing equality",
        )
        ModelActionCategory.register(cat)

        retrieved = ModelActionCategory.get_by_name("test_equality_cat")
        assert retrieved == cat
        assert retrieved == "test_equality_cat"  # String comparison

    def test_model_action_category_hash(self) -> None:
        """Test ModelActionCategory can be used in sets and as dict keys."""
        cat1 = ModelActionCategory(
            name="test_hashable1",
            display_name="Hashable 1",
            description="Testing hash 1",
        )
        cat2 = ModelActionCategory(
            name="test_hashable2",
            display_name="Hashable 2",
            description="Testing hash 2",
        )

        # Test in set
        category_set = {cat1, cat2}
        assert len(category_set) == 2

        # Test as dict key
        category_dict = {cat1: "first", cat2: "second"}
        assert category_dict[cat1] == "first"
        assert category_dict[cat2] == "second"

    # -------------------------------------------------------------------------
    # No RecursionError Validation
    # -------------------------------------------------------------------------

    def test_no_recursion_error_on_model_mask_data_instantiation(self) -> None:
        """Verify no RecursionError when instantiating ModelMaskData with nesting."""
        # This should not raise RecursionError
        try:
            inner = ModelMaskData(string_data={"test": "value"})
            outer = ModelMaskData(nested_data={"nested": inner})
            _ = outer.model_dump()
        except RecursionError:
            pytest.fail("RecursionError raised during ModelMaskData instantiation")

    def test_no_recursion_error_on_model_yaml_value_instantiation(self) -> None:
        """Verify no RecursionError when instantiating ModelYamlValue with nesting."""
        # This should not raise RecursionError
        try:
            inner = ModelYamlValue(
                value_type=EnumYamlValueType.SCHEMA_VALUE,
                schema_value=ModelSchemaValue.from_value("test"),
            )
            outer = ModelYamlValue(
                value_type=EnumYamlValueType.DICT,
                dict_value={"inner": inner},
            )
            _ = outer.model_dump()
        except RecursionError:
            pytest.fail("RecursionError raised during ModelYamlValue instantiation")

    def test_no_recursion_error_on_model_action_category_instantiation(self) -> None:
        """Verify no RecursionError when instantiating ModelActionCategory."""
        # This should not raise RecursionError
        try:
            cat = ModelActionCategory(
                name="test_no_recursion",
                display_name="No Recursion Test",
                description="Testing for no recursion error",
            )
            _ = cat.model_dump()
        except RecursionError:
            pytest.fail(
                "RecursionError raised during ModelActionCategory instantiation"
            )
