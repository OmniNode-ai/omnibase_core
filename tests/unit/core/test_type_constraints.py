"""
Tests for type constraints and protocols.

Validates type guards, protocols, type variables, and runtime validation
functions for better generic programming patterns.
"""

import pytest
from pydantic import BaseModel

from omnibase_core.types.type_constraints import (
    BaseCollection,
    BaseFactory,
    Configurable,
    ContextValueType,
    Executable,
    Identifiable,
    Nameable,
    PrimitiveValueType,
    ProtocolMetadataProvider,
    ProtocolValidatable,
    Serializable,
    is_complex_context_value,
    is_configurable,
    is_context_value,
    is_executable,
    is_identifiable,
    is_metadata_provider,
    is_nameable,
    is_primitive_value,
    is_serializable,
    is_validatable,
    validate_context_value,
    validate_primitive_value,
)


@pytest.mark.unit
class TestSerializableProtocol:
    """Test Serializable protocol and type guard."""

    def test_is_serializable_with_valid_object(self):
        """Test is_serializable with object that has serialize method."""

        class ValidSerializable:
            def serialize(self) -> dict[str, object]:
                return {"key": "value"}

        obj = ValidSerializable()
        assert is_serializable(obj) is True

    def test_is_serializable_with_invalid_object(self):
        """Test is_serializable with object missing serialize method."""

        class NotSerializable:
            pass

        obj = NotSerializable()
        assert is_serializable(obj) is False

    def test_is_serializable_with_non_callable_attribute(self):
        """Test is_serializable with serialize as non-callable attribute."""

        class InvalidSerializable:
            serialize = "not_a_method"

        obj = InvalidSerializable()
        assert is_serializable(obj) is False


@pytest.mark.unit
class TestIdentifiableProtocol:
    """Test Identifiable protocol and type guard."""

    def test_is_identifiable_with_valid_object(self):
        """Test is_identifiable with object that has id property."""

        class ValidIdentifiable:
            @property
            def id(self) -> str:
                return "test_id"

        obj = ValidIdentifiable()
        assert is_identifiable(obj) is True

    def test_is_identifiable_with_id_attribute(self):
        """Test is_identifiable with id as regular attribute."""

        class SimpleIdentifiable:
            def __init__(self):
                self.id = "simple_id"

        obj = SimpleIdentifiable()
        assert is_identifiable(obj) is True

    def test_is_identifiable_with_invalid_object(self):
        """Test is_identifiable with object missing id."""

        class NotIdentifiable:
            pass

        obj = NotIdentifiable()
        assert is_identifiable(obj) is False


@pytest.mark.unit
class TestNameableProtocol:
    """Test Nameable protocol and type guard."""

    def test_is_nameable_with_valid_object(self):
        """Test is_nameable with object that has get_name and set_name."""

        class ValidNameable:
            def __init__(self):
                self._name = "test"

            def get_name(self) -> str:
                return self._name

            def set_name(self, name: str) -> None:
                self._name = name

        obj = ValidNameable()
        assert is_nameable(obj) is True

    def test_is_nameable_missing_get_name(self):
        """Test is_nameable with object missing get_name."""

        class PartialNameable:
            def set_name(self, name: str) -> None:
                pass

        obj = PartialNameable()
        assert is_nameable(obj) is False

    def test_is_nameable_missing_set_name(self):
        """Test is_nameable with object missing set_name."""

        class PartialNameable:
            def get_name(self) -> str:
                return "name"

        obj = PartialNameable()
        assert is_nameable(obj) is False

    def test_is_nameable_non_callable_methods(self):
        """Test is_nameable with non-callable attributes."""

        class InvalidNameable:
            get_name = "not_a_method"
            set_name = "not_a_method"

        obj = InvalidNameable()
        assert is_nameable(obj) is False


