# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

# Copyright (c) 2025 OmniNode Team
"""
Unit tests for ModelContractCapabilities.

Tests all aspects of the contract capabilities model including:
- Basic instantiation with required and optional fields
- List fields default to empty lists
- service_metadata is optional and defaults to None
- Model serializes/deserializes correctly
- Model accepts valid contract types
- from_attributes=True allows object-based construction
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from omnibase_core.models.capabilities.model_contract_capabilities import (
    ModelContractCapabilities,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer

# =============================================================================
# Basic Instantiation Tests
# =============================================================================


@pytest.mark.unit
class TestModelContractCapabilitiesBasicInstantiation:
    """Tests for basic model instantiation."""

    def test_instantiation_with_required_fields_only(self) -> None:
        """Test that model can be instantiated with only required fields."""
        capabilities = ModelContractCapabilities(
            contract_type="compute",
            contract_version=ModelSemVer(major=1, minor=0, patch=0),
        )

        assert capabilities.contract_type == "compute"
        assert capabilities.contract_version == ModelSemVer(major=1, minor=0, patch=0)
        assert capabilities.intent_types == []
        assert capabilities.protocols == []
        assert capabilities.capability_tags == []
        assert capabilities.service_metadata is None

    def test_instantiation_with_all_fields(self) -> None:
        """Test model instantiation with all fields populated."""
        service_meta: dict[str, object] = {"environment": "production", "tier": "gold"}

        capabilities = ModelContractCapabilities(
            contract_type="orchestrator",
            contract_version=ModelSemVer(major=2, minor=1, patch=0),
            intent_types=["OrderCreated", "PaymentProcessed"],
            protocols=["ProtocolCompute", "ProtocolEffect"],
            capability_tags=["async", "distributed", "fault-tolerant"],
            service_metadata=service_meta,
        )

        assert capabilities.contract_type == "orchestrator"
        assert capabilities.contract_version == ModelSemVer(major=2, minor=1, patch=0)
        assert capabilities.intent_types == ["OrderCreated", "PaymentProcessed"]
        assert capabilities.protocols == ["ProtocolCompute", "ProtocolEffect"]
        assert capabilities.capability_tags == [
            "async",
            "distributed",
            "fault-tolerant",
        ]
        assert capabilities.service_metadata == service_meta

    def test_contract_type_is_required(self) -> None:
        """Test that contract_type field is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelContractCapabilities(  # type: ignore[call-arg]
                contract_version=ModelSemVer(major=1, minor=0, patch=0),
            )

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("contract_type",)
        assert errors[0]["type"] == "missing"

    def test_contract_version_is_required(self) -> None:
        """Test that contract_version field is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelContractCapabilities(  # type: ignore[call-arg]
                contract_type="effect",
            )

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("contract_version",)
        assert errors[0]["type"] == "missing"

    def test_both_required_fields_missing(self) -> None:
        """Test that both required fields produce validation errors."""
        with pytest.raises(ValidationError) as exc_info:
            ModelContractCapabilities()  # type: ignore[call-arg]

        errors = exc_info.value.errors()
        assert len(errors) == 2
        error_locs = {e["loc"][0] for e in errors}
        assert "contract_type" in error_locs
        assert "contract_version" in error_locs


# =============================================================================
# Contract Type Tests
# =============================================================================


@pytest.mark.unit
class TestModelContractCapabilitiesContractTypes:
    """Tests for contract_type field validation."""

    def test_accepts_effect_contract_type(self) -> None:
        """Test that effect is a valid contract type."""
        capabilities = ModelContractCapabilities(
            contract_type="effect",
            contract_version=ModelSemVer(major=1, minor=0, patch=0),
        )
        assert capabilities.contract_type == "effect"

    def test_accepts_compute_contract_type(self) -> None:
        """Test that compute is a valid contract type."""
        capabilities = ModelContractCapabilities(
            contract_type="compute",
            contract_version=ModelSemVer(major=1, minor=0, patch=0),
        )
        assert capabilities.contract_type == "compute"

    def test_accepts_reducer_contract_type(self) -> None:
        """Test that reducer is a valid contract type."""
        capabilities = ModelContractCapabilities(
            contract_type="reducer",
            contract_version=ModelSemVer(major=1, minor=0, patch=0),
        )
        assert capabilities.contract_type == "reducer"

    def test_accepts_orchestrator_contract_type(self) -> None:
        """Test that orchestrator is a valid contract type."""
        capabilities = ModelContractCapabilities(
            contract_type="orchestrator",
            contract_version=ModelSemVer(major=1, minor=0, patch=0),
        )
        assert capabilities.contract_type == "orchestrator"

    def test_accepts_custom_contract_type(self) -> None:
        """Test that custom contract types are accepted (string type)."""
        capabilities = ModelContractCapabilities(
            contract_type="custom-workflow",
            contract_version=ModelSemVer(major=1, minor=0, patch=0),
        )
        assert capabilities.contract_type == "custom-workflow"


# =============================================================================
# Default Values Tests
# =============================================================================


@pytest.mark.unit
class TestModelContractCapabilitiesDefaultValues:
    """Tests for default value behavior."""

    def test_intent_types_defaults_to_empty_list(self) -> None:
        """Test that intent_types defaults to empty list."""
        capabilities = ModelContractCapabilities(
            contract_type="effect",
            contract_version=ModelSemVer(major=1, minor=0, patch=0),
        )
        assert capabilities.intent_types == []
        assert isinstance(capabilities.intent_types, list)

    def test_protocols_defaults_to_empty_list(self) -> None:
        """Test that protocols defaults to empty list."""
        capabilities = ModelContractCapabilities(
            contract_type="effect",
            contract_version=ModelSemVer(major=1, minor=0, patch=0),
        )
        assert capabilities.protocols == []
        assert isinstance(capabilities.protocols, list)

    def test_capability_tags_defaults_to_empty_list(self) -> None:
        """Test that capability_tags defaults to empty list."""
        capabilities = ModelContractCapabilities(
            contract_type="effect",
            contract_version=ModelSemVer(major=1, minor=0, patch=0),
        )
        assert capabilities.capability_tags == []
        assert isinstance(capabilities.capability_tags, list)

    def test_service_metadata_defaults_to_none(self) -> None:
        """Test that service_metadata defaults to None."""
        capabilities = ModelContractCapabilities(
            contract_type="effect",
            contract_version=ModelSemVer(major=1, minor=0, patch=0),
        )
        assert capabilities.service_metadata is None

    def test_list_defaults_are_independent_instances(self) -> None:
        """Test that list defaults don't share state between instances."""
        cap1 = ModelContractCapabilities(
            contract_type="effect",
            contract_version=ModelSemVer(major=1, minor=0, patch=0),
        )
        cap2 = ModelContractCapabilities(
            contract_type="compute",
            contract_version=ModelSemVer(major=2, minor=0, patch=0),
        )

        # Modifying one should not affect the other
        # Note: We need to test that the lists are independent
        assert cap1.intent_types is not cap2.intent_types
        assert cap1.protocols is not cap2.protocols
        assert cap1.capability_tags is not cap2.capability_tags


