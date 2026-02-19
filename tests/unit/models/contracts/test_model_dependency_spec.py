# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Comprehensive unit tests for ModelDependencySpec.

Tests the ModelDependencySpec model which defines capability-based dependencies
for ONEX nodes. This enables auto-discovery and loose coupling between nodes
using the principle: "I'm interested in what you do, not what you are."

Test Categories:
1. Minimal Instantiation Tests - Required fields only
2. Full Instantiation Tests - All fields populated
3. Capability-Based Discovery Tests - Capability, intent_types, protocol
4. Selection Strategy Tests - Different selection strategies
5. Validation Tests - At least one discovery method required
6. Serialization Tests - model_dump/model_validate roundtrip
7. Edge Cases - Boundary conditions and special values
8. Error Handling Tests - Invalid inputs and error messages

See Also:
    - OMN-1123: ModelDependencySpec (Capability-Based Dependencies)
    - ONEX Four-Node Architecture documentation
"""

import pytest
from pydantic import ValidationError

from omnibase_core.models.contracts.model_dependency_spec import (
    ModelDependencySpec,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError

# =============================================================================
# SECTION 1: Minimal Instantiation Tests
# =============================================================================


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestModelDependencySpecMinimal:
    """Tests for minimal instantiation with required fields only."""

    def test_minimal_with_capability(self) -> None:
        """Test minimal instantiation with capability specified."""
        spec = ModelDependencySpec(
            name="event_bus",
            type="protocol",
            capability="event.publishing",
        )
        assert spec.name == "event_bus"
        assert spec.type == "protocol"
        assert spec.capability == "event.publishing"
        assert spec.intent_types is None
        assert spec.protocol is None
        assert spec.contract_type is None
        assert spec.state == "ACTIVE"
        assert spec.selection_strategy == "first"
        assert spec.fallback_module is None
        assert spec.description is None

    def test_minimal_with_intent_types(self) -> None:
        """Test minimal instantiation with intent_types specified."""
        spec = ModelDependencySpec(
            name="consul_service",
            type="handler",
            intent_types=["consul.register", "consul.deregister"],
        )
        assert spec.name == "consul_service"
        assert spec.type == "handler"
        assert spec.intent_types == ["consul.register", "consul.deregister"]
        assert spec.capability is None
        assert spec.protocol is None

    def test_minimal_with_protocol(self) -> None:
        """Test minimal instantiation with protocol specified."""
        spec = ModelDependencySpec(
            name="reducer_dep",
            type="node",
            protocol="ProtocolReducer",
        )
        assert spec.name == "reducer_dep"
        assert spec.type == "node"
        assert spec.protocol == "ProtocolReducer"
        assert spec.capability is None
        assert spec.intent_types is None

    def test_missing_name_fails(self) -> None:
        """Test that missing name field raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelDependencySpec(
                type="protocol",
                capability="event.publishing",
            )  # type: ignore[call-arg]
        assert "name" in str(exc_info.value).lower()

    def test_missing_type_fails(self) -> None:
        """Test that missing type field raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelDependencySpec(
                name="test_dep",
                capability="event.publishing",
            )  # type: ignore[call-arg]
        assert "type" in str(exc_info.value).lower()


# =============================================================================
# SECTION 2: Full Instantiation Tests
# =============================================================================


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestModelDependencySpecFull:
    """Tests for full instantiation with all fields populated."""

    def test_full_instantiation_with_capability(self) -> None:
        """Test full instantiation with capability and all optional fields."""
        spec = ModelDependencySpec(
            name="event_publisher",
            type="protocol",
            capability="event.publishing",
            contract_type="effect",
            state="ACTIVE",
            selection_strategy="round_robin",
            fallback_module="omnibase_core.events.default_publisher",
            description="Event publishing capability for node communication",
        )
        assert spec.name == "event_publisher"
        assert spec.type == "protocol"
        assert spec.capability == "event.publishing"
        assert spec.contract_type == "effect"
        assert spec.state == "ACTIVE"
        assert spec.selection_strategy == "round_robin"
        assert spec.fallback_module == "omnibase_core.events.default_publisher"
        assert spec.description == "Event publishing capability for node communication"

    def test_full_instantiation_with_intent_types(self) -> None:
        """Test full instantiation with intent_types and all optional fields."""
        spec = ModelDependencySpec(
            name="registration_handler",
            type="handler",
            intent_types=["service.register", "service.deregister", "service.update"],
            contract_type="reducer",
            state="ACTIVE",
            selection_strategy="least_loaded",
            fallback_module="omnibase_core.handlers.registration_fallback",
            description="Service registration handler for Consul",
        )
        assert spec.name == "registration_handler"
        assert spec.intent_types == [
            "service.register",
            "service.deregister",
            "service.update",
        ]
        assert spec.selection_strategy == "least_loaded"

    def test_full_instantiation_with_protocol(self) -> None:
        """Test full instantiation with protocol and all optional fields."""
        spec = ModelDependencySpec(
            name="compute_node",
            type="node",
            protocol="ProtocolCompute",
            contract_type="compute",
            state="ACTIVE",
            selection_strategy="random",
            fallback_module="omnibase_core.nodes.default_compute",
            description="Compute node for data transformation",
        )
        assert spec.name == "compute_node"
        assert spec.protocol == "ProtocolCompute"
        assert spec.selection_strategy == "random"


# =============================================================================
# SECTION 3: Capability-Based Discovery Tests
# =============================================================================


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestModelDependencySpecDiscovery:
    """Tests for capability-based discovery methods."""

    def test_capability_only(self) -> None:
        """Test dependency with only capability specified."""
        spec = ModelDependencySpec(
            name="logger",
            type="protocol",
            capability="logging.structured",
        )
        assert spec.capability == "logging.structured"
        assert spec.has_capability_filter()
        assert not spec.has_intent_filter()
        assert not spec.has_protocol_filter()

    def test_intent_types_only(self) -> None:
        """Test dependency with only intent_types specified."""
        spec = ModelDependencySpec(
            name="state_handler",
            type="handler",
            intent_types=["state.transition", "state.query"],
        )
        assert spec.intent_types == ["state.transition", "state.query"]
        assert not spec.has_capability_filter()
        assert spec.has_intent_filter()
        assert not spec.has_protocol_filter()

    def test_protocol_only(self) -> None:
        """Test dependency with only protocol specified."""
        spec = ModelDependencySpec(
            name="orchestrator",
            type="node",
            protocol="ProtocolOrchestrator",
        )
        assert spec.protocol == "ProtocolOrchestrator"
        assert not spec.has_capability_filter()
        assert not spec.has_intent_filter()
        assert spec.has_protocol_filter()

    def test_multiple_discovery_methods(self) -> None:
        """Test dependency with multiple discovery methods specified."""
        spec = ModelDependencySpec(
            name="multi_dep",
            type="node",
            capability="compute.transform",
            intent_types=["data.transform"],
            protocol="ProtocolCompute",
        )
        assert spec.capability == "compute.transform"
        assert spec.intent_types == ["data.transform"]
        assert spec.protocol == "ProtocolCompute"
        assert spec.has_capability_filter()
        assert spec.has_intent_filter()
        assert spec.has_protocol_filter()

    def test_empty_intent_types_list_fails(self) -> None:
        """Test that empty intent_types list with no other discovery fails."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelDependencySpec(
                name="empty_intents",
                type="handler",
                intent_types=[],
            )
        assert (
            "capability" in str(exc_info.value).lower()
            or "intent" in str(exc_info.value).lower()
        )