@pytest.mark.unit
class TestValidatableProtocol:
    """Test ProtocolValidatable protocol and type guard."""

    def test_is_validatable_with_valid_object(self):
        """Test is_validatable with object that has validate_instance."""

        class ValidValidatable:
            def validate_instance(self) -> bool:
                return True

        obj = ValidValidatable()
        assert is_validatable(obj) is True

    def test_is_validatable_with_invalid_object(self):
        """Test is_validatable with object missing validate_instance."""

        class NotValidatable:
            pass

        obj = NotValidatable()
        assert is_validatable(obj) is False

    def test_is_validatable_non_callable_attribute(self):
        """Test is_validatable with validate_instance as non-callable."""

        class InvalidValidatable:
            validate_instance = "not_a_method"

        obj = InvalidValidatable()
        assert is_validatable(obj) is False


@pytest.mark.unit
class TestConfigurableProtocol:
    """Test Configurable protocol and type guard."""

    def test_is_configurable_with_valid_object(self):
        """Test is_configurable with object that has configure method."""

        class ValidConfigurable:
            def configure(self, **kwargs: object) -> bool:
                return True

        obj = ValidConfigurable()
        assert is_configurable(obj) is True

    def test_is_configurable_with_invalid_object(self):
        """Test is_configurable with object missing configure."""

        class NotConfigurable:
            pass

        obj = NotConfigurable()
        assert is_configurable(obj) is False


@pytest.mark.unit
class TestExecutableProtocol:
    """Test Executable protocol and type guard."""

    def test_is_executable_with_valid_object(self):
        """Test is_executable with object that has execute method."""

        class ValidExecutable:
            def execute(self, *args: object, **kwargs: object) -> object:
                return "executed"

        obj = ValidExecutable()
        assert is_executable(obj) is True

    def test_is_executable_with_invalid_object(self):
        """Test is_executable with object missing execute."""

        class NotExecutable:
            pass

        obj = NotExecutable()
        assert is_executable(obj) is False


@pytest.mark.unit
class TestMetadataProviderProtocol:
    """Test ProtocolMetadataProvider protocol and type guard."""

    def test_is_metadata_provider_with_valid_object(self):
        """Test is_metadata_provider with object that has metadata property."""

        class ValidMetadataProvider:
            @property
            def metadata(self) -> dict[str, object]:
                return {"key": "value"}

        obj = ValidMetadataProvider()
        assert is_metadata_provider(obj) is True

    def test_is_metadata_provider_with_attribute(self):
        """Test is_metadata_provider with metadata as regular attribute."""

        class SimpleMetadataProvider:
            def __init__(self):
                self.metadata = {"key": "value"}

        obj = SimpleMetadataProvider()
        assert is_metadata_provider(obj) is True

    def test_is_metadata_provider_with_invalid_object(self):
        """Test is_metadata_provider with object missing metadata."""

        class NotMetadataProvider:
            pass

        obj = NotMetadataProvider()
        assert is_metadata_provider(obj) is False


@pytest.mark.unit
class TestPrimitiveValueValidation:
    """Test primitive value type guards and validation."""

    def test_is_primitive_value_with_string(self):
        """Test is_primitive_value with string."""
        assert is_primitive_value("test") is True

    def test_is_primitive_value_with_int(self):
        """Test is_primitive_value with integer."""
        assert is_primitive_value(42) is True

    def test_is_primitive_value_with_float(self):
        """Test is_primitive_value with float."""
        assert is_primitive_value(3.14) is True

    def test_is_primitive_value_with_bool(self):
        """Test is_primitive_value with boolean."""
        assert is_primitive_value(True) is True
        assert is_primitive_value(False) is True

    def test_is_primitive_value_with_invalid_types(self):
        """Test is_primitive_value with non-primitive types."""
        assert is_primitive_value([1, 2, 3]) is False
        assert is_primitive_value({"key": "value"}) is False
        assert is_primitive_value(None) is False
        assert is_primitive_value(object()) is False

    def test_validate_primitive_value_success(self):
        """Test validate_primitive_value with valid values."""
        assert validate_primitive_value("test") is True
        assert validate_primitive_value(42) is True
        assert validate_primitive_value(3.14) is True
        assert validate_primitive_value(True) is True

    def test_validate_primitive_value_failure(self):
        """Test validate_primitive_value with invalid values."""
        with pytest.raises(TypeError) as exc_info:
            validate_primitive_value([1, 2, 3])
        assert "Expected primitive value" in str(exc_info.value)
        assert "list" in str(exc_info.value)

    def test_validate_primitive_value_with_dict(self):
        """Test validate_primitive_value fails with dict."""
        with pytest.raises(TypeError) as exc_info:
            validate_primitive_value({"key": "value"})
        assert "Expected primitive value" in str(exc_info.value)

    def test_validate_primitive_value_with_none(self):
        """Test validate_primitive_value fails with None."""
        with pytest.raises(TypeError) as exc_info:
            validate_primitive_value(None)
        assert "Expected primitive value" in str(exc_info.value)


