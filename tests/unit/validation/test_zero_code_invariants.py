# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for zero-code contract-driven node invariants.

Validates architectural invariants for contract-driven nodes (OMN-1731).
"""

from __future__ import annotations

import pytest

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_handler_routing_strategy import EnumHandlerRoutingStrategy
from omnibase_core.models.container.model_protocols_namespace import (
    ModelProtocolsNamespace,
)
from omnibase_core.models.contracts.subcontracts.model_handler_routing_entry import (
    ModelHandlerRoutingEntry,
)
from omnibase_core.models.contracts.subcontracts.model_handler_routing_subcontract import (
    ModelHandlerRoutingSubcontract,
)
from omnibase_core.models.contracts.subcontracts.model_protocol_dependency import (
    ModelProtocolDependency,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.resolution.resolver_handler import (
    clear_handler_cache,
    resolve_handler,
)

pytestmark = pytest.mark.unit


def _handler_entry(
    name: str,
    *,
    operation: str | None = None,
    event_type: str | None = None,
    event_model: dict[str, str] | None = None,
) -> ModelHandlerRoutingEntry:
    return ModelHandlerRoutingEntry(
        handler={"name": name, "module": "tests.handlers"},
        operation=operation,
        event_type=event_type,
        event_model=event_model,
    )


class TestHandlerRoutingLiveShape:
    """Tests for the canonical five-field handler routing shape."""

    def test_operation_match_builds_routing_table(self) -> None:
        subcontract = ModelHandlerRoutingSubcontract(
            version=ModelSemVer(major=1, minor=0, patch=0),
            routing_strategy=EnumHandlerRoutingStrategy.OPERATION_MATCH,
            handlers=[
                _handler_entry("HandlerA", operation="event.a"),
                _handler_entry("HandlerB", operation="event.b"),
            ],
        )

        assert subcontract.build_routing_table() == {
            "event.a": ["HandlerA"],
            "event.b": ["HandlerB"],
        }

    def test_payload_type_match_builds_routing_table(self) -> None:
        subcontract = ModelHandlerRoutingSubcontract(
            version=ModelSemVer(major=1, minor=0, patch=0),
            routing_strategy=EnumHandlerRoutingStrategy.PAYLOAD_TYPE_MATCH,
            handlers=[
                _handler_entry(
                    "HandlerUserCreated",
                    event_model={
                        "name": "ModelUserCreated",
                        "module": "tests.models",
                    },
                )
            ],
        )

        assert subcontract.build_routing_table() == {
            "ModelUserCreated": ["HandlerUserCreated"]
        }

    def test_topic_pattern_builds_routing_table_from_event_type(self) -> None:
        subcontract = ModelHandlerRoutingSubcontract(
            version=ModelSemVer(major=1, minor=0, patch=0),
            routing_strategy=EnumHandlerRoutingStrategy.TOPIC_PATTERN,
            handlers=[
                _handler_entry("HandlerLifecycle", event_type="omni.lifecycle.*"),
            ],
        )

        assert subcontract.build_routing_table() == {
            "omni.lifecycle.*": ["HandlerLifecycle"]
        }

    def test_missing_discriminator_is_skipped_for_active_strategy(self) -> None:
        subcontract = ModelHandlerRoutingSubcontract(
            version=ModelSemVer(major=1, minor=0, patch=0),
            routing_strategy=EnumHandlerRoutingStrategy.OPERATION_MATCH,
            handlers=[_handler_entry("HandlerA", event_type="event.a")],
        )

        assert subcontract.build_routing_table() == {}

    def test_legacy_extra_fields_are_ignored_during_transition(self) -> None:
        entry = ModelHandlerRoutingEntry(
            handler={"name": "HandlerEvent", "module": "tests.handlers"},
            routing_key="legacy.event",
            handler_key="handle_legacy_event",
            priority=10,
        )

        assert entry.handler.name == "HandlerEvent"
        assert not hasattr(entry, "routing_key")
        assert not hasattr(entry, "handler_key")


class TestProtocolDependencyValidation:
    """Tests for protocol dependency configuration."""

    def test_protocol_path_requires_colon_separator(self) -> None:
        """Protocol path must be in module.path:ClassName format."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelProtocolDependency(
                name="ProtocolLogger",
                protocol="omnibase_core.protocols.ProtocolLogger",  # Missing colon!
            )
        assert "colon-separated" in str(exc_info.value).lower()
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR

    def test_protocol_path_empty_module_fails(self) -> None:
        """Empty module path should fail validation."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelProtocolDependency(
                name="ProtocolLogger",
                protocol=":ProtocolLogger",  # Empty module
            )
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR

    def test_protocol_path_empty_class_fails(self) -> None:
        """Empty class name should fail validation."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelProtocolDependency(
                name="ProtocolLogger",
                protocol="omnibase_core.protocols:",  # Empty class
            )
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR

    def test_valid_protocol_dependency(self) -> None:
        """Valid protocol dependency is accepted."""
        dep = ModelProtocolDependency(
            name="ProtocolLogger",
            protocol="omnibase_core.protocols.protocol_logger:ProtocolLogger",
        )
        assert dep.get_bind_name() == "logger"

    def test_bind_as_overrides_derived_name(self) -> None:
        """bind_as takes precedence over derived name."""
        dep = ModelProtocolDependency(
            name="ProtocolLogger",
            protocol="omnibase_core.protocols.protocol_logger:ProtocolLogger",
            bind_as="custom_log",
        )
        assert dep.get_bind_name() == "custom_log"

    def test_protocol_dependency_immutable(self) -> None:
        """Protocol dependency model is frozen (immutable)."""
        dep = ModelProtocolDependency(
            name="ProtocolLogger",
            protocol="omnibase_core.protocols.protocol_logger:ProtocolLogger",
        )
        with pytest.raises(Exception):  # Pydantic raises ValidationError for frozen
            # NOTE(OMN-1731): Intentional assignment to frozen model to test immutability.
            dep.name = "NewName"  # type: ignore[misc]

    def test_pascal_to_snake_conversion(self) -> None:
        """Protocol name is correctly converted to snake_case."""
        dep = ModelProtocolDependency(
            name="ProtocolEventBus",
            protocol="m:C",  # Minimal valid format
        )
        assert dep.get_bind_name() == "event_bus"

    def test_name_without_protocol_prefix(self) -> None:
        """Name without Protocol prefix is still converted correctly."""
        dep = ModelProtocolDependency(
            name="EventBus",
            protocol="m:C",
        )
        assert dep.get_bind_name() == "event_bus"

    def test_invalid_name_format_fails(self) -> None:
        """Invalid Python identifier as name should fail."""
        with pytest.raises(ModelOnexError):
            ModelProtocolDependency(
                name="123Invalid",  # Starts with number
                protocol="m:C",
            )

    def test_invalid_bind_as_format_fails(self) -> None:
        """Invalid Python identifier as bind_as should fail."""
        with pytest.raises(ModelOnexError):
            ModelProtocolDependency(
                name="ProtocolLogger",
                protocol="m:C",
                bind_as="123-invalid",  # Not a valid identifier
            )


