"""
Tests for protocol implementations across different model types.

Tests protocol compliance for various omnibase_core models and validates
that protocols work correctly with real model implementations.
"""

import pytest
from pydantic import BaseModel, Field

from omnibase_core.core.type_constraints import (
    Configurable,
    Executable,
    Identifiable,
    Nameable,
    ProtocolMetadataProvider,
    ProtocolValidatable,
    Serializable,
    is_configurable,
    is_executable,
    is_identifiable,
    is_metadata_provider,
    is_nameable,
    is_serializable,
    is_validatable,
)


class TestProtocolWithComplexModels:
    """Test protocols with more complex model structures."""

    def test_nested_model_serialization(self):
        """Test serializable protocol with nested models."""

        class InnerModel(BaseModel):
            value: int = 1

        class OuterModel(BaseModel):
            inner: InnerModel = Field(default_factory=InnerModel)
            name: str = "outer"

            def serialize(self) -> dict[str, object]:
                return {
                    "name": self.name,
                    "inner": self.inner.model_dump(),
                }

        model = OuterModel()
        assert is_serializable(model) is True
        result = model.serialize()
        assert "name" in result
        assert "inner" in result

    def test_model_with_validators(self):
        """Test validatable protocol with field validators."""

        class ValidatedModel(BaseModel):
            email: str = "test@example.com"
            age: int = 25

            def validate_instance(self) -> bool:
                return "@" in self.email and self.age >= 0

        model = ValidatedModel()
        assert is_validatable(model) is True
        assert model.validate_instance() is True

        invalid_model = ValidatedModel(email="invalid", age=25)
        assert invalid_model.validate_instance() is False

    def test_model_with_complex_metadata(self):
        """Test metadata provider with complex metadata."""

        class MetadataModel(BaseModel):
            identifier: str = "test_id"  # Test fixture

            @property
            def id(self) -> str:
                """Provide id property for Identifiable protocol."""
                return self.identifier

            @property
            def metadata(self) -> dict[str, object]:
                return {
                    "id": self.id,
                    "type": self.__class__.__name__,
                    "fields": list(self.model_fields.keys()),
                    "nested": {
                        "version": "1.0",
                        "created": "2024-01-01",
                    },
                }

        model = MetadataModel()
        assert is_metadata_provider(model) is True
        meta = model.metadata
        assert "id" in meta
        assert "type" in meta
        assert "fields" in meta
        assert "nested" in meta


class TestProtocolWithOptionalFields:
    """Test protocols with optional and default fields."""

    def test_optional_fields_serialization(self):
        """Test serialization with optional fields."""

        class OptionalFieldsModel(BaseModel):
            required_field: str = "required"
            optional_field: str | None = None

            def serialize(self) -> dict[str, object]:
                result: dict[str, object] = {"required_field": self.required_field}
                if self.optional_field is not None:
                    result["optional_field"] = self.optional_field
                return result

        model1 = OptionalFieldsModel()
        assert is_serializable(model1) is True
        result1 = model1.serialize()
        assert "required_field" in result1
        assert "optional_field" not in result1

        model2 = OptionalFieldsModel(optional_field="present")
        result2 = model2.serialize()
        assert "optional_field" in result2

    def test_configurable_with_optional_config(self):
        """Test configurable protocol with optional configuration."""

        class OptionalConfigModel(BaseModel):
            enabled: bool = False
            timeout: int | None = None

            def configure(self, **kwargs: object) -> bool:
                updated = False
                if "enabled" in kwargs:
                    self.enabled = bool(kwargs["enabled"])
                    updated = True
                if "timeout" in kwargs:
                    self.timeout = int(kwargs["timeout"]) if kwargs["timeout"] else None
                    updated = True
                return updated

        model = OptionalConfigModel()
        assert is_configurable(model) is True
        assert model.configure(enabled=True) is True
        assert model.enabled is True
        assert model.timeout is None