@pytest.mark.unit
class TestContextValueValidation:
    """Test context value type guards and validation."""

    def test_is_context_value_with_primitives(self):
        """Test is_context_value with primitive values."""
        assert is_context_value("test") is True
        assert is_context_value(42) is True
        assert is_context_value(3.14) is True
        assert is_context_value(True) is True

    def test_is_context_value_with_list(self):
        """Test is_context_value with list."""
        assert is_context_value([1, 2, 3]) is True
        assert is_context_value(["a", "b"]) is True
        assert is_context_value([]) is True

    def test_is_context_value_with_dict_string_keys(self):
        """Test is_context_value with dict having string keys."""
        assert is_context_value({"key": "value"}) is True
        assert is_context_value({"a": 1, "b": 2}) is True

    def test_is_context_value_with_dict_non_string_keys(self):
        """Test is_context_value with dict having non-string keys."""
        assert is_context_value({1: "value"}) is False
        assert is_context_value({("a", "b"): "value"}) is False

    def test_is_context_value_with_invalid_types(self):
        """Test is_context_value with invalid types."""
        assert is_context_value(None) is False
        assert is_context_value(object()) is False
        assert is_context_value({1, 2, 3}) is False

    def test_is_complex_context_value(self):
        """Test is_complex_context_value (same as is_context_value)."""
        assert is_complex_context_value("test") is True
        assert is_complex_context_value([1, 2, 3]) is True
        assert is_complex_context_value({"key": "value"}) is True
        assert is_complex_context_value(None) is False

    def test_validate_context_value_success(self):
        """Test validate_context_value with valid values."""
        assert validate_context_value("test") is True
        assert validate_context_value(42) is True
        assert validate_context_value([1, 2, 3]) is True
        assert validate_context_value({"key": "value"}) is True

    def test_validate_context_value_failure(self):
        """Test validate_context_value with invalid values."""
        with pytest.raises(TypeError) as exc_info:
            validate_context_value(None)
        assert "Expected context value" in str(exc_info.value)

    def test_validate_context_value_with_object(self):
        """Test validate_context_value fails with arbitrary object."""
        with pytest.raises(TypeError) as exc_info:
            validate_context_value(object())
        assert "Expected context value" in str(exc_info.value)

    def test_validate_context_value_with_set(self):
        """Test validate_context_value fails with set."""
        with pytest.raises(TypeError) as exc_info:
            validate_context_value({1, 2, 3})
        assert "Expected context value" in str(exc_info.value)


@pytest.mark.unit
class TestTypeVariablesAndProtocols:
    """Test that type variables and protocols are properly defined."""

    def test_base_collection_exists(self):
        """Test that BaseCollection is available."""
        assert BaseCollection is not None

    def test_base_factory_exists(self):
        """Test that BaseFactory is available."""
        assert BaseFactory is not None

    def test_protocols_exist(self):
        """Test that all protocols are properly defined."""
        assert Configurable is not None
        assert Executable is not None
        assert Identifiable is not None
        assert ProtocolMetadataProvider is not None
        assert Nameable is not None
        assert Serializable is not None
        assert ProtocolValidatable is not None

    def test_type_aliases_exist(self):
        """Test that type aliases are properly defined."""
        # These are type aliases, check they're not None
        assert PrimitiveValueType is not None
        assert ContextValueType is not None