class TestProtocolsNamespaceImmutability:
    """Tests that protocols namespace is truly immutable."""

    def test_cannot_set_attribute_after_init(self) -> None:
        """Setting attribute after init must raise AttributeError."""
        ns = ModelProtocolsNamespace({"logger": object()})
        with pytest.raises(AttributeError, match="immutable"):
            # NOTE(OMN-1731): Intentional dynamic attribute assignment to test immutability.
            ns.new_attr = "value"  # type: ignore[attr-defined]

    def test_cannot_modify_existing_protocol(self) -> None:
        """Cannot overwrite an existing protocol."""
        ns = ModelProtocolsNamespace({"logger": object()})
        with pytest.raises(AttributeError, match="immutable"):
            # NOTE(OMN-1731): Intentional assignment to existing attr to test immutability.
            ns.logger = object()  # type: ignore[misc]

    def test_cannot_delete_attribute(self) -> None:
        """Cannot delete attributes from namespace."""
        ns = ModelProtocolsNamespace({"logger": object()})
        with pytest.raises(AttributeError, match="immutable"):
            # NOTE(OMN-1731): Intentional deletion attempt to test immutability.
            del ns.logger  # type: ignore[attr-defined]

    def test_attribute_access_works(self) -> None:
        """Attribute access returns the protocol."""
        logger = object()
        ns = ModelProtocolsNamespace({"logger": logger})
        # NOTE(OMN-1731): Dynamic attribute access via __getattr__ not visible to mypy.
        assert ns.logger is logger  # type: ignore[attr-defined]

    def test_dict_access_works(self) -> None:
        """Dict-style access returns the protocol."""
        logger = object()
        ns = ModelProtocolsNamespace({"logger": logger})
        assert ns["logger"] is logger

    def test_missing_protocol_raises_attribute_error(self) -> None:
        """Accessing non-existent protocol raises AttributeError."""
        ns = ModelProtocolsNamespace({"logger": object()})
        with pytest.raises(AttributeError, match="not found"):
            # NOTE(OMN-1731): Intentional access to missing attr to test error handling.
            _ = ns.event_bus  # type: ignore[attr-defined]

    def test_missing_protocol_dict_raises_key_error(self) -> None:
        """Dict access to non-existent protocol raises KeyError."""
        ns = ModelProtocolsNamespace({"logger": object()})
        with pytest.raises(KeyError, match="not found"):
            _ = ns["event_bus"]

    def test_contains_check(self) -> None:
        """Membership test works correctly."""
        ns = ModelProtocolsNamespace({"logger": object()})
        assert "logger" in ns
        assert "event_bus" not in ns

    def test_iteration(self) -> None:
        """Can iterate over protocol names."""
        ns = ModelProtocolsNamespace({"logger": object(), "event_bus": object()})
        names = list(ns)
        assert "logger" in names
        assert "event_bus" in names
        assert len(names) == 2

    def test_len(self) -> None:
        """len() returns correct count."""
        ns = ModelProtocolsNamespace({"a": 1, "b": 2, "c": 3})
        assert len(ns) == 3

    def test_keys(self) -> None:
        """keys() returns protocol names."""
        ns = ModelProtocolsNamespace({"logger": object(), "event_bus": object()})
        keys = ns.keys()
        assert "logger" in keys
        assert "event_bus" in keys

    def test_get_with_default(self) -> None:
        """get() returns default for missing protocols."""
        ns = ModelProtocolsNamespace({"logger": object()})
        default = object()
        assert ns.get("missing", default) is default
        assert ns.get("logger") is not None

    def test_none_value_supported(self) -> None:
        """None values are supported for optional protocols."""
        ns = ModelProtocolsNamespace({"optional": None})
        assert "optional" in ns
        assert ns.get("optional") is None