class TestProtocolChaining:
    """Test chaining multiple protocol operations."""

    def test_serialize_validate_chain(self):
        """Test chaining serialize and validate operations."""

        class ChainableModel(BaseModel):
            value: int = 10

            def serialize(self) -> dict[str, object]:
                return {"value": self.value, "validated": self.validate_instance()}

            def validate_instance(self) -> bool:
                return self.value > 0

        model = ChainableModel(value=5)
        assert is_serializable(model) is True
        assert is_validatable(model) is True

        result = model.serialize()
        assert result["value"] == 5
        assert result["validated"] is True

    def test_configure_execute_chain(self):
        """Test chaining configure and execute operations."""

        class ConfigurableExecutor(BaseModel):
            command: str = "default"
            args: list[str] = Field(default_factory=list)

            def configure(self, **kwargs: object) -> bool:
                if "command" in kwargs:
                    self.command = str(kwargs["command"])
                if "args" in kwargs and isinstance(kwargs["args"], list):
                    self.args = kwargs["args"]
                return True

            def execute(self, *args: object, **kwargs: object) -> object:
                all_args = list(self.args) + list(args)
                return f"{self.command} {' '.join(str(a) for a in all_args)}"

        model = ConfigurableExecutor()
        assert is_configurable(model) is True
        assert is_executable(model) is True

        model.configure(command="run", args=["--verbose"])
        result = model.execute("file.txt")
        assert "run" in result
        assert "--verbose" in result
        assert "file.txt" in result


class TestProtocolErrorHandling:
    """Test error handling in protocol implementations."""

    def test_serialization_with_error_handling(self):
        """Test serialize method with error handling."""

        class SafeSerializableModel(BaseModel):
            value: str = "test"
            unsafe_value: object = None

            def serialize(self) -> dict[str, object]:
                result: dict[str, object] = {}
                try:
                    result["value"] = self.value
                    if self.unsafe_value is not None:
                        result["unsafe"] = str(self.unsafe_value)
                except Exception as e:
                    result["error"] = str(e)
                return result

        model = SafeSerializableModel(unsafe_value=lambda: None)
        assert is_serializable(model) is True
        result = model.serialize()
        assert "value" in result

    def test_validation_with_exception_handling(self):
        """Test validate_instance with exception handling."""

        class SafeValidatableModel(BaseModel):
            value: int = 10

            def validate_instance(self) -> bool:
                try:
                    return self.value > 0 and self.value < 100
                except Exception:
                    return False

        model = SafeValidatableModel()
        assert is_validatable(model) is True
        assert model.validate_instance() is True


class TestProtocolWithCustomTypes:
    """Test protocols with custom type definitions."""

    def test_custom_id_type(self):
        """Test identifiable protocol with custom ID type."""

        class CustomIdModel:
            def __init__(self, id_prefix: str = "ID"):
                self._id_prefix = id_prefix
                self._id_number = 12345

            @property
            def id(self) -> str:
                return f"{self._id_prefix}_{self._id_number}"

        model = CustomIdModel("USER")
        assert is_identifiable(model) is True
        assert model.id == "USER_12345"

    def test_custom_metadata_type(self):
        """Test metadata provider with custom metadata structure."""

        class CustomMetadataModel:
            @property
            def metadata(self) -> dict[str, object]:
                return {
                    "version": 1,
                    "schema": {
                        "type": "object",
                        "properties": {},
                    },
                    "tags": ["test", "custom"],
                }

        model = CustomMetadataModel()
        assert is_metadata_provider(model) is True
        meta = model.metadata
        assert "version" in meta
        assert "schema" in meta
        assert "tags" in meta


class TestProtocolWithStateMachine:
    """Test protocols with stateful behavior."""

    def test_stateful_executable(self):
        """Test executable protocol with state tracking."""

        class StatefulExecutor:
            def __init__(self):
                self.execution_count = 0
                self.last_result: object = None

            def execute(self, *args: object, **kwargs: object) -> object:
                self.execution_count += 1
                self.last_result = f"Execution {self.execution_count}"
                return self.last_result

        executor = StatefulExecutor()
        assert is_executable(executor) is True

        result1 = executor.execute()
        assert executor.execution_count == 1
        assert result1 == "Execution 1"

        result2 = executor.execute()
        assert executor.execution_count == 2
        assert result2 == "Execution 2"

    def test_stateful_configurable(self):
        """Test configurable protocol with state changes."""

        class StatefulConfig:
            def __init__(self):
                self.config_history: list[dict[str, object]] = []
                self.current_config: dict[str, object] = {}

            def configure(self, **kwargs: object) -> bool:
                self.config_history.append(dict(kwargs))
                self.current_config.update(kwargs)
                return True

        config = StatefulConfig()
        assert is_configurable(config) is True

        config.configure(setting1="value1")
        assert len(config.config_history) == 1

        config.configure(setting2="value2")
        assert len(config.config_history) == 2
        assert "setting1" in config.current_config
        assert "setting2" in config.current_config