# =============================================================================
# SECTION 4: Selection Strategy Tests
# =============================================================================


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestModelDependencySpecSelectionStrategy:
    """Tests for selection strategy options."""

    @pytest.mark.parametrize(
        "strategy",
        ["first", "random", "round_robin", "least_loaded"],
    )
    def test_valid_selection_strategies(self, strategy: str) -> None:
        """Test that all valid selection strategies are accepted."""
        spec = ModelDependencySpec(
            name="test_dep",
            type="protocol",
            capability="test.capability",
            selection_strategy=strategy,  # type: ignore[arg-type]
        )
        assert spec.selection_strategy == strategy

    def test_default_selection_strategy(self) -> None:
        """Test that default selection strategy is 'first'."""
        spec = ModelDependencySpec(
            name="test_dep",
            type="protocol",
            capability="test.capability",
        )
        assert spec.selection_strategy == "first"

    def test_invalid_selection_strategy_fails(self) -> None:
        """Test that invalid selection strategy raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelDependencySpec(
                name="test_dep",
                type="protocol",
                capability="test.capability",
                selection_strategy="invalid_strategy",  # type: ignore[arg-type]
            )
        assert "selection_strategy" in str(exc_info.value).lower()


# =============================================================================
# SECTION 5: Validation Tests - At Least One Discovery Method Required
# =============================================================================


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestModelDependencySpecValidation:
    """Tests for validation - at least one discovery method required."""

    def test_no_discovery_method_fails(self) -> None:
        """Test that missing all discovery methods raises ModelOnexError."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelDependencySpec(
                name="no_discovery",
                type="protocol",
            )
        error_msg = str(exc_info.value).lower()
        assert (
            "capability" in error_msg
            or "intent" in error_msg
            or "protocol" in error_msg
        )

    def test_none_values_for_all_discovery_methods_fails(self) -> None:
        """Test that explicitly None values for all discovery methods fails."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelDependencySpec(
                name="all_none",
                type="protocol",
                capability=None,
                intent_types=None,
                protocol=None,
            )
        error_msg = str(exc_info.value).lower()
        assert (
            "capability" in error_msg
            or "intent" in error_msg
            or "protocol" in error_msg
        )

    def test_empty_string_capability_fails(self) -> None:
        """Test that empty string capability with no other discovery fails."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelDependencySpec(
                name="empty_cap",
                type="protocol",
                capability="",
            )
        error_msg = str(exc_info.value).lower()
        assert "capability" in error_msg or "empty" in error_msg

    def test_whitespace_capability_fails(self) -> None:
        """Test that whitespace-only capability with no other discovery fails."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelDependencySpec(
                name="whitespace_cap",
                type="protocol",
                capability="   ",
            )
        error_msg = str(exc_info.value).lower()
        assert "capability" in error_msg or "empty" in error_msg


# =============================================================================
# SECTION 6: Type Field Tests
# =============================================================================


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestModelDependencySpecType:
    """Tests for dependency type field."""

    @pytest.mark.parametrize(
        "dep_type",
        ["node", "protocol", "handler"],
    )
    def test_valid_dependency_types(self, dep_type: str) -> None:
        """Test that all valid dependency types are accepted."""
        spec = ModelDependencySpec(
            name="test_dep",
            type=dep_type,  # type: ignore[arg-type]
            capability="test.capability",
        )
        assert spec.type == dep_type

    def test_invalid_dependency_type_fails(self) -> None:
        """Test that invalid dependency type raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelDependencySpec(
                name="test_dep",
                type="invalid_type",  # type: ignore[arg-type]
                capability="test.capability",
            )
        assert "type" in str(exc_info.value).lower()