# =============================================================================
# Model Configuration Tests
# =============================================================================


@pytest.mark.unit
class TestModelContractCapabilitiesConfiguration:
    """Tests for model configuration (extra forbidden, from_attributes)."""

    def test_extra_fields_forbidden(self) -> None:
        """Test that extra fields are not allowed (extra='forbid')."""
        with pytest.raises(ValidationError) as exc_info:
            ModelContractCapabilities(
                contract_type="effect",
                contract_version=ModelSemVer(major=1, minor=0, patch=0),
                extra_field="should_fail",  # type: ignore[call-arg]
            )

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["type"] == "extra_forbidden"

    def test_from_attributes_allows_object_instantiation(self) -> None:
        """Test that from_attributes=True allows instantiation from objects.

        This is important for pytest-xdist parallel execution where model
        classes may be imported in separate workers with different identities.
        """

        # Create a simple object with matching attributes
        class MockCapabilities:
            contract_type = "orchestrator"
            contract_version = ModelSemVer(major=3, minor=0, patch=0)
            intent_types = ["IntentA", "IntentB"]
            protocols = ["ProtocolX"]
            capability_tags = ["tag1", "tag2"]
            service_metadata = {"key": "value"}

        mock = MockCapabilities()

        # from_attributes=True allows model_validate to accept objects
        capabilities = ModelContractCapabilities.model_validate(mock)

        assert capabilities.contract_type == "orchestrator"
        assert capabilities.contract_version == ModelSemVer(major=3, minor=0, patch=0)
        assert capabilities.intent_types == ["IntentA", "IntentB"]
        assert capabilities.protocols == ["ProtocolX"]
        assert capabilities.capability_tags == ["tag1", "tag2"]
        assert capabilities.service_metadata == {"key": "value"}


