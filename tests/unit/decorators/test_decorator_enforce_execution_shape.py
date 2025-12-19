"""
Test suite for enforce_execution_shape decorator.

Tests cover:
- Allowed execution shapes pass through correctly
- Forbidden execution shapes raise ModelOnexError at decoration time
- Decorator preserves function signature and docstring
- Works with both sync and async functions
- Works with class methods and static methods
- Error context contains appropriate details

Target: 90%+ coverage for decorators/decorator_enforce_execution_shape.py
"""

import pytest

# Module-level pytest marker for all tests in this file
pytestmark = pytest.mark.unit

from omnibase_core.decorators.decorator_enforce_execution_shape import (
    enforce_execution_shape,
)
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_execution_shape import EnumMessageCategory
from omnibase_core.enums.enum_node_kind import EnumNodeKind
from omnibase_core.models.errors.model_onex_error import ModelOnexError


@pytest.mark.unit
class TestEnforceExecutionShapeAllowedShapes:
    """Test enforce_execution_shape with allowed canonical shapes."""

    def test_event_to_orchestrator_allowed(self):
        """Test EVENT -> ORCHESTRATOR shape is allowed."""

        @enforce_execution_shape(
            source_category=EnumMessageCategory.EVENT,
            target_node_kind=EnumNodeKind.ORCHESTRATOR,
        )
        def handle_event(data: str) -> str:
            return f"processed: {data}"

        result = handle_event("test")
        assert result == "processed: test"

    def test_event_to_reducer_allowed(self):
        """Test EVENT -> REDUCER shape is allowed."""

        @enforce_execution_shape(
            source_category=EnumMessageCategory.EVENT,
            target_node_kind=EnumNodeKind.REDUCER,
        )
        def handle_event(data: str) -> str:
            return f"reduced: {data}"

        result = handle_event("test")
        assert result == "reduced: test"

    def test_intent_to_effect_allowed(self):
        """Test INTENT -> EFFECT shape is allowed."""

        @enforce_execution_shape(
            source_category=EnumMessageCategory.INTENT,
            target_node_kind=EnumNodeKind.EFFECT,
        )
        def handle_intent(data: str) -> str:
            return f"effect: {data}"

        result = handle_intent("test")
        assert result == "effect: test"

    def test_command_to_orchestrator_allowed(self):
        """Test COMMAND -> ORCHESTRATOR shape is allowed."""

        @enforce_execution_shape(
            source_category=EnumMessageCategory.COMMAND,
            target_node_kind=EnumNodeKind.ORCHESTRATOR,
        )
        def handle_command(data: str) -> str:
            return f"orchestrated: {data}"

        result = handle_command("test")
        assert result == "orchestrated: test"

    def test_command_to_effect_allowed(self):
        """Test COMMAND -> EFFECT shape is allowed."""

        @enforce_execution_shape(
            source_category=EnumMessageCategory.COMMAND,
            target_node_kind=EnumNodeKind.EFFECT,
        )
        def handle_command(data: str) -> str:
            return f"executed: {data}"

        result = handle_command("test")
        assert result == "executed: test"


