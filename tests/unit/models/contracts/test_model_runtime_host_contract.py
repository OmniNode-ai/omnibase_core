"""
Comprehensive TDD unit tests for RuntimeHostContract models.

Tests the four models that comprise the RuntimeHostContract:
1. ModelRuntimeHandlerConfig - handler type configuration
2. ModelRuntimeEventBusConfig - event bus configuration (kind only)
3. ModelNodeRef - node reference (slug only)
4. ModelRuntimeHostContract - main contract with from_yaml()

Test Categories:
1. Basic Construction Tests
2. Field Validation Tests
3. Serialization Tests
4. YAML Loading Tests (ModelRuntimeHostContract)
5. Edge Cases
6. Error Handling Tests

Requirements from OMN-225:
- All models use extra='forbid' configuration
- Handler configs use EnumHandlerType for type classification
- Event bus and node refs use min_length=1 validation
- from_yaml() provides YAML contract loading with proper error handling
"""

from pathlib import Path

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_handler_type import EnumHandlerType
from omnibase_core.models.contracts.model_node_ref import ModelNodeRef
from omnibase_core.models.contracts.model_runtime_event_bus_config import (
    ModelRuntimeEventBusConfig,
)
from omnibase_core.models.contracts.model_runtime_handler_config import (
    ModelRuntimeHandlerConfig,
)
from omnibase_core.models.contracts.model_runtime_host_contract import (
    ModelRuntimeHostContract,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError

# =============================================================================
# ModelRuntimeHandlerConfig Tests
# =============================================================================


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestModelRuntimeHandlerConfigBasicConstruction:
    """Tests for ModelRuntimeHandlerConfig basic construction and initialization."""

    def test_create_with_valid_handler_type_http(self) -> None:
        """Test creating ModelRuntimeHandlerConfig with HTTP handler type."""
        config = ModelRuntimeHandlerConfig(handler_type=EnumHandlerType.HTTP)
        assert config.handler_type == EnumHandlerType.HTTP

    def test_create_with_valid_handler_type_database(self) -> None:
        """Test creating ModelRuntimeHandlerConfig with DATABASE handler type."""
        config = ModelRuntimeHandlerConfig(handler_type=EnumHandlerType.DATABASE)
        assert config.handler_type == EnumHandlerType.DATABASE

    def test_create_with_valid_handler_type_kafka(self) -> None:
        """Test creating ModelRuntimeHandlerConfig with KAFKA handler type."""
        config = ModelRuntimeHandlerConfig(handler_type=EnumHandlerType.KAFKA)
        assert config.handler_type == EnumHandlerType.KAFKA

    def test_create_with_valid_handler_type_filesystem(self) -> None:
        """Test creating ModelRuntimeHandlerConfig with FILESYSTEM handler type."""
        config = ModelRuntimeHandlerConfig(handler_type=EnumHandlerType.FILESYSTEM)
        assert config.handler_type == EnumHandlerType.FILESYSTEM

    def test_create_with_valid_handler_type_vault(self) -> None:
        """Test creating ModelRuntimeHandlerConfig with VAULT handler type."""
        config = ModelRuntimeHandlerConfig(handler_type=EnumHandlerType.VAULT)
        assert config.handler_type == EnumHandlerType.VAULT

    def test_create_with_valid_handler_type_vector_store(self) -> None:
        """Test creating ModelRuntimeHandlerConfig with VECTOR_STORE handler type."""
        config = ModelRuntimeHandlerConfig(handler_type=EnumHandlerType.VECTOR_STORE)
        assert config.handler_type == EnumHandlerType.VECTOR_STORE

    def test_create_with_valid_handler_type_graph_database(self) -> None:
        """Test creating ModelRuntimeHandlerConfig with GRAPH_DATABASE handler type."""
        config = ModelRuntimeHandlerConfig(handler_type=EnumHandlerType.GRAPH_DATABASE)
        assert config.handler_type == EnumHandlerType.GRAPH_DATABASE

    def test_create_with_valid_handler_type_redis(self) -> None:
        """Test creating ModelRuntimeHandlerConfig with REDIS handler type."""
        config = ModelRuntimeHandlerConfig(handler_type=EnumHandlerType.REDIS)
        assert config.handler_type == EnumHandlerType.REDIS

    def test_create_with_valid_handler_type_event_bus(self) -> None:
        """Test creating ModelRuntimeHandlerConfig with EVENT_BUS handler type."""
        config = ModelRuntimeHandlerConfig(handler_type=EnumHandlerType.EVENT_BUS)
        assert config.handler_type == EnumHandlerType.EVENT_BUS

    def test_create_with_abstract_type_extension(self) -> None:
        """Test creating ModelRuntimeHandlerConfig with EXTENSION abstract type."""
        config = ModelRuntimeHandlerConfig(handler_type=EnumHandlerType.EXTENSION)
        assert config.handler_type == EnumHandlerType.EXTENSION

    def test_create_with_abstract_type_special(self) -> None:
        """Test creating ModelRuntimeHandlerConfig with SPECIAL abstract type."""
        config = ModelRuntimeHandlerConfig(handler_type=EnumHandlerType.SPECIAL)
        assert config.handler_type == EnumHandlerType.SPECIAL

    def test_create_with_abstract_type_named(self) -> None:
        """Test creating ModelRuntimeHandlerConfig with NAMED abstract type."""
        config = ModelRuntimeHandlerConfig(handler_type=EnumHandlerType.NAMED)
        assert config.handler_type == EnumHandlerType.NAMED


@pytest.mark.unit
class TestModelRuntimeHandlerConfigAllHandlerTypes:
    """Tests to ensure all EnumHandlerType values work with ModelRuntimeHandlerConfig."""

    def test_all_handler_types_valid(self) -> None:
        """Test all EnumHandlerType values are valid for ModelRuntimeHandlerConfig."""
        for handler_type in EnumHandlerType:
            config = ModelRuntimeHandlerConfig(handler_type=handler_type)
            assert config.handler_type == handler_type

    def test_handler_type_count_matches_enum(self) -> None:
        """Test that we're testing all handler types."""
        expected_types = [
            EnumHandlerType.EXTENSION,
            EnumHandlerType.SPECIAL,
            EnumHandlerType.NAMED,
            EnumHandlerType.HTTP,
            EnumHandlerType.DATABASE,
            EnumHandlerType.KAFKA,
            EnumHandlerType.FILESYSTEM,
            EnumHandlerType.VAULT,
            EnumHandlerType.VECTOR_STORE,
            EnumHandlerType.GRAPH_DATABASE,
            EnumHandlerType.REDIS,
            EnumHandlerType.EVENT_BUS,
        ]
        assert len(list(EnumHandlerType)) == len(expected_types)


@pytest.mark.unit
class TestModelRuntimeHandlerConfigValidation:
    """Tests for ModelRuntimeHandlerConfig field validation."""

    def test_handler_type_is_required(self) -> None:
        """Test that handler_type is a required field."""
        with pytest.raises(ValidationError) as exc_info:
            ModelRuntimeHandlerConfig()  # type: ignore[call-arg]
        assert "handler_type" in str(exc_info.value)

    def test_extra_fields_forbidden(self) -> None:
        """Test extra fields are rejected (extra='forbid')."""
        with pytest.raises(ValidationError) as exc_info:
            ModelRuntimeHandlerConfig(
                handler_type=EnumHandlerType.HTTP,
                extra_field="not allowed",  # type: ignore[call-arg]
            )
        assert (
            "extra_field" in str(exc_info.value).lower()
            or "extra" in str(exc_info.value).lower()
        )

    def test_invalid_handler_type_string_rejected(self) -> None:
        """Test invalid string handler type is rejected."""
        with pytest.raises(ValidationError):
            ModelRuntimeHandlerConfig(handler_type="invalid_type")  # type: ignore[arg-type]

    def test_none_handler_type_rejected(self) -> None:
        """Test None handler type is rejected."""
        with pytest.raises(ValidationError):
            ModelRuntimeHandlerConfig(handler_type=None)  # type: ignore[arg-type]

    def test_integer_handler_type_rejected(self) -> None:
        """Test integer handler type is rejected."""
        with pytest.raises(ValidationError):
            ModelRuntimeHandlerConfig(handler_type=123)  # type: ignore[arg-type]


@pytest.mark.unit
class TestModelRuntimeHandlerConfigSerialization:
    """Tests for ModelRuntimeHandlerConfig serialization."""

    def test_model_dump_returns_dict(self) -> None:
        """Test model_dump() returns a dictionary with handler_type."""
        config = ModelRuntimeHandlerConfig(handler_type=EnumHandlerType.HTTP)
        dumped = config.model_dump()
        assert isinstance(dumped, dict)
        assert "handler_type" in dumped
        assert dumped["handler_type"] == EnumHandlerType.HTTP

    def test_model_dump_json_returns_string(self) -> None:
        """Test model_dump_json() returns a JSON string."""
        config = ModelRuntimeHandlerConfig(handler_type=EnumHandlerType.HTTP)
        json_str = config.model_dump_json()
        assert isinstance(json_str, str)
        assert "handler_type" in json_str

    def test_model_validate_from_dict(self) -> None:
        """Test model_validate() creates config from dictionary."""
        data = {"handler_type": "http"}
        config = ModelRuntimeHandlerConfig.model_validate(data)
        assert config.handler_type == EnumHandlerType.HTTP

    def test_roundtrip_serialization(self) -> None:
        """Test roundtrip serialization preserves values."""
        original = ModelRuntimeHandlerConfig(handler_type=EnumHandlerType.KAFKA)
        dumped = original.model_dump()
        restored = ModelRuntimeHandlerConfig.model_validate(dumped)
        assert original.handler_type == restored.handler_type


# =============================================================================
# ModelRuntimeEventBusConfig Tests
# =============================================================================


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestModelRuntimeEventBusConfigBasicConstruction:
    """Tests for ModelRuntimeEventBusConfig basic construction and initialization."""

    def test_create_with_valid_kind_kafka(self) -> None:
        """Test creating ModelRuntimeEventBusConfig with 'kafka' kind."""
        config = ModelRuntimeEventBusConfig(kind="kafka")
        assert config.kind == "kafka"

    def test_create_with_valid_kind_local(self) -> None:
        """Test creating ModelRuntimeEventBusConfig with 'local' kind."""
        config = ModelRuntimeEventBusConfig(kind="local")
        assert config.kind == "local"

    def test_create_with_valid_kind_redis(self) -> None:
        """Test creating ModelRuntimeEventBusConfig with 'redis' kind."""
        config = ModelRuntimeEventBusConfig(kind="redis")
        assert config.kind == "redis"

    def test_create_with_custom_kind(self) -> None:
        """Test creating ModelRuntimeEventBusConfig with custom kind string."""
        config = ModelRuntimeEventBusConfig(kind="custom_event_bus")
        assert config.kind == "custom_event_bus"

    def test_create_with_single_character_kind(self) -> None:
        """Test creating ModelRuntimeEventBusConfig with single character kind."""
        config = ModelRuntimeEventBusConfig(kind="x")
        assert config.kind == "x"


@pytest.mark.unit
class TestModelRuntimeEventBusConfigValidation:
    """Tests for ModelRuntimeEventBusConfig field validation."""

    def test_kind_is_required(self) -> None:
        """Test that kind is a required field."""
        with pytest.raises(ValidationError) as exc_info:
            ModelRuntimeEventBusConfig()  # type: ignore[call-arg]
        assert "kind" in str(exc_info.value)

    def test_empty_string_kind_rejected(self) -> None:
        """Test empty string kind is rejected (min_length=1)."""
        with pytest.raises(ValidationError) as exc_info:
            ModelRuntimeEventBusConfig(kind="")
        assert "kind" in str(exc_info.value).lower()

    def test_extra_fields_forbidden(self) -> None:
        """Test extra fields are rejected (extra='forbid')."""
        with pytest.raises(ValidationError) as exc_info:
            ModelRuntimeEventBusConfig(
                kind="kafka",
                extra_field="not allowed",  # type: ignore[call-arg]
            )
        assert (
            "extra_field" in str(exc_info.value).lower()
            or "extra" in str(exc_info.value).lower()
        )

    def test_none_kind_rejected(self) -> None:
        """Test None kind is rejected."""
        with pytest.raises(ValidationError):
            ModelRuntimeEventBusConfig(kind=None)  # type: ignore[arg-type]

    def test_integer_kind_rejected(self) -> None:
        """Test integer kind is rejected."""
        with pytest.raises(ValidationError):
            ModelRuntimeEventBusConfig(kind=123)  # type: ignore[arg-type]


@pytest.mark.unit
class TestModelRuntimeEventBusConfigSerialization:
    """Tests for ModelRuntimeEventBusConfig serialization."""

    def test_model_dump_returns_dict(self) -> None:
        """Test model_dump() returns a dictionary with kind."""
        config = ModelRuntimeEventBusConfig(kind="kafka")
        dumped = config.model_dump()
        assert isinstance(dumped, dict)
        assert dumped["kind"] == "kafka"

    def test_model_dump_json_returns_string(self) -> None:
        """Test model_dump_json() returns a JSON string."""
        config = ModelRuntimeEventBusConfig(kind="kafka")
        json_str = config.model_dump_json()
        assert isinstance(json_str, str)
        assert "kafka" in json_str

    def test_model_validate_from_dict(self) -> None:
        """Test model_validate() creates config from dictionary."""
        data = {"kind": "redis"}
        config = ModelRuntimeEventBusConfig.model_validate(data)
        assert config.kind == "redis"

    def test_roundtrip_serialization(self) -> None:
        """Test roundtrip serialization preserves values."""
        original = ModelRuntimeEventBusConfig(kind="local")
        dumped = original.model_dump()
        restored = ModelRuntimeEventBusConfig.model_validate(dumped)
        assert original.kind == restored.kind


# =============================================================================
# ModelNodeRef Tests
# =============================================================================


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestModelNodeRefBasicConstruction:
    """Tests for ModelNodeRef basic construction and initialization."""

    def test_create_with_valid_slug(self) -> None:
        """Test creating ModelNodeRef with valid slug."""
        ref = ModelNodeRef(slug="my-node")
        assert ref.slug == "my-node"

    def test_create_with_compute_node_slug(self) -> None:
        """Test creating ModelNodeRef with compute node naming pattern."""
        ref = ModelNodeRef(slug="node-compute-transformer")
        assert ref.slug == "node-compute-transformer"

    def test_create_with_effect_node_slug(self) -> None:
        """Test creating ModelNodeRef with effect node naming pattern."""
        ref = ModelNodeRef(slug="node-effect-http-client")
        assert ref.slug == "node-effect-http-client"

    def test_create_with_reducer_node_slug(self) -> None:
        """Test creating ModelNodeRef with reducer node naming pattern."""
        ref = ModelNodeRef(slug="node-reducer-aggregator")
        assert ref.slug == "node-reducer-aggregator"

    def test_create_with_orchestrator_node_slug(self) -> None:
        """Test creating ModelNodeRef with orchestrator node naming pattern."""
        ref = ModelNodeRef(slug="node-orchestrator-workflow")
        assert ref.slug == "node-orchestrator-workflow"

    def test_create_with_single_character_slug(self) -> None:
        """Test creating ModelNodeRef with single character slug."""
        ref = ModelNodeRef(slug="x")
        assert ref.slug == "x"

    def test_create_with_underscore_slug(self) -> None:
        """Test creating ModelNodeRef with underscore slug."""
        ref = ModelNodeRef(slug="my_node_name")
        assert ref.slug == "my_node_name"

    def test_create_with_numeric_slug(self) -> None:
        """Test creating ModelNodeRef with numeric characters in slug."""
        ref = ModelNodeRef(slug="node-v2-123")
        assert ref.slug == "node-v2-123"


@pytest.mark.unit
class TestModelNodeRefValidation:
    """Tests for ModelNodeRef field validation."""

    def test_slug_is_required(self) -> None:
        """Test that slug is a required field."""
        with pytest.raises(ValidationError) as exc_info:
            ModelNodeRef()  # type: ignore[call-arg]
        assert "slug" in str(exc_info.value)

    def test_empty_string_slug_rejected(self) -> None:
        """Test empty string slug is rejected (min_length=1)."""
        with pytest.raises(ValidationError) as exc_info:
            ModelNodeRef(slug="")
        assert "slug" in str(exc_info.value).lower()

    def test_extra_fields_forbidden(self) -> None:
        """Test extra fields are rejected (extra='forbid')."""
        with pytest.raises(ValidationError) as exc_info:
            ModelNodeRef(
                slug="my-node",
                extra_field="not allowed",  # type: ignore[call-arg]
            )
        assert (
            "extra_field" in str(exc_info.value).lower()
            or "extra" in str(exc_info.value).lower()
        )

    def test_none_slug_rejected(self) -> None:
        """Test None slug is rejected."""
        with pytest.raises(ValidationError):
            ModelNodeRef(slug=None)  # type: ignore[arg-type]

    def test_integer_slug_rejected(self) -> None:
        """Test integer slug is rejected."""
        with pytest.raises(ValidationError):
            ModelNodeRef(slug=123)  # type: ignore[arg-type]


@pytest.mark.unit
class TestModelNodeRefSerialization:
    """Tests for ModelNodeRef serialization."""

    def test_model_dump_returns_dict(self) -> None:
        """Test model_dump() returns a dictionary with slug."""
        ref = ModelNodeRef(slug="my-node")
        dumped = ref.model_dump()
        assert isinstance(dumped, dict)
        assert dumped["slug"] == "my-node"

    def test_model_dump_json_returns_string(self) -> None:
        """Test model_dump_json() returns a JSON string."""
        ref = ModelNodeRef(slug="my-node")
        json_str = ref.model_dump_json()
        assert isinstance(json_str, str)
        assert "my-node" in json_str

    def test_model_validate_from_dict(self) -> None:
        """Test model_validate() creates ref from dictionary."""
        data = {"slug": "test-node"}
        ref = ModelNodeRef.model_validate(data)
        assert ref.slug == "test-node"

    def test_roundtrip_serialization(self) -> None:
        """Test roundtrip serialization preserves values."""
        original = ModelNodeRef(slug="node-compute-transformer")
        dumped = original.model_dump()
        restored = ModelNodeRef.model_validate(dumped)
        assert original.slug == restored.slug


# =============================================================================
# ModelRuntimeHostContract Tests
# =============================================================================


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestModelRuntimeHostContractBasicConstruction:
    """Tests for ModelRuntimeHostContract basic construction and initialization."""

    def test_create_with_all_required_fields(self) -> None:
        """Test creating ModelRuntimeHostContract with all required fields."""
        contract = ModelRuntimeHostContract(
            handlers=[ModelRuntimeHandlerConfig(handler_type=EnumHandlerType.HTTP)],
            event_bus=ModelRuntimeEventBusConfig(kind="kafka"),
            nodes=[ModelNodeRef(slug="my-node")],
        )
        assert len(contract.handlers) == 1
        assert contract.event_bus.kind == "kafka"
        assert len(contract.nodes) == 1

    def test_create_with_only_event_bus(self) -> None:
        """Test creating ModelRuntimeHostContract with only event_bus (defaults for others)."""
        contract = ModelRuntimeHostContract(
            event_bus=ModelRuntimeEventBusConfig(kind="local"),
        )
        assert contract.event_bus.kind == "local"
        assert contract.handlers == []
        assert contract.nodes == []

    def test_handlers_default_to_empty_list(self) -> None:
        """Test that handlers defaults to empty list."""
        contract = ModelRuntimeHostContract(
            event_bus=ModelRuntimeEventBusConfig(kind="kafka"),
        )
        assert contract.handlers == []
        assert isinstance(contract.handlers, list)

    def test_nodes_default_to_empty_list(self) -> None:
        """Test that nodes defaults to empty list."""
        contract = ModelRuntimeHostContract(
            event_bus=ModelRuntimeEventBusConfig(kind="kafka"),
        )
        assert contract.nodes == []
        assert isinstance(contract.nodes, list)

    def test_create_with_multiple_handlers(self) -> None:
        """Test creating ModelRuntimeHostContract with multiple handlers."""
        contract = ModelRuntimeHostContract(
            handlers=[
                ModelRuntimeHandlerConfig(handler_type=EnumHandlerType.HTTP),
                ModelRuntimeHandlerConfig(handler_type=EnumHandlerType.DATABASE),
                ModelRuntimeHandlerConfig(handler_type=EnumHandlerType.KAFKA),
            ],
            event_bus=ModelRuntimeEventBusConfig(kind="kafka"),
        )
        assert len(contract.handlers) == 3
        assert contract.handlers[0].handler_type == EnumHandlerType.HTTP
        assert contract.handlers[1].handler_type == EnumHandlerType.DATABASE
        assert contract.handlers[2].handler_type == EnumHandlerType.KAFKA

    def test_create_with_multiple_nodes(self) -> None:
        """Test creating ModelRuntimeHostContract with multiple nodes."""
        contract = ModelRuntimeHostContract(
            event_bus=ModelRuntimeEventBusConfig(kind="kafka"),
            nodes=[
                ModelNodeRef(slug="node-compute-a"),
                ModelNodeRef(slug="node-effect-b"),
                ModelNodeRef(slug="node-reducer-c"),
            ],
        )
        assert len(contract.nodes) == 3
        assert contract.nodes[0].slug == "node-compute-a"
        assert contract.nodes[1].slug == "node-effect-b"
        assert contract.nodes[2].slug == "node-reducer-c"


@pytest.mark.unit
class TestModelRuntimeHostContractValidation:
    """Tests for ModelRuntimeHostContract field validation."""

    def test_event_bus_is_required(self) -> None:
        """Test that event_bus is a required field."""
        with pytest.raises(ValidationError) as exc_info:
            ModelRuntimeHostContract()  # type: ignore[call-arg]
        assert "event_bus" in str(exc_info.value)

    def test_extra_fields_forbidden(self) -> None:
        """Test extra fields are rejected (extra='forbid')."""
        with pytest.raises(ValidationError) as exc_info:
            ModelRuntimeHostContract(
                event_bus=ModelRuntimeEventBusConfig(kind="kafka"),
                extra_field="not allowed",  # type: ignore[call-arg]
            )
        assert (
            "extra_field" in str(exc_info.value).lower()
            or "extra" in str(exc_info.value).lower()
        )

    def test_invalid_handler_in_list_rejected(self) -> None:
        """Test invalid handler in handlers list is rejected."""
        with pytest.raises(ValidationError):
            ModelRuntimeHostContract(
                handlers=[{"invalid": "handler"}],  # type: ignore[list-item]
                event_bus=ModelRuntimeEventBusConfig(kind="kafka"),
            )

    def test_invalid_node_in_list_rejected(self) -> None:
        """Test invalid node in nodes list is rejected."""
        with pytest.raises(ValidationError):
            ModelRuntimeHostContract(
                event_bus=ModelRuntimeEventBusConfig(kind="kafka"),
                nodes=[{"invalid": "node"}],  # type: ignore[list-item]
            )


@pytest.mark.unit
class TestModelRuntimeHostContractSerialization:
    """Tests for ModelRuntimeHostContract serialization."""

    def test_model_dump_returns_dict(self) -> None:
        """Test model_dump() returns a dictionary with all fields."""
        contract = ModelRuntimeHostContract(
            handlers=[ModelRuntimeHandlerConfig(handler_type=EnumHandlerType.HTTP)],
            event_bus=ModelRuntimeEventBusConfig(kind="kafka"),
            nodes=[ModelNodeRef(slug="my-node")],
        )
        dumped = contract.model_dump()
        assert isinstance(dumped, dict)
        assert "handlers" in dumped
        assert "event_bus" in dumped
        assert "nodes" in dumped

    def test_model_dump_json_returns_string(self) -> None:
        """Test model_dump_json() returns a JSON string."""
        contract = ModelRuntimeHostContract(
            event_bus=ModelRuntimeEventBusConfig(kind="kafka"),
        )
        json_str = contract.model_dump_json()
        assert isinstance(json_str, str)
        assert "kafka" in json_str

    def test_model_validate_from_dict(self) -> None:
        """Test model_validate() creates contract from dictionary."""
        data = {
            "handlers": [{"handler_type": "http"}],
            "event_bus": {"kind": "kafka"},
            "nodes": [{"slug": "test-node"}],
        }
        contract = ModelRuntimeHostContract.model_validate(data)
        assert len(contract.handlers) == 1
        assert contract.handlers[0].handler_type == EnumHandlerType.HTTP
        assert contract.event_bus.kind == "kafka"
        assert len(contract.nodes) == 1
        assert contract.nodes[0].slug == "test-node"

    def test_roundtrip_serialization(self) -> None:
        """Test roundtrip serialization preserves values."""
        original = ModelRuntimeHostContract(
            handlers=[
                ModelRuntimeHandlerConfig(handler_type=EnumHandlerType.HTTP),
                ModelRuntimeHandlerConfig(handler_type=EnumHandlerType.KAFKA),
            ],
            event_bus=ModelRuntimeEventBusConfig(kind="redis"),
            nodes=[
                ModelNodeRef(slug="node-a"),
                ModelNodeRef(slug="node-b"),
            ],
        )
        dumped = original.model_dump()
        restored = ModelRuntimeHostContract.model_validate(dumped)
        assert len(original.handlers) == len(restored.handlers)
        assert original.event_bus.kind == restored.event_bus.kind
        assert len(original.nodes) == len(restored.nodes)


# =============================================================================
# ModelRuntimeHostContract YAML Loading Tests
# =============================================================================


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestModelRuntimeHostContractYamlLoading:
    """Tests for from_yaml() functionality."""

    def test_from_yaml_valid_file(self, tmp_path: Path) -> None:
        """Test from_yaml() with valid YAML file."""
        yaml_content = """
handlers:
  - handler_type: http
  - handler_type: kafka
event_bus:
  kind: kafka
nodes:
  - slug: my-node
"""
        yaml_file = tmp_path / "contract.yaml"
        yaml_file.write_text(yaml_content)

        contract = ModelRuntimeHostContract.from_yaml(yaml_file)
        assert len(contract.handlers) == 2
        assert contract.handlers[0].handler_type == EnumHandlerType.HTTP
        assert contract.handlers[1].handler_type == EnumHandlerType.KAFKA
        assert contract.event_bus.kind == "kafka"
        assert len(contract.nodes) == 1
        assert contract.nodes[0].slug == "my-node"

    def test_from_yaml_minimal_valid_file(self, tmp_path: Path) -> None:
        """Test from_yaml() with minimal valid YAML file (only required fields)."""
        yaml_content = """
event_bus:
  kind: local
"""
        yaml_file = tmp_path / "minimal_contract.yaml"
        yaml_file.write_text(yaml_content)

        contract = ModelRuntimeHostContract.from_yaml(yaml_file)
        assert contract.event_bus.kind == "local"
        assert contract.handlers == []
        assert contract.nodes == []

    def test_from_yaml_all_handler_types(self, tmp_path: Path) -> None:
        """Test from_yaml() with all handler types."""
        yaml_content = """
handlers:
  - handler_type: http
  - handler_type: database
  - handler_type: kafka
  - handler_type: filesystem
  - handler_type: vault
  - handler_type: vector_store
  - handler_type: graph_database
  - handler_type: redis
  - handler_type: event_bus
event_bus:
  kind: kafka
"""
        yaml_file = tmp_path / "all_handlers.yaml"
        yaml_file.write_text(yaml_content)

        contract = ModelRuntimeHostContract.from_yaml(yaml_file)
        assert len(contract.handlers) == 9
        handler_types = [h.handler_type for h in contract.handlers]
        assert EnumHandlerType.HTTP in handler_types
        assert EnumHandlerType.DATABASE in handler_types
        assert EnumHandlerType.KAFKA in handler_types
        assert EnumHandlerType.FILESYSTEM in handler_types
        assert EnumHandlerType.VAULT in handler_types
        assert EnumHandlerType.VECTOR_STORE in handler_types
        assert EnumHandlerType.GRAPH_DATABASE in handler_types
        assert EnumHandlerType.REDIS in handler_types
        assert EnumHandlerType.EVENT_BUS in handler_types

    def test_from_yaml_multiple_nodes(self, tmp_path: Path) -> None:
        """Test from_yaml() with multiple nodes."""
        yaml_content = """
event_bus:
  kind: kafka
nodes:
  - slug: node-compute-transformer
  - slug: node-effect-http-client
  - slug: node-reducer-aggregator
  - slug: node-orchestrator-workflow
"""
        yaml_file = tmp_path / "multiple_nodes.yaml"
        yaml_file.write_text(yaml_content)

        contract = ModelRuntimeHostContract.from_yaml(yaml_file)
        assert len(contract.nodes) == 4
        slugs = [n.slug for n in contract.nodes]
        assert "node-compute-transformer" in slugs
        assert "node-effect-http-client" in slugs
        assert "node-reducer-aggregator" in slugs
        assert "node-orchestrator-workflow" in slugs


@pytest.mark.unit
class TestModelRuntimeHostContractYamlErrors:
    """Tests for from_yaml() error handling."""

    def test_from_yaml_missing_file_raises_error(self, tmp_path: Path) -> None:
        """Test from_yaml() raises ModelOnexError for missing file."""
        missing_file = tmp_path / "nonexistent.yaml"
        with pytest.raises(ModelOnexError) as exc_info:
            ModelRuntimeHostContract.from_yaml(missing_file)
        assert "not found" in str(exc_info.value).lower()

    def test_from_yaml_invalid_yaml_syntax_raises_error(self, tmp_path: Path) -> None:
        """Test from_yaml() raises ModelOnexError for invalid YAML syntax."""
        yaml_content = """
event_bus:
  kind: kafka
  invalid: yaml: syntax: here
    unbalanced: [brackets
"""
        yaml_file = tmp_path / "invalid_syntax.yaml"
        yaml_file.write_text(yaml_content)

        with pytest.raises(ModelOnexError) as exc_info:
            ModelRuntimeHostContract.from_yaml(yaml_file)
        assert "yaml" in str(exc_info.value).lower()

    def test_from_yaml_invalid_contract_data_raises_error(self, tmp_path: Path) -> None:
        """Test from_yaml() raises ModelOnexError for invalid contract data."""
        yaml_content = """
event_bus:
  kind: ""
"""
        yaml_file = tmp_path / "invalid_data.yaml"
        yaml_file.write_text(yaml_content)

        with pytest.raises(ModelOnexError) as exc_info:
            ModelRuntimeHostContract.from_yaml(yaml_file)
        assert "validation" in str(exc_info.value).lower()

    def test_from_yaml_missing_required_field_raises_error(
        self, tmp_path: Path
    ) -> None:
        """Test from_yaml() raises ModelOnexError for missing required field."""
        yaml_content = """
handlers:
  - handler_type: http
nodes:
  - slug: my-node
"""
        yaml_file = tmp_path / "missing_event_bus.yaml"
        yaml_file.write_text(yaml_content)

        with pytest.raises(ModelOnexError) as exc_info:
            ModelRuntimeHostContract.from_yaml(yaml_file)
        assert "validation" in str(exc_info.value).lower()

    def test_from_yaml_invalid_handler_type_raises_error(self, tmp_path: Path) -> None:
        """Test from_yaml() raises ModelOnexError for invalid handler type."""
        yaml_content = """
handlers:
  - handler_type: invalid_type
event_bus:
  kind: kafka
"""
        yaml_file = tmp_path / "invalid_handler.yaml"
        yaml_file.write_text(yaml_content)

        with pytest.raises(ModelOnexError) as exc_info:
            ModelRuntimeHostContract.from_yaml(yaml_file)
        assert "validation" in str(exc_info.value).lower()

    def test_from_yaml_extra_fields_raises_error(self, tmp_path: Path) -> None:
        """Test from_yaml() raises ModelOnexError for extra fields."""
        yaml_content = """
event_bus:
  kind: kafka
  extra_field: not_allowed
"""
        yaml_file = tmp_path / "extra_fields.yaml"
        yaml_file.write_text(yaml_content)

        with pytest.raises(ModelOnexError) as exc_info:
            ModelRuntimeHostContract.from_yaml(yaml_file)
        assert "validation" in str(exc_info.value).lower()

    def test_from_yaml_non_mapping_yaml_raises_error(self, tmp_path: Path) -> None:
        """Test from_yaml() raises ModelOnexError for non-mapping YAML."""
        yaml_content = """
- item1
- item2
- item3
"""
        yaml_file = tmp_path / "list_yaml.yaml"
        yaml_file.write_text(yaml_content)

        with pytest.raises(ModelOnexError) as exc_info:
            ModelRuntimeHostContract.from_yaml(yaml_file)
        assert "mapping" in str(exc_info.value).lower()

    def test_from_yaml_scalar_yaml_raises_error(self, tmp_path: Path) -> None:
        """Test from_yaml() raises ModelOnexError for scalar YAML."""
        yaml_content = "just_a_string"
        yaml_file = tmp_path / "scalar.yaml"
        yaml_file.write_text(yaml_content)

        with pytest.raises(ModelOnexError) as exc_info:
            ModelRuntimeHostContract.from_yaml(yaml_file)
        assert "mapping" in str(exc_info.value).lower()

    def test_from_yaml_empty_file_raises_error(self, tmp_path: Path) -> None:
        """Test from_yaml() raises ModelOnexError for empty YAML file."""
        yaml_file = tmp_path / "empty.yaml"
        yaml_file.write_text("")

        with pytest.raises(ModelOnexError) as exc_info:
            ModelRuntimeHostContract.from_yaml(yaml_file)
        # Empty YAML results in None which is not a mapping
        assert "mapping" in str(exc_info.value).lower()


# =============================================================================
# Edge Cases and Integration Tests
# =============================================================================


@pytest.mark.unit
class TestRuntimeHostContractEdgeCases:
    """Edge case tests for RuntimeHostContract models."""

    def test_handler_config_preserves_enum_not_string(self) -> None:
        """Test that handler_type is preserved as enum, not string value."""
        config = ModelRuntimeHandlerConfig(handler_type=EnumHandlerType.HTTP)
        assert isinstance(config.handler_type, EnumHandlerType)
        assert config.handler_type is EnumHandlerType.HTTP

    def test_contract_with_empty_handlers_and_nodes(self) -> None:
        """Test contract with explicitly empty handlers and nodes."""
        contract = ModelRuntimeHostContract(
            handlers=[],
            event_bus=ModelRuntimeEventBusConfig(kind="kafka"),
            nodes=[],
        )
        assert contract.handlers == []
        assert contract.nodes == []

    def test_event_bus_kind_with_whitespace(self) -> None:
        """Test event bus kind with leading/trailing whitespace is preserved."""
        # Whitespace is allowed if min_length is satisfied
        config = ModelRuntimeEventBusConfig(kind=" kafka ")
        assert config.kind == " kafka "

    def test_node_ref_slug_with_special_characters(self) -> None:
        """Test node ref slug with special characters."""
        ref = ModelNodeRef(slug="node.name-with_special.chars-123")
        assert ref.slug == "node.name-with_special.chars-123"

    def test_handler_config_model_config_settings(self) -> None:
        """Test ModelRuntimeHandlerConfig has correct model_config settings."""
        assert ModelRuntimeHandlerConfig.model_config.get("extra") == "forbid"
        assert ModelRuntimeHandlerConfig.model_config.get("use_enum_values") is False

    def test_event_bus_config_model_config_settings(self) -> None:
        """Test ModelRuntimeEventBusConfig has correct model_config settings."""
        assert ModelRuntimeEventBusConfig.model_config.get("extra") == "forbid"
        assert (
            ModelRuntimeEventBusConfig.model_config.get("validate_assignment") is True
        )

    def test_node_ref_model_config_settings(self) -> None:
        """Test ModelNodeRef has correct model_config settings."""
        assert ModelNodeRef.model_config.get("extra") == "forbid"
        assert ModelNodeRef.model_config.get("validate_assignment") is True

    def test_runtime_host_contract_model_config_settings(self) -> None:
        """Test ModelRuntimeHostContract has correct model_config settings."""
        assert ModelRuntimeHostContract.model_config.get("extra") == "forbid"
        assert ModelRuntimeHostContract.model_config.get("validate_assignment") is True


@pytest.mark.unit
class TestRuntimeHostContractRepr:
    """Tests for __repr__ representation of RuntimeHostContract models."""

    def test_handler_config_repr_contains_type(self) -> None:
        """Test ModelRuntimeHandlerConfig repr contains handler type."""
        config = ModelRuntimeHandlerConfig(handler_type=EnumHandlerType.HTTP)
        repr_str = repr(config)
        assert "ModelRuntimeHandlerConfig" in repr_str or "http" in repr_str.lower()

    def test_event_bus_config_repr_contains_kind(self) -> None:
        """Test ModelRuntimeEventBusConfig repr contains kind."""
        config = ModelRuntimeEventBusConfig(kind="kafka")
        repr_str = repr(config)
        assert "ModelRuntimeEventBusConfig" in repr_str or "kafka" in repr_str

    def test_node_ref_repr_contains_slug(self) -> None:
        """Test ModelNodeRef repr contains slug."""
        ref = ModelNodeRef(slug="my-node")
        repr_str = repr(ref)
        assert "ModelNodeRef" in repr_str or "my-node" in repr_str

    def test_runtime_host_contract_repr(self) -> None:
        """Test ModelRuntimeHostContract repr is valid."""
        contract = ModelRuntimeHostContract(
            event_bus=ModelRuntimeEventBusConfig(kind="kafka"),
        )
        repr_str = repr(contract)
        assert "ModelRuntimeHostContract" in repr_str or "kafka" in repr_str