# =============================================================================
# Serialization Tests
# =============================================================================


@pytest.mark.unit
class TestModelContractCapabilitiesSerialization:
    """Tests for model serialization and deserialization."""

    def test_model_dump(self) -> None:
        """Test model serialization with model_dump."""
        service_meta: dict[str, object] = {"env": "prod"}
        capabilities = ModelContractCapabilities(
            contract_type="compute",
            contract_version=ModelSemVer(major=1, minor=2, patch=3),
            intent_types=["Intent1"],
            protocols=["Protocol1"],
            capability_tags=["tag1"],
            service_metadata=service_meta,
        )

        data = capabilities.model_dump()

        # Verify serialization roundtrips correctly
        restored = ModelContractCapabilities.model_validate(data)
        assert restored.contract_type == "compute"
        assert restored.contract_version == ModelSemVer(major=1, minor=2, patch=3)
        assert restored.intent_types == ["Intent1"]
        assert restored.protocols == ["Protocol1"]
        assert restored.capability_tags == ["tag1"]
        assert restored.service_metadata == {"env": "prod"}

    def test_model_dump_with_defaults(self) -> None:
        """Test model serialization includes default values."""
        capabilities = ModelContractCapabilities(
            contract_type="effect",
            contract_version=ModelSemVer(major=1, minor=0, patch=0),
        )

        data = capabilities.model_dump()

        # Verify serialization roundtrips correctly with defaults
        restored = ModelContractCapabilities.model_validate(data)
        assert restored.contract_type == "effect"
        assert restored.contract_version == ModelSemVer(major=1, minor=0, patch=0)
        assert restored.intent_types == []
        assert restored.protocols == []
        assert restored.capability_tags == []
        assert restored.service_metadata is None

    def test_model_dump_json(self) -> None:
        """Test model JSON serialization."""
        capabilities = ModelContractCapabilities(
            contract_type="reducer",
            contract_version=ModelSemVer(major=2, minor=0, patch=0),
            intent_types=["OrderIntent"],
            capability_tags=["stateful"],
        )

        json_str = capabilities.model_dump_json()

        assert isinstance(json_str, str)
        assert "reducer" in json_str
        assert "OrderIntent" in json_str
        assert "stateful" in json_str

    def test_model_roundtrip(self) -> None:
        """Test model roundtrip serialization/deserialization."""
        original = ModelContractCapabilities(
            contract_type="orchestrator",
            contract_version=ModelSemVer(major=4, minor=0, patch=0),
            intent_types=["A", "B", "C"],
            protocols=["P1", "P2"],
            capability_tags=["distributed", "resilient"],
            service_metadata={"priority": "high", "count": 42},
        )

        data = original.model_dump()
        restored = ModelContractCapabilities.model_validate(data)

        assert restored.contract_type == original.contract_type
        assert restored.contract_version == original.contract_version
        assert restored.intent_types == original.intent_types
        assert restored.protocols == original.protocols
        assert restored.capability_tags == original.capability_tags
        assert restored.service_metadata == original.service_metadata

    def test_model_validate_from_dict(self) -> None:
        """Test model validation from dictionary."""
        data = {
            "contract_type": "effect",
            "contract_version": {"major": 1, "minor": 1, "patch": 1},
            "intent_types": ["TestIntent"],
            "protocols": ["TestProtocol"],
            "capability_tags": ["test-tag"],
            "service_metadata": None,
        }

        capabilities = ModelContractCapabilities.model_validate(data)

        assert capabilities.contract_type == "effect"
        assert capabilities.contract_version == ModelSemVer(major=1, minor=1, patch=1)
        assert capabilities.intent_types == ["TestIntent"]