# =============================================================================
# SECTION 7: Contract Type Filter Tests
# =============================================================================


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestModelDependencySpecContractType:
    """Tests for contract_type filter field."""

    @pytest.mark.parametrize(
        "contract_type",
        ["effect", "compute", "reducer", "orchestrator"],
    )
    def test_valid_contract_types(self, contract_type: str) -> None:
        """Test that all valid contract types are accepted."""
        spec = ModelDependencySpec(
            name="test_dep",
            type="node",
            capability="test.capability",
            contract_type=contract_type,
        )
        assert spec.contract_type == contract_type

    def test_contract_type_optional(self) -> None:
        """Test that contract_type is optional."""
        spec = ModelDependencySpec(
            name="test_dep",
            type="node",
            capability="test.capability",
        )
        assert spec.contract_type is None


# =============================================================================
# SECTION 8: State Filter Tests
# =============================================================================


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestModelDependencySpecState:
    """Tests for state filter field."""

    def test_default_state_is_active(self) -> None:
        """Test that default state is 'ACTIVE'."""
        spec = ModelDependencySpec(
            name="test_dep",
            type="protocol",
            capability="test.capability",
        )
        assert spec.state == "ACTIVE"

    def test_custom_state(self) -> None:
        """Test that custom state can be specified."""
        spec = ModelDependencySpec(
            name="test_dep",
            type="protocol",
            capability="test.capability",
            state="DEPRECATED",
        )
        assert spec.state == "DEPRECATED"