class TestHandlerResolver:
    """Tests for handler resolver."""

    def setup_method(self) -> None:
        """Clear handler cache before each test."""
        clear_handler_cache()

    def teardown_method(self) -> None:
        """Clear handler cache after each test."""
        clear_handler_cache()

    def test_resolves_stdlib_callable(self) -> None:
        """Can resolve stdlib callables."""
        handler = resolve_handler("json:dumps", eager=True)
        assert callable(handler)

    def test_resolves_and_caches(self) -> None:
        """Handler is cached after first resolution."""
        handler1 = resolve_handler("json:dumps", eager=True)
        handler2 = resolve_handler("json:dumps", eager=True)
        assert handler1 is handler2

    def test_invalid_module_raises_error(self) -> None:
        """Invalid module path raises ModelOnexError."""
        with pytest.raises(ModelOnexError) as exc_info:
            resolve_handler("nonexistent_module_12345:function", eager=True)
        assert exc_info.value.error_code == EnumCoreErrorCode.HANDLER_EXECUTION_ERROR

    def test_invalid_callable_raises_error(self) -> None:
        """Invalid callable name raises ModelOnexError."""
        with pytest.raises(ModelOnexError) as exc_info:
            resolve_handler("json:nonexistent_function_12345", eager=True)
        assert exc_info.value.error_code == EnumCoreErrorCode.HANDLER_EXECUTION_ERROR
        assert "not found" in str(exc_info.value)

    def test_invalid_format_no_colon_raises_error(self) -> None:
        """Handler path without colon raises error."""
        with pytest.raises(ModelOnexError) as exc_info:
            resolve_handler("json.dumps", eager=True)  # No colon
        assert "Invalid handler path format" in str(exc_info.value)

    def test_invalid_format_multiple_colons_raises_error(self) -> None:
        """Handler path with multiple colons raises error."""
        with pytest.raises(ModelOnexError) as exc_info:
            resolve_handler("json:dumps:extra", eager=True)  # Multiple colons
        assert "Invalid handler path format" in str(exc_info.value)

    def test_empty_module_raises_error(self) -> None:
        """Empty module path raises error."""
        with pytest.raises(ModelOnexError) as exc_info:
            resolve_handler(":dumps", eager=True)
        assert "non-empty" in str(exc_info.value)

    def test_empty_callable_raises_error(self) -> None:
        """Empty callable name raises error."""
        with pytest.raises(ModelOnexError) as exc_info:
            resolve_handler("json:", eager=True)
        assert "non-empty" in str(exc_info.value)

    def test_lazy_returns_callable(self) -> None:
        """Lazy mode returns a callable that resolves later."""
        lazy_loader = resolve_handler("json:dumps", eager=False)
        assert callable(lazy_loader)
        handler = lazy_loader()
        assert callable(handler)

    def test_lazy_defers_import(self) -> None:
        """Lazy loading defers import until called."""
        # This should not raise even for invalid modules
        lazy_loader = resolve_handler(
            "nonexistent_module_for_lazy_test:func", eager=False
        )
        assert callable(lazy_loader)
        # Only when called should it fail
        with pytest.raises(ModelOnexError):
            lazy_loader()

    def test_non_callable_raises_error(self) -> None:
        """Non-callable attribute raises error."""
        # json.decoder is a module (not directly callable in the same way)
        # Let's use a constant that's definitely not callable
        with pytest.raises(ModelOnexError) as exc_info:
            resolve_handler("json:__version__", eager=True)
        assert "not callable" in str(exc_info.value)

    def test_clear_cache_allows_reimport(self) -> None:
        """Clearing cache allows handler to be re-imported."""
        handler1 = resolve_handler("json:dumps", eager=True)
        clear_handler_cache()
        handler2 = resolve_handler("json:dumps", eager=True)
        # After cache clear, new resolution happens but returns same function
        assert handler1 is handler2  # Same underlying function