# =============================================================================
# Service Metadata Tests
# =============================================================================


@pytest.mark.unit
class TestModelContractCapabilitiesServiceMetadata:
    """Tests for service_metadata field behavior."""

    def test_service_metadata_accepts_dict(self) -> None:
        """Test that service_metadata accepts dict values."""
        metadata: dict[str, object] = {
            "environment": "production",
            "region": "us-east-1",
            "tier": "premium",
        }

        capabilities = ModelContractCapabilities(
            contract_type="effect",
            contract_version=ModelSemVer(major=1, minor=0, patch=0),
            service_metadata=metadata,
        )

        assert capabilities.service_metadata == metadata

    def test_service_metadata_accepts_nested_dict(self) -> None:
        """Test that service_metadata accepts nested dict values."""
        metadata: dict[str, object] = {
            "config": {
                "timeout": 30,
                "retries": 3,
            },
            "features": ["feature1", "feature2"],
        }

        capabilities = ModelContractCapabilities(
            contract_type="compute",
            contract_version=ModelSemVer(major=1, minor=0, patch=0),
            service_metadata=metadata,
        )

        assert capabilities.service_metadata == metadata
        # Access nested values via cast since we know the structure
        assert capabilities.service_metadata is not None
        config = capabilities.service_metadata["config"]
        assert isinstance(config, dict)
        assert config["timeout"] == 30

    def test_service_metadata_accepts_none_explicitly(self) -> None:
        """Test that service_metadata accepts None explicitly."""
        capabilities = ModelContractCapabilities(
            contract_type="effect",
            contract_version=ModelSemVer(major=1, minor=0, patch=0),
            service_metadata=None,
        )

        assert capabilities.service_metadata is None


# =============================================================================
# List Fields Tests
# =============================================================================


@pytest.mark.unit
class TestModelContractCapabilitiesListFields:
    """Tests for list field behaviors."""

    def test_intent_types_with_multiple_values(self) -> None:
        """Test intent_types with multiple values."""
        intents = ["OrderCreated", "PaymentReceived", "ShipmentDispatched"]

        capabilities = ModelContractCapabilities(
            contract_type="orchestrator",
            contract_version=ModelSemVer(major=1, minor=0, patch=0),
            intent_types=intents,
        )

        assert len(capabilities.intent_types) == 3
        assert capabilities.intent_types == intents

    def test_protocols_with_multiple_values(self) -> None:
        """Test protocols with multiple values."""
        protocols = ["ProtocolCompute", "ProtocolEffect", "ProtocolOrchestrator"]

        capabilities = ModelContractCapabilities(
            contract_type="orchestrator",
            contract_version=ModelSemVer(major=1, minor=0, patch=0),
            protocols=protocols,
        )

        assert len(capabilities.protocols) == 3
        assert capabilities.protocols == protocols

    def test_capability_tags_with_multiple_values(self) -> None:
        """Test capability_tags with multiple values."""
        tags = ["async", "distributed", "fault-tolerant", "scalable"]

        capabilities = ModelContractCapabilities(
            contract_type="effect",
            contract_version=ModelSemVer(major=1, minor=0, patch=0),
            capability_tags=tags,
        )

        assert len(capabilities.capability_tags) == 4
        assert capabilities.capability_tags == tags

    def test_empty_lists_explicit(self) -> None:
        """Test that empty lists can be set explicitly."""
        capabilities = ModelContractCapabilities(
            contract_type="effect",
            contract_version=ModelSemVer(major=1, minor=0, patch=0),
            intent_types=[],
            protocols=[],
            capability_tags=[],
        )

        assert capabilities.intent_types == []
        assert capabilities.protocols == []
        assert capabilities.capability_tags == []