@pytest.mark.unit
class TestProtocolIntegration:
    """Test protocols working with actual implementations."""

    def test_pydantic_model_with_metadata(self):
        """Test Pydantic model implementing metadata protocol."""

        class MetadataModel(BaseModel):
            @property
            def metadata(self) -> dict[str, object]:
                return {"model": "test"}

        model = MetadataModel()
        assert is_metadata_provider(model) is True

    def test_pydantic_model_with_id(self):
        """Test Pydantic model implementing identifiable protocol."""

        class IdentifiableModel(BaseModel):
            identifier: str = "test_id"  # Test fixture

            @property
            def id(self) -> str:
                """Provide id property for Identifiable protocol."""
                return self.identifier

        model = IdentifiableModel()
        assert is_identifiable(model) is True

    def test_combined_protocols(self):
        """Test object implementing multiple protocols."""

        class MultiProtocol:
            def __init__(self):
                self.id = "multi_id"
                self.metadata_value = {"key": "value"}

            @property
            def metadata(self) -> dict[str, object]:
                return self.metadata_value

            def serialize(self) -> dict[str, object]:
                return {"id": self.id, "metadata": self.metadata}

            def validate_instance(self) -> bool:
                return self.id is not None

        obj = MultiProtocol()
        assert is_identifiable(obj) is True
        assert is_metadata_provider(obj) is True
        assert is_serializable(obj) is True
        assert is_validatable(obj) is True


@pytest.mark.unit
class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_list_is_context_value(self):
        """Test empty list is valid context value."""
        assert is_context_value([]) is True

    def test_empty_dict_is_context_value(self):
        """Test empty dict is valid context value."""
        assert is_context_value({}) is True

    def test_zero_is_primitive_value(self):
        """Test zero is valid primitive value."""
        assert is_primitive_value(0) is True
        assert is_primitive_value(0.0) is True

    def test_empty_string_is_primitive_value(self):
        """Test empty string is valid primitive value."""
        assert is_primitive_value("") is True

    def test_nested_list_is_context_value(self):
        """Test nested list is valid context value."""
        assert is_context_value([1, [2, 3], [4, [5, 6]]]) is True

    def test_nested_dict_is_context_value(self):
        """Test nested dict with string keys is valid context value."""
        assert is_context_value({"outer": {"inner": "value"}}) is True

    def test_mixed_list_is_context_value(self):
        """Test list with mixed types is valid context value."""
        assert is_context_value([1, "two", 3.0, True, [5]]) is True