@pytest.mark.unit
class TestEnforceExecutionShapeForbiddenShapes:
    """Test enforce_execution_shape with forbidden shapes."""

    def test_event_to_compute_forbidden(self):
        """Test EVENT -> COMPUTE shape raises error at decoration time."""
        with pytest.raises(ModelOnexError) as exc_info:

            @enforce_execution_shape(
                source_category=EnumMessageCategory.EVENT,
                target_node_kind=EnumNodeKind.COMPUTE,
            )
            def handle_event(data: str) -> str:
                return data

        assert exc_info.value.error_code == EnumCoreErrorCode.CONTRACT_VIOLATION
        assert "event" in exc_info.value.message.lower()
        assert "compute" in exc_info.value.message.lower()

    def test_event_to_effect_forbidden(self):
        """Test EVENT -> EFFECT shape raises error at decoration time."""
        with pytest.raises(ModelOnexError) as exc_info:

            @enforce_execution_shape(
                source_category=EnumMessageCategory.EVENT,
                target_node_kind=EnumNodeKind.EFFECT,
            )
            def handle_event(data: str) -> str:
                return data

        assert exc_info.value.error_code == EnumCoreErrorCode.CONTRACT_VIOLATION
        assert "no canonical shape" in exc_info.value.message.lower()

    def test_intent_to_reducer_forbidden(self):
        """Test INTENT -> REDUCER shape raises error at decoration time."""
        with pytest.raises(ModelOnexError) as exc_info:

            @enforce_execution_shape(
                source_category=EnumMessageCategory.INTENT,
                target_node_kind=EnumNodeKind.REDUCER,
            )
            def handle_intent(data: str) -> str:
                return data

        assert exc_info.value.error_code == EnumCoreErrorCode.CONTRACT_VIOLATION

    def test_intent_to_compute_forbidden(self):
        """Test INTENT -> COMPUTE shape raises error at decoration time."""
        with pytest.raises(ModelOnexError) as exc_info:

            @enforce_execution_shape(
                source_category=EnumMessageCategory.INTENT,
                target_node_kind=EnumNodeKind.COMPUTE,
            )
            def handle_intent(data: str) -> str:
                return data

        assert exc_info.value.error_code == EnumCoreErrorCode.CONTRACT_VIOLATION

    def test_intent_to_orchestrator_forbidden(self):
        """Test INTENT -> ORCHESTRATOR shape raises error at decoration time."""
        with pytest.raises(ModelOnexError) as exc_info:

            @enforce_execution_shape(
                source_category=EnumMessageCategory.INTENT,
                target_node_kind=EnumNodeKind.ORCHESTRATOR,
            )
            def handle_intent(data: str) -> str:
                return data

        assert exc_info.value.error_code == EnumCoreErrorCode.CONTRACT_VIOLATION

    def test_command_to_compute_forbidden(self):
        """Test COMMAND -> COMPUTE shape raises error at decoration time."""
        with pytest.raises(ModelOnexError) as exc_info:

            @enforce_execution_shape(
                source_category=EnumMessageCategory.COMMAND,
                target_node_kind=EnumNodeKind.COMPUTE,
            )
            def handle_command(data: str) -> str:
                return data

        assert exc_info.value.error_code == EnumCoreErrorCode.CONTRACT_VIOLATION

    def test_command_to_reducer_forbidden(self):
        """Test COMMAND -> REDUCER shape raises error at decoration time."""
        with pytest.raises(ModelOnexError) as exc_info:

            @enforce_execution_shape(
                source_category=EnumMessageCategory.COMMAND,
                target_node_kind=EnumNodeKind.REDUCER,
            )
            def handle_command(data: str) -> str:
                return data

        assert exc_info.value.error_code == EnumCoreErrorCode.CONTRACT_VIOLATION

    def test_any_to_runtime_host_forbidden(self):
        """Test any category -> RUNTIME_HOST shape raises error."""
        for category in EnumMessageCategory:
            with pytest.raises(ModelOnexError) as exc_info:

                @enforce_execution_shape(
                    source_category=category,
                    target_node_kind=EnumNodeKind.RUNTIME_HOST,
                )
                def handle_message(data: str) -> str:
                    return data

            assert exc_info.value.error_code == EnumCoreErrorCode.CONTRACT_VIOLATION


@pytest.mark.unit
class TestEnforceExecutionShapeErrorContext:
    """Test error context details for forbidden shapes."""

    def _get_additional_context(
        self, error: ModelOnexError
    ) -> dict[str, str | dict[str, str]]:
        """Helper to extract additional_context from error context."""
        context = error.context
        additional = context.get("additional_context", {})
        if isinstance(additional, dict):
            # Context is nested: additional_context.context.{field}
            return additional.get("context", additional)
        return {}

    def test_error_context_contains_source_category(self):
        """Test error context includes source_category."""
        with pytest.raises(ModelOnexError) as exc_info:

            @enforce_execution_shape(
                source_category=EnumMessageCategory.EVENT,
                target_node_kind=EnumNodeKind.COMPUTE,
            )
            def handle_event(data: str) -> str:
                return data

        additional_context = self._get_additional_context(exc_info.value)
        assert additional_context.get("source_category") == "event"

    def test_error_context_contains_target_node_kind(self):
        """Test error context includes target_node_kind."""
        with pytest.raises(ModelOnexError) as exc_info:

            @enforce_execution_shape(
                source_category=EnumMessageCategory.INTENT,
                target_node_kind=EnumNodeKind.REDUCER,
            )
            def handle_intent(data: str) -> str:
                return data

        additional_context = self._get_additional_context(exc_info.value)
        assert additional_context.get("target_node_kind") == "reducer"

    def test_error_context_contains_rationale(self):
        """Test error context includes rationale."""
        with pytest.raises(ModelOnexError) as exc_info:

            @enforce_execution_shape(
                source_category=EnumMessageCategory.COMMAND,
                target_node_kind=EnumNodeKind.COMPUTE,
            )
            def handle_command(data: str) -> str:
                return data

        additional_context = self._get_additional_context(exc_info.value)
        rationale = additional_context.get("rationale", "")
        assert isinstance(rationale, str)
        assert "no canonical shape" in rationale.lower()