class TestProtocolComposition:
    """Test composing multiple protocol implementations."""

    def test_composition_through_delegation(self):
        """Test protocol implementation through delegation."""

        class InnerSerializable:
            def serialize(self) -> dict[str, object]:
                return {"inner": "data"}

        class OuterComposed:
            def __init__(self):
                self._inner = InnerSerializable()
                self.id = "outer_id"

            def serialize(self) -> dict[str, object]:
                result = self._inner.serialize()
                result["outer_id"] = self.id
                return result

        model = OuterComposed()
        assert is_serializable(model) is True
        assert is_identifiable(model) is True
        result = model.serialize()
        assert "inner" in result
        assert "outer_id" in result


class TestProtocolWithAsyncPatterns:
    """Test protocol patterns that could support async operations."""

    def test_executor_with_sync_and_async_patterns(self):
        """Test executable that supports both sync patterns."""

        class FlexibleExecutor:
            def __init__(self):
                self.mode = "sync"

            def execute(self, *args: object, **kwargs: object) -> object:
                if self.mode == "sync":
                    return self._execute_sync(*args, **kwargs)
                return f"Mode: {self.mode}"

            def _execute_sync(self, *args: object, **kwargs: object) -> object:
                return f"Sync result: {args}"

        executor = FlexibleExecutor()
        assert is_executable(executor) is True
        result = executor.execute("test")
        assert "Sync result" in str(result)


class TestProtocolWithBuilders:
    """Test protocols with builder pattern implementations."""

    def test_buildable_configurable(self):
        """Test configurable protocol with builder pattern."""

        class BuildableConfig:
            def __init__(self):
                self.settings: dict[str, object] = {}

            def configure(self, **kwargs: object) -> bool:
                self.settings.update(kwargs)
                return True

            def build(self) -> dict[str, object]:
                return dict(self.settings)

        config = BuildableConfig()
        assert is_configurable(config) is True
        config.configure(option1="value1")
        config.configure(option2="value2")
        result = config.build()
        assert result["option1"] == "value1"
        assert result["option2"] == "value2"


class TestProtocolBoundaryConditions:
    """Test boundary conditions for protocol implementations."""

    def test_empty_serialization(self):
        """Test serialization returning empty dict."""

        class EmptySerializable:
            def serialize(self) -> dict[str, object]:
                return {}

        obj = EmptySerializable()
        assert is_serializable(obj) is True
        assert obj.serialize() == {}

    def test_always_valid_validator(self):
        """Test validator that always returns True."""

        class AlwaysValidModel:
            def validate_instance(self) -> bool:
                return True

        obj = AlwaysValidModel()
        assert is_validatable(obj) is True
        assert obj.validate_instance() is True

    def test_always_false_validator(self):
        """Test validator that always returns False."""

        class NeverValidModel:
            def validate_instance(self) -> bool:
                return False

        obj = NeverValidModel()
        assert is_validatable(obj) is True
        assert obj.validate_instance() is False

    def test_executor_returning_none(self):
        """Test executor that returns None."""

        class NoneExecutor:
            def execute(self, *args: object, **kwargs: object) -> object:
                return None

        executor = NoneExecutor()
        assert is_executable(executor) is True
        assert executor.execute() is None

    def test_empty_metadata_provider(self):
        """Test metadata provider returning empty dict."""

        class EmptyMetadata:
            @property
            def metadata(self) -> dict[str, object]:
                return {}

        obj = EmptyMetadata()
        assert is_metadata_provider(obj) is True
        assert obj.metadata == {}


class TestProtocolWithGenericTypes:
    """Test protocols with generic type parameters."""

    def test_generic_serializable(self):
        """Test serializable with generic content."""

        class GenericSerializable:
            def __init__(self, content: object):
                self.content = content

            def serialize(self) -> dict[str, object]:
                return {"content": self.content, "type": type(self.content).__name__}

        obj1 = GenericSerializable("string")
        obj2 = GenericSerializable(42)
        obj3 = GenericSerializable([1, 2, 3])

        assert is_serializable(obj1) is True
        assert is_serializable(obj2) is True
        assert is_serializable(obj3) is True

        assert obj1.serialize()["type"] == "str"
        assert obj2.serialize()["type"] == "int"
        assert obj3.serialize()["type"] == "list"