@pytest.mark.unit
class TestProtocolImplementationWithPydanticModels:
    """Test protocols implemented by Pydantic models."""

    def test_pydantic_model_implements_serializable(self):
        """Test Pydantic model with custom serialize method."""

        class SerializableModel(BaseModel):
            name: str = "test"
            value: int = 42

            def serialize(self) -> dict[str, object]:
                return {"name": self.name, "value": self.value, "extra": "data"}

        model = SerializableModel()
        assert is_serializable(model) is True
        result = model.serialize()
        assert result["name"] == "test"
        assert result["value"] == 42

    def test_pydantic_model_implements_validatable(self):
        """Test Pydantic model with custom validation."""

        class ValidatableModel(BaseModel):
            value: int = 10

            def validate_instance(self) -> bool:
                return self.value > 0

        model = ValidatableModel(value=5)
        assert is_validatable(model) is True
        assert model.validate_instance() is True

        invalid_model = ValidatableModel(value=-5)
        assert invalid_model.validate_instance() is False

    def test_pydantic_model_implements_configurable(self):
        """Test Pydantic model with configuration."""

        class ConfigurableModel(BaseModel):
            enabled: bool = False
            timeout: int = 30

            def configure(self, **kwargs: object) -> bool:
                for key, value in kwargs.items():
                    if hasattr(self, key):
                        setattr(self, key, value)
                return True

        model = ConfigurableModel()
        assert is_configurable(model) is True
        assert model.configure(enabled=True, timeout=60) is True
        assert model.enabled is True
        assert model.timeout == 60

    def test_pydantic_model_implements_executable(self):
        """Test Pydantic model with execute method."""

        class ExecutableModel(BaseModel):
            command: str = "test"

            def execute(self, *args: object, **kwargs: object) -> object:
                return f"Executed: {self.command}"

        model = ExecutableModel(command="run")
        assert is_executable(model) is True
        result = model.execute()
        assert result == "Executed: run"

    def test_pydantic_model_implements_nameable(self):
        """Test Pydantic model with name management."""

        class NameableModel(BaseModel):
            _internal_name: str = "default"

            def get_name(self) -> str:
                return self._internal_name

            def set_name(self, name: str) -> None:
                self._internal_name = name

        model = NameableModel()
        assert is_nameable(model) is True
        assert model.get_name() == "default"
        model.set_name("updated")
        assert model.get_name() == "updated"


@pytest.mark.unit
class TestProtocolWithInheritance:
    """Test protocol compliance with inheritance."""

    def test_inherited_protocol_implementation(self):
        """Test protocol implementation through inheritance."""

        class BaseClass:
            def serialize(self) -> dict[str, object]:
                return {"base": "data"}

        class DerivedClass(BaseClass):
            def __init__(self):
                self.extra = "value"

            def serialize(self) -> dict[str, object]:
                result = super().serialize()
                result["extra"] = self.extra
                return result

        obj = DerivedClass()
        assert is_serializable(obj) is True
        result = obj.serialize()
        assert "base" in result
        assert "extra" in result

    def test_multiple_protocol_inheritance(self):
        """Test object implementing multiple protocols through inheritance."""

        class IdentifiableBase:
            def __init__(self):
                self.id = "base_id"

        class SerializableBase:
            def serialize(self) -> dict[str, object]:
                return {}

        class CombinedClass(IdentifiableBase, SerializableBase):
            def serialize(self) -> dict[str, object]:
                return {"id": self.id}

        obj = CombinedClass()
        assert is_identifiable(obj) is True
        assert is_serializable(obj) is True

    def test_protocol_implementation_override(self):
        """Test overriding protocol methods in derived classes."""

        class BaseExecutable:
            def execute(self, *args: object, **kwargs: object) -> object:
                return "base"

        class DerivedExecutable(BaseExecutable):
            def execute(self, *args: object, **kwargs: object) -> object:
                return "derived"

        base = BaseExecutable()
        derived = DerivedExecutable()

        assert is_executable(base) is True
        assert is_executable(derived) is True
        assert base.execute() == "base"
        assert derived.execute() == "derived"


@pytest.mark.unit
class TestProtocolTypeGuardsEdgeCases:
    """Test edge cases for protocol type guards."""

    def test_serialize_attribute_is_none(self):
        """Test is_serializable when serialize attribute is None."""

        class InvalidSerializable:
            serialize = None

        obj = InvalidSerializable()
        assert is_serializable(obj) is False

    def test_configurable_with_non_callable_configure(self):
        """Test is_configurable when configure is not callable."""

        class InvalidConfigurable:
            configure = 42

        obj = InvalidConfigurable()
        assert is_configurable(obj) is False

    def test_executable_with_non_callable_execute(self):
        """Test is_executable when execute is not callable."""

        class InvalidExecutable:
            execute = "not_a_function"

        obj = InvalidExecutable()
        assert is_executable(obj) is False

    def test_metadata_with_none_value(self):
        """Test is_metadata_provider when metadata is None."""

        class MetadataWithNone:
            metadata = None

        obj = MetadataWithNone()
        # Should still return True as it has the attribute
        assert is_metadata_provider(obj) is True

    def test_id_with_different_types(self):
        """Test is_identifiable with different id types."""

        class NumericId:
            id = 123

        class TupleId:
            id = (1, 2, 3)

        assert is_identifiable(NumericId()) is True
        assert is_identifiable(TupleId()) is True