# =============================================================================
# Model Equality Tests
# =============================================================================


@pytest.mark.unit
class TestModelContractCapabilitiesEquality:
    """Tests for model equality comparison."""

    def test_model_equality_same_values(self) -> None:
        """Test model equality with same values."""
        cap1 = ModelContractCapabilities(
            contract_type="effect",
            contract_version=ModelSemVer(major=1, minor=0, patch=0),
            intent_types=["Intent1"],
            protocols=["Protocol1"],
            capability_tags=["tag1"],
        )

        cap2 = ModelContractCapabilities(
            contract_type="effect",
            contract_version=ModelSemVer(major=1, minor=0, patch=0),
            intent_types=["Intent1"],
            protocols=["Protocol1"],
            capability_tags=["tag1"],
        )

        assert cap1 == cap2

    def test_model_inequality_different_contract_type(self) -> None:
        """Test model inequality with different contract_type."""
        cap1 = ModelContractCapabilities(
            contract_type="effect",
            contract_version=ModelSemVer(major=1, minor=0, patch=0),
        )

        cap2 = ModelContractCapabilities(
            contract_type="compute",
            contract_version=ModelSemVer(major=1, minor=0, patch=0),
        )

        assert cap1 != cap2

    def test_model_inequality_different_version(self) -> None:
        """Test model inequality with different contract_version."""
        cap1 = ModelContractCapabilities(
            contract_type="effect",
            contract_version=ModelSemVer(major=1, minor=0, patch=0),
        )

        cap2 = ModelContractCapabilities(
            contract_type="effect",
            contract_version=ModelSemVer(major=2, minor=0, patch=0),
        )

        assert cap1 != cap2


# =============================================================================
# Model Schema Tests
# =============================================================================


@pytest.mark.unit
class TestModelContractCapabilitiesSchema:
    """Tests for model schema and field information."""

    def test_model_json_schema(self) -> None:
        """Test that model generates valid JSON schema."""
        schema = ModelContractCapabilities.model_json_schema()

        assert isinstance(schema, dict)
        assert "properties" in schema
        assert "contract_type" in schema["properties"]
        assert "contract_version" in schema["properties"]
        assert "intent_types" in schema["properties"]
        assert "protocols" in schema["properties"]
        assert "capability_tags" in schema["properties"]
        assert "service_metadata" in schema["properties"]

    def test_model_fields(self) -> None:
        """Test model fields metadata."""
        fields = ModelContractCapabilities.model_fields

        assert "contract_type" in fields
        assert "contract_version" in fields
        assert "intent_types" in fields
        assert "protocols" in fields
        assert "capability_tags" in fields
        assert "service_metadata" in fields

        # Check required vs optional
        assert fields["contract_type"].is_required() is True
        assert fields["contract_version"].is_required() is True
        assert fields["intent_types"].is_required() is False
        assert fields["protocols"].is_required() is False
        assert fields["capability_tags"].is_required() is False
        assert fields["service_metadata"].is_required() is False


# =============================================================================
# String Representation Tests
# =============================================================================


@pytest.mark.unit
class TestModelContractCapabilitiesRepresentation:
    """Tests for model string representation."""

    def test_str_representation(self) -> None:
        """Test string representation of model."""
        capabilities = ModelContractCapabilities(
            contract_type="compute",
            contract_version=ModelSemVer(major=1, minor=0, patch=0),
        )

        str_repr = str(capabilities)
        assert isinstance(str_repr, str)

    def test_repr_representation(self) -> None:
        """Test repr representation of model."""
        capabilities = ModelContractCapabilities(
            contract_type="compute",
            contract_version=ModelSemVer(major=1, minor=0, patch=0),
        )

        repr_str = repr(capabilities)
        assert isinstance(repr_str, str)
        assert "ModelContractCapabilities" in repr_str