@pytest.mark.unit
class TestEnforceExecutionShapePreservesFunctionMetadata:
    """Test decorator preserves function signature and docstring."""

    def test_preserves_function_name(self):
        """Test decorator preserves function __name__."""

        @enforce_execution_shape(
            source_category=EnumMessageCategory.EVENT,
            target_node_kind=EnumNodeKind.ORCHESTRATOR,
        )
        def my_handler_function(data: str) -> str:
            return data

        assert my_handler_function.__name__ == "my_handler_function"

    def test_preserves_function_docstring(self):
        """Test decorator preserves function __doc__."""

        @enforce_execution_shape(
            source_category=EnumMessageCategory.EVENT,
            target_node_kind=EnumNodeKind.REDUCER,
        )
        def my_handler_function(data: str) -> str:
            """This is my handler docstring."""
            return data

        assert my_handler_function.__doc__ == "This is my handler docstring."

    def test_preserves_function_annotations(self):
        """Test decorator preserves function __annotations__."""

        @enforce_execution_shape(
            source_category=EnumMessageCategory.INTENT,
            target_node_kind=EnumNodeKind.EFFECT,
        )
        def my_handler(data: str, count: int) -> str:
            return f"{data}-{count}"

        annotations = my_handler.__annotations__
        assert annotations.get("data") == str
        assert annotations.get("count") == int
        assert annotations.get("return") == str


@pytest.mark.unit
class TestEnforceExecutionShapeAsyncFunctions:
    """Test decorator works with async functions."""

    @pytest.mark.asyncio
    async def test_async_function_allowed_shape(self):
        """Test async function with allowed shape works correctly."""

        @enforce_execution_shape(
            source_category=EnumMessageCategory.EVENT,
            target_node_kind=EnumNodeKind.ORCHESTRATOR,
        )
        async def async_handler(data: str) -> str:
            return f"async: {data}"

        result = await async_handler("test")
        assert result == "async: test"

    @pytest.mark.asyncio
    async def test_async_function_preserves_name(self):
        """Test async function preserves __name__."""

        @enforce_execution_shape(
            source_category=EnumMessageCategory.COMMAND,
            target_node_kind=EnumNodeKind.EFFECT,
        )
        async def my_async_handler(data: str) -> str:
            """Async handler docstring."""
            return data

        assert my_async_handler.__name__ == "my_async_handler"
        assert my_async_handler.__doc__ == "Async handler docstring."

    def test_async_function_forbidden_shape_raises_at_decoration(self):
        """Test async function with forbidden shape raises at decoration time."""
        with pytest.raises(ModelOnexError) as exc_info:

            @enforce_execution_shape(
                source_category=EnumMessageCategory.EVENT,
                target_node_kind=EnumNodeKind.COMPUTE,
            )
            async def async_handler(data: str) -> str:
                return data

        assert exc_info.value.error_code == EnumCoreErrorCode.CONTRACT_VIOLATION


@pytest.mark.unit
class TestEnforceExecutionShapeClassMethods:
    """Test decorator works with class methods."""

    def test_instance_method_allowed_shape(self):
        """Test instance method with allowed shape works correctly."""

        class EventHandler:
            @enforce_execution_shape(
                source_category=EnumMessageCategory.EVENT,
                target_node_kind=EnumNodeKind.ORCHESTRATOR,
            )
            def handle(self, data: str) -> str:
                return f"instance: {data}"

        handler = EventHandler()
        result = handler.handle("test")
        assert result == "instance: test"

    def test_static_method_allowed_shape(self):
        """Test static method with allowed shape works correctly."""

        class EventHandler:
            @staticmethod
            @enforce_execution_shape(
                source_category=EnumMessageCategory.EVENT,
                target_node_kind=EnumNodeKind.REDUCER,
            )
            def handle(data: str) -> str:
                return f"static: {data}"

        result = EventHandler.handle("test")
        assert result == "static: test"

    def test_class_method_allowed_shape(self):
        """Test class method with allowed shape works correctly."""

        class EventHandler:
            handler_type = "event"

            @classmethod
            @enforce_execution_shape(
                source_category=EnumMessageCategory.COMMAND,
                target_node_kind=EnumNodeKind.ORCHESTRATOR,
            )
            def handle(cls, data: str) -> str:
                return f"{cls.handler_type}: {data}"

        result = EventHandler.handle("test")
        assert result == "event: test"