@pytest.mark.unit
class TestProtocolWithDynamicAttributes:
    """Test protocols with dynamically added attributes."""

    def test_dynamic_serializable(self):
        """Test adding serialize method dynamically."""

        class DynamicClass:
            pass

        obj = DynamicClass()
        assert is_serializable(obj) is False

        # Add method dynamically
        obj.serialize = lambda: {"dynamic": "data"}
        assert is_serializable(obj) is True

    def test_dynamic_identifiable(self):
        """Test adding id attribute dynamically."""

        class DynamicClass:
            pass

        obj = DynamicClass()
        assert is_identifiable(obj) is False

        # Add attribute dynamically
        obj.id = "dynamic_id"
        assert is_identifiable(obj) is True

    def test_dynamic_nameable(self):
        """Test adding nameable methods dynamically."""

        class DynamicClass:
            def __init__(self):
                self._name = "test"

        obj = DynamicClass()
        assert is_nameable(obj) is False

        # Add methods dynamically
        obj.get_name = lambda: obj._name
        obj.set_name = lambda name: setattr(obj, "_name", name)
        assert is_nameable(obj) is True


@pytest.mark.unit
class TestPrimitiveValueValidationEdgeCases:
    """Test edge cases for primitive value validation."""

    def test_validate_primitive_with_custom_object(self):
        """Test validate_primitive_value with custom object."""

        class CustomObject:
            pass

        with pytest.raises(TypeError) as exc_info:
            validate_primitive_value(CustomObject())
        assert "Expected primitive value" in str(exc_info.value)
        assert "CustomObject" in str(exc_info.value)

    def test_validate_primitive_with_lambda(self):
        """Test validate_primitive_value with lambda."""
        with pytest.raises(TypeError) as exc_info:
            validate_primitive_value(lambda x: x)
        assert "Expected primitive value" in str(exc_info.value)

    def test_is_primitive_value_with_numeric_edge_cases(self):
        """Test is_primitive_value with numeric edge cases."""
        assert is_primitive_value(float("inf")) is True
        assert is_primitive_value(float("-inf")) is True
        assert is_primitive_value(float("nan")) is True
        assert is_primitive_value(-999999) is True
        assert is_primitive_value(999999.999999) is True

    def test_is_primitive_value_with_negative_zero(self):
        """Test is_primitive_value with negative zero."""
        assert is_primitive_value(-0.0) is True
        assert is_primitive_value(0.0) is True


@pytest.mark.unit
class TestContextValueValidationEdgeCases:
    """Test edge cases for context value validation."""

    def test_validate_context_value_with_tuple(self):
        """Test validate_context_value with tuple (invalid)."""
        with pytest.raises(TypeError) as exc_info:
            validate_context_value((1, 2, 3))
        assert "Expected context value" in str(exc_info.value)

    def test_is_context_value_with_deeply_nested_structures(self):
        """Test is_context_value with deeply nested structures."""
        deep_list = [[[[[1]]]]]
        assert is_context_value(deep_list) is True

        deep_dict = {"a": {"b": {"c": {"d": "value"}}}}
        assert is_context_value(deep_dict) is True

    def test_is_context_value_with_mixed_key_types(self):
        """Test is_context_value with mixed dict key types."""
        mixed_keys = {1: "one", "two": 2}
        assert is_context_value(mixed_keys) is False

    def test_is_context_value_with_empty_nested_structures(self):
        """Test is_context_value with empty nested structures."""
        assert is_context_value([[], {}, []]) is True
        assert is_context_value({"a": [], "b": {}}) is True

    def test_validate_context_value_with_frozenset(self):
        """Test validate_context_value with frozenset (invalid)."""
        with pytest.raises(TypeError):
            validate_context_value(frozenset([1, 2, 3]))