# =============================================================================
# SECTION 9: Fallback Module Tests
# =============================================================================


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestModelDependencySpecFallback:
    """Tests for fallback_module field."""

    def test_fallback_module_optional(self) -> None:
        """Test that fallback_module is optional."""
        spec = ModelDependencySpec(
            name="test_dep",
            type="protocol",
            capability="test.capability",
        )
        assert spec.fallback_module is None

    def test_fallback_module_specified(self) -> None:
        """Test that fallback_module can be specified."""
        spec = ModelDependencySpec(
            name="test_dep",
            type="protocol",
            capability="test.capability",
            fallback_module="omnibase_core.fallback.default_service",
        )
        assert spec.fallback_module == "omnibase_core.fallback.default_service"


# =============================================================================
# SECTION 10: Serialization Tests
# =============================================================================


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestModelDependencySpecSerialization:
    """Tests for serialization and deserialization."""

    def test_model_dump_minimal(self) -> None:
        """Test model_dump with minimal instantiation."""
        spec = ModelDependencySpec(
            name="test_dep",
            type="protocol",
            capability="test.capability",
        )
        dumped = spec.model_dump()
        assert dumped["name"] == "test_dep"
        assert dumped["type"] == "protocol"
        assert dumped["capability"] == "test.capability"
        assert dumped["selection_strategy"] == "first"
        assert dumped["state"] == "ACTIVE"

    def test_model_dump_full(self) -> None:
        """Test model_dump with all fields."""
        spec = ModelDependencySpec(
            name="full_dep",
            type="handler",
            capability="full.capability",
            intent_types=["full.intent"],
            protocol="FullProtocol",
            contract_type="reducer",
            state="ACTIVE",
            selection_strategy="round_robin",
            fallback_module="omnibase.fallback",
            description="Full description",
        )
        dumped = spec.model_dump()
        assert dumped["name"] == "full_dep"
        assert dumped["intent_types"] == ["full.intent"]
        assert dumped["protocol"] == "FullProtocol"
        assert dumped["contract_type"] == "reducer"
        assert dumped["selection_strategy"] == "round_robin"
        assert dumped["fallback_module"] == "omnibase.fallback"
        assert dumped["description"] == "Full description"

    def test_model_validate_from_dict(self) -> None:
        """Test model_validate from dictionary."""
        data = {
            "name": "validated_dep",
            "type": "node",
            "capability": "validated.capability",
            "selection_strategy": "random",
        }
        spec = ModelDependencySpec.model_validate(data)
        assert spec.name == "validated_dep"
        assert spec.type == "node"
        assert spec.capability == "validated.capability"
        assert spec.selection_strategy == "random"

    def test_roundtrip_serialization(self) -> None:
        """Test roundtrip serialization."""
        original = ModelDependencySpec(
            name="roundtrip_dep",
            type="handler",
            intent_types=["roundtrip.intent"],
            contract_type="effect",
            selection_strategy="least_loaded",
            description="Roundtrip test",
        )
        dumped = original.model_dump()
        restored = ModelDependencySpec.model_validate(dumped)
        assert restored.name == original.name
        assert restored.type == original.type
        assert restored.intent_types == original.intent_types
        assert restored.contract_type == original.contract_type
        assert restored.selection_strategy == original.selection_strategy
        assert restored.description == original.description

    def test_model_dump_json_mode(self) -> None:
        """Test model_dump with mode='json' for JSON-compatible output."""
        spec = ModelDependencySpec(
            name="json_dep",
            type="protocol",
            capability="json.capability",
        )
        dumped = spec.model_dump(mode="json")
        import json

        json_str = json.dumps(dumped)
        assert json_str is not None


# =============================================================================
# SECTION 11: Edge Cases
# =============================================================================


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestModelDependencySpecEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_single_char_name_valid(self) -> None:
        """Test that single character name is valid."""
        spec = ModelDependencySpec(
            name="x",
            type="protocol",
            capability="test.capability",
        )
        assert spec.name == "x"

    def test_long_name_valid(self) -> None:
        """Test that long name is valid."""
        long_name = "a" * 200
        spec = ModelDependencySpec(
            name=long_name,
            type="protocol",
            capability="test.capability",
        )
        assert spec.name == long_name

    def test_name_with_dots_valid(self) -> None:
        """Test name with dots (module-like naming)."""
        spec = ModelDependencySpec(
            name="omnibase.services.event_bus",
            type="protocol",
            capability="test.capability",
        )
        assert spec.name == "omnibase.services.event_bus"

    def test_capability_with_deep_nesting(self) -> None:
        """Test capability with deep nesting."""
        spec = ModelDependencySpec(
            name="nested_dep",
            type="protocol",
            capability="level1.level2.level3.level4.capability",
        )
        assert spec.capability == "level1.level2.level3.level4.capability"

    def test_many_intent_types(self) -> None:
        """Test with many intent types."""
        intents = [f"intent.type.{i}" for i in range(50)]
        spec = ModelDependencySpec(
            name="many_intents",
            type="handler",
            intent_types=intents,
        )
        assert len(spec.intent_types or []) == 50