@pytest.mark.unit
class TestEnforceExecutionShapeReturnTypes:
    """Test decorator works with various return types."""

    def test_returns_none(self):
        """Test function returning None works correctly."""

        @enforce_execution_shape(
            source_category=EnumMessageCategory.EVENT,
            target_node_kind=EnumNodeKind.ORCHESTRATOR,
        )
        def void_handler(data: str) -> None:
            pass

        result = void_handler("test")
        assert result is None

    def test_returns_dict(self):
        """Test function returning dict works correctly."""

        @enforce_execution_shape(
            source_category=EnumMessageCategory.COMMAND,
            target_node_kind=EnumNodeKind.EFFECT,
        )
        def dict_handler(data: str) -> dict[str, int]:
            return {"count": len(data)}

        result = dict_handler("test")
        assert result == {"count": 4}

    def test_returns_list(self):
        """Test function returning list works correctly."""

        @enforce_execution_shape(
            source_category=EnumMessageCategory.EVENT,
            target_node_kind=EnumNodeKind.REDUCER,
        )
        def list_handler(data: str) -> list[str]:
            return list(data)

        result = list_handler("abc")
        assert result == ["a", "b", "c"]


@pytest.mark.unit
class TestEnforceExecutionShapeArgsKwargs:
    """Test decorator works with various argument patterns."""

    def test_function_with_args_and_kwargs(self):
        """Test function with *args and **kwargs works correctly."""

        @enforce_execution_shape(
            source_category=EnumMessageCategory.EVENT,
            target_node_kind=EnumNodeKind.ORCHESTRATOR,
        )
        def flexible_handler(
            *args: str, prefix: str = "", **kwargs: str
        ) -> dict[str, str | tuple[str, ...]]:
            return {"args": args, "prefix": prefix, "kwargs": kwargs}

        result = flexible_handler("a", "b", prefix="test", extra="value")
        assert result["args"] == ("a", "b")
        assert result["prefix"] == "test"
        assert result["kwargs"] == {"extra": "value"}

    def test_function_with_default_args(self):
        """Test function with default arguments works correctly."""

        @enforce_execution_shape(
            source_category=EnumMessageCategory.INTENT,
            target_node_kind=EnumNodeKind.EFFECT,
        )
        def handler_with_defaults(
            data: str, multiplier: int = 2, suffix: str = "!"
        ) -> str:
            return (data * multiplier) + suffix

        result = handler_with_defaults("test")
        assert result == "testtest!"

        result = handler_with_defaults("test", multiplier=3, suffix="?")
        assert result == "testtesttest?"


@pytest.mark.unit
class TestEnforceExecutionShapeAllCanonicalShapes:
    """Parametrized tests for all canonical shapes."""

    @pytest.mark.parametrize(
        ("category", "node_kind"),
        [
            (EnumMessageCategory.EVENT, EnumNodeKind.ORCHESTRATOR),
            (EnumMessageCategory.EVENT, EnumNodeKind.REDUCER),
            (EnumMessageCategory.INTENT, EnumNodeKind.EFFECT),
            (EnumMessageCategory.COMMAND, EnumNodeKind.ORCHESTRATOR),
            (EnumMessageCategory.COMMAND, EnumNodeKind.EFFECT),
        ],
    )
    def test_all_allowed_shapes(
        self, category: EnumMessageCategory, node_kind: EnumNodeKind
    ):
        """Test all canonical allowed shapes pass validation."""

        @enforce_execution_shape(
            source_category=category,
            target_node_kind=node_kind,
        )
        def handler(data: str) -> str:
            return data

        result = handler("test")
        assert result == "test"

    @pytest.mark.parametrize(
        ("category", "node_kind"),
        [
            (EnumMessageCategory.EVENT, EnumNodeKind.COMPUTE),
            (EnumMessageCategory.EVENT, EnumNodeKind.EFFECT),
            (EnumMessageCategory.INTENT, EnumNodeKind.REDUCER),
            (EnumMessageCategory.INTENT, EnumNodeKind.COMPUTE),
            (EnumMessageCategory.INTENT, EnumNodeKind.ORCHESTRATOR),
            (EnumMessageCategory.COMMAND, EnumNodeKind.COMPUTE),
            (EnumMessageCategory.COMMAND, EnumNodeKind.REDUCER),
            (EnumMessageCategory.EVENT, EnumNodeKind.RUNTIME_HOST),
            (EnumMessageCategory.INTENT, EnumNodeKind.RUNTIME_HOST),
            (EnumMessageCategory.COMMAND, EnumNodeKind.RUNTIME_HOST),
        ],
    )
    def test_all_forbidden_shapes(
        self, category: EnumMessageCategory, node_kind: EnumNodeKind
    ):
        """Test all forbidden shapes raise error at decoration time."""
        with pytest.raises(ModelOnexError) as exc_info:

            @enforce_execution_shape(
                source_category=category,
                target_node_kind=node_kind,
            )
            def handler(data: str) -> str:
                return data

        assert exc_info.value.error_code == EnumCoreErrorCode.CONTRACT_VIOLATION