class TestHandlerRoutingEntryValidation:
    """Tests for individual live-shape handler routing entries."""

    def test_handler_reference_is_required(self) -> None:
        with pytest.raises(ValueError, match="handler"):
            ModelHandlerRoutingEntry(operation="event.run")

    def test_valid_entry_with_all_live_fields(self) -> None:
        entry = ModelHandlerRoutingEntry(
            handler={"name": "HandlerJobCreated", "module": "myapp.handlers"},
            event_model={"name": "ModelEventJobCreated", "module": "myapp.models"},
            operation="job.created",
            event_type="omni.job.created",
            message_category="EVENT",
        )

        assert entry.handler.name == "HandlerJobCreated"
        assert entry.event_model is not None
        assert entry.event_model.name == "ModelEventJobCreated"
        assert entry.operation == "job.created"
        assert entry.event_type == "omni.job.created"
        assert entry.message_category == "EVENT"

    def test_legacy_extra_fields_do_not_become_model_attributes(self) -> None:
        entry = ModelHandlerRoutingEntry(
            handler={"name": "HandlerJobCreated", "module": "myapp.handlers"},
            routing_key="ModelEventJobCreated",
            handler_key="handle_job_created",
            priority=-10,
            output_events=["ModelEventJobStarted", "ModelEventJobFailed"],
            callable="myapp.handlers:handle_job_created",
            lazy_import=True,
        )

        for field in (
            "routing_key",
            "handler_key",
            "priority",
            "output_events",
            "callable",
            "lazy_import",
        ):
            assert not hasattr(entry, field)