@pytest.mark.unit
class TestProtocolCompliance:
    """Test actual protocol compliance and type checking."""

    def test_protocol_type_annotation_compliance(self):
        """Test that implementations satisfy protocol type annotations."""

        class CompliantSerializable:
            def serialize(self) -> dict[str, object]:
                return {"key": "value"}

        obj = CompliantSerializable()
        assert is_serializable(obj) is True

        # Test actual method signature compliance
        result = obj.serialize()
        assert isinstance(result, dict)

    def test_protocol_method_signature_validation(self):
        """Test protocol methods accept correct signatures."""

        class CompliantExecutable:
            def execute(self, *args: object, **kwargs: object) -> object:
                return f"args: {args}, kwargs: {kwargs}"

        obj = CompliantExecutable()
        assert is_executable(obj) is True

        # Test with various argument patterns
        result1 = obj.execute()
        assert "args: ()" in result1

        result2 = obj.execute(1, 2, 3)
        assert "args: (1, 2, 3)" in result2

        result3 = obj.execute(a=1, b=2)
        assert "kwargs:" in result3

    def test_protocol_property_compliance(self):
        """Test protocol properties work correctly."""

        class CompliantIdentifiable:
            @property
            def id(self) -> str:
                return self._compute_id()

            def _compute_id(self) -> str:
                return "computed_id"

        obj = CompliantIdentifiable()
        assert is_identifiable(obj) is True
        assert obj.id == "computed_id"


@pytest.mark.unit
class TestBaseCollectionAndFactory:
    """Test BaseCollection and BaseFactory imports."""

    def test_base_collection_is_available(self):
        """Test BaseCollection can be imported and used."""
        assert BaseCollection is not None
        # BaseCollection is an abstract class
        assert hasattr(BaseCollection, "__abstractmethods__")

    def test_base_factory_is_available(self):
        """Test BaseFactory can be imported and used."""
        assert BaseFactory is not None
        # BaseFactory is an abstract class
        assert hasattr(BaseFactory, "__abstractmethods__")


@pytest.mark.unit
class TestMultiProtocolObjects:
    """Test objects implementing multiple protocols simultaneously."""

    def test_full_protocol_implementation(self):
        """Test object implementing all protocols."""

        class FullProtocolClass:
            def __init__(self):
                self.id = "full_id"
                self._name = "full_name"

            @property
            def metadata(self) -> dict[str, object]:
                return {"type": "full"}

            def serialize(self) -> dict[str, object]:
                return {"id": self.id, "name": self._name}

            def validate_instance(self) -> bool:
                return len(self.id) > 0

            def configure(self, **kwargs: object) -> bool:
                return True

            def execute(self, *args: object, **kwargs: object) -> object:
                return "executed"

            def get_name(self) -> str:
                return self._name

            def set_name(self, name: str) -> None:
                self._name = name

        obj = FullProtocolClass()

        # Verify all protocols
        assert is_identifiable(obj) is True
        assert is_metadata_provider(obj) is True
        assert is_serializable(obj) is True
        assert is_validatable(obj) is True
        assert is_configurable(obj) is True
        assert is_executable(obj) is True
        assert is_nameable(obj) is True

    def test_partial_protocol_implementation(self):
        """Test object implementing some but not all protocols."""

        class PartialProtocolClass:
            def __init__(self):
                self.id = "partial_id"

            def serialize(self) -> dict[str, object]:
                return {"id": self.id}

        obj = PartialProtocolClass()

        # Verify some protocols pass
        assert is_identifiable(obj) is True
        assert is_serializable(obj) is True

        # Verify others fail
        assert is_metadata_provider(obj) is False
        assert is_validatable(obj) is False
        assert is_configurable(obj) is False
        assert is_executable(obj) is False
        assert is_nameable(obj) is False