# =============================================================================
# SECTION 12: Model Configuration Tests
# =============================================================================


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestModelDependencySpecModelConfig:
    """Tests for model configuration settings."""

    def test_extra_fields_forbidden(self) -> None:
        """Test that extra fields are forbidden (extra='forbid')."""
        with pytest.raises(ValidationError) as exc_info:
            ModelDependencySpec.model_validate(
                {
                    "name": "test",
                    "type": "protocol",
                    "capability": "test.capability",
                    "unknown_field": "should_fail",
                }
            )
        assert (
            "unknown_field" in str(exc_info.value).lower()
            or "extra" in str(exc_info.value).lower()
        )


# =============================================================================
# SECTION 13: Export and Import Tests
# =============================================================================


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestModelDependencySpecExports:
    """Tests for module exports."""

    def test_import_from_contracts_package(self) -> None:
        """Test that model can be imported from contracts package."""
        from omnibase_core.models.contracts import ModelDependencySpec

        spec = ModelDependencySpec(
            name="test",
            type="protocol",
            capability="test.capability",
        )
        assert spec.name == "test"

    def test_model_in_all_exports(self) -> None:
        """Test that ModelDependencySpec is in __all__."""
        from omnibase_core.models.contracts import __all__

        assert "ModelDependencySpec" in __all__


# =============================================================================
# SECTION 14: Helper Method Tests
# =============================================================================


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestModelDependencySpecHelperMethods:
    """Tests for helper methods."""

    def test_has_capability_filter_true(self) -> None:
        """Test has_capability_filter returns True when capability set."""
        spec = ModelDependencySpec(
            name="test",
            type="protocol",
            capability="test.capability",
        )
        assert spec.has_capability_filter() is True

    def test_has_capability_filter_false(self) -> None:
        """Test has_capability_filter returns False when capability not set."""
        spec = ModelDependencySpec(
            name="test",
            type="protocol",
            protocol="TestProtocol",
        )
        assert spec.has_capability_filter() is False

    def test_has_intent_filter_true(self) -> None:
        """Test has_intent_filter returns True when intent_types set."""
        spec = ModelDependencySpec(
            name="test",
            type="handler",
            intent_types=["test.intent"],
        )
        assert spec.has_intent_filter() is True

    def test_has_intent_filter_false(self) -> None:
        """Test has_intent_filter returns False when intent_types not set."""
        spec = ModelDependencySpec(
            name="test",
            type="protocol",
            capability="test.capability",
        )
        assert spec.has_intent_filter() is False

    def test_has_protocol_filter_true(self) -> None:
        """Test has_protocol_filter returns True when protocol set."""
        spec = ModelDependencySpec(
            name="test",
            type="node",
            protocol="TestProtocol",
        )
        assert spec.has_protocol_filter() is True

    def test_has_protocol_filter_false(self) -> None:
        """Test has_protocol_filter returns False when protocol not set."""
        spec = ModelDependencySpec(
            name="test",
            type="protocol",
            capability="test.capability",
        )
        assert spec.has_protocol_filter() is False

    def test_get_discovery_methods_single(self) -> None:
        """Test get_discovery_methods returns single method."""
        spec = ModelDependencySpec(
            name="test",
            type="protocol",
            capability="test.capability",
        )
        methods = spec.get_discovery_methods()
        assert "capability" in methods
        assert len(methods) == 1

    def test_get_discovery_methods_multiple(self) -> None:
        """Test get_discovery_methods returns multiple methods."""
        spec = ModelDependencySpec(
            name="test",
            type="node",
            capability="test.capability",
            intent_types=["test.intent"],
            protocol="TestProtocol",
        )
        methods = spec.get_discovery_methods()
        assert "capability" in methods
        assert "intent_types" in methods
        assert "protocol" in methods
        assert len(methods) == 3
