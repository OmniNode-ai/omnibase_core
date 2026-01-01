# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for ModelProviderDescriptor."""

from typing import Any
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.providers import ModelProviderDescriptor

# Fixed UUID for deterministic tests
TEST_UUID = UUID("12345678-1234-5678-1234-567812345678")
TEST_UUID_2 = UUID("87654321-4321-8765-4321-876543218765")


def _get_health_status_class() -> type[Any]:
    """Lazily import ModelHealthStatus and rebuild ModelProviderDescriptor.

    This function handles the circular import issue by importing ModelHealthStatus
    only when needed, and ensures ModelProviderDescriptor's forward reference
    is resolved.
    """
    from omnibase_core.models.health.model_health_status import ModelHealthStatus

    # Ensure the forward reference is resolved
    ModelProviderDescriptor.model_rebuild()
    return ModelHealthStatus


@pytest.fixture
def valid_descriptor_kwargs() -> dict:
    """Fixture providing valid kwargs for ModelProviderDescriptor."""
    return {
        "provider_id": TEST_UUID,
        "capabilities": ["database.relational"],
        "adapter": "test.adapters.TestAdapter",
        "connection_ref": "secrets://test/connection",
    }


@pytest.mark.unit
class TestModelProviderDescriptorInstantiation:
    """Tests for ModelProviderDescriptor instantiation."""

    def test_basic_instantiation_with_required_fields(
        self, valid_descriptor_kwargs: dict
    ) -> None:
        """Test creating descriptor with all required fields."""
        descriptor = ModelProviderDescriptor(**valid_descriptor_kwargs)

        assert descriptor.provider_id == TEST_UUID
        assert descriptor.capabilities == ["database.relational"]
        assert descriptor.adapter == "test.adapters.TestAdapter"
        assert descriptor.connection_ref == "secrets://test/connection"
        # Verify defaults
        assert descriptor.attributes == {}
        assert descriptor.declared_features == {}
        assert descriptor.observed_features == {}
        assert descriptor.tags == []
        assert descriptor.health is None

    def test_instantiation_with_all_fields(self) -> None:
        """Test creating descriptor with all optional fields."""
        ModelHealthStatus = _get_health_status_class()
        health = ModelHealthStatus.create_healthy(score=1.0)
        descriptor = ModelProviderDescriptor(
            provider_id=TEST_UUID,
            capabilities=["database.relational", "database.postgresql"],
            adapter="omnibase_infra.adapters.PostgresAdapter",
            connection_ref="secrets://postgres/primary",
            attributes={"version": "15.4", "region": "us-east-1"},
            declared_features={"supports_json": True, "max_connections": 100},
            observed_features={"actual_connections": 50},
            tags=["production", "primary"],
            health=health,
        )

        assert descriptor.provider_id == TEST_UUID
        assert len(descriptor.capabilities) == 2
        assert "database.postgresql" in descriptor.capabilities
        assert "database.relational" in descriptor.capabilities
        assert descriptor.adapter == "omnibase_infra.adapters.PostgresAdapter"
        assert descriptor.connection_ref == "secrets://postgres/primary"
        assert descriptor.attributes["version"] == "15.4"
        assert descriptor.declared_features["supports_json"] is True
        assert descriptor.observed_features["actual_connections"] == 50
        assert "production" in descriptor.tags
        assert descriptor.health == health

    def test_instantiation_with_health_status(
        self, valid_descriptor_kwargs: dict
    ) -> None:
        """Test creating descriptor with health status."""
        ModelHealthStatus = _get_health_status_class()
        health = ModelHealthStatus.create_degraded(score=0.6)
        descriptor = ModelProviderDescriptor(
            **valid_descriptor_kwargs,
            health=health,
        )

        assert descriptor.health is not None
        assert descriptor.health.status == "degraded"
        assert descriptor.health.health_score == 0.6


@pytest.mark.unit
class TestModelProviderDescriptorCapabilities:
    """Tests for capability validation."""

    def test_capabilities_non_empty_required(self) -> None:
        """Test that capabilities list cannot be empty.

        Validates structural requirement: capabilities must have at least one entry.
        This is distinct from pattern validation (test_capabilities_valid_pattern_accepted)
        which validates the format of individual capability strings.
        """
        with pytest.raises(
            (ValidationError, ModelOnexError),
        ):
            ModelProviderDescriptor(
                provider_id=uuid4(),
                capabilities=[],
                adapter="test.Adapter",
                connection_ref="secrets://test",
            )

    def test_capabilities_valid_pattern_accepted(self) -> None:
        """Test that valid capability patterns are accepted.

        Validates pattern format: capabilities must be lowercase dot-separated strings.
        This is distinct from non-empty validation (test_capabilities_non_empty_required)
        which ensures the list has at least one entry.
        """
        descriptor = ModelProviderDescriptor(
            provider_id=uuid4(),
            capabilities=["database.relational", "cache.redis.cluster"],
            adapter="test.Adapter",
            connection_ref="secrets://test",
        )

        assert "database.relational" in descriptor.capabilities
        assert "cache.redis.cluster" in descriptor.capabilities

    def test_capabilities_complex_hierarchy_accepted(self) -> None:
        """Test that deeply nested capability patterns are accepted."""
        descriptor = ModelProviderDescriptor(
            provider_id=uuid4(),
            capabilities=["storage.s3.us.east.1"],
            adapter="test.Adapter",
            connection_ref="secrets://test",
        )

        assert "storage.s3.us.east.1" in descriptor.capabilities

    def test_capabilities_invalid_pattern_no_dot_rejected(self) -> None:
        """Test that capabilities without dots are rejected."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelProviderDescriptor(
                provider_id=uuid4(),
                capabilities=["nodot"],
                adapter="test.Adapter",
                connection_ref="secrets://test",
            )

        assert "must be lowercase" in str(exc_info.value)
        assert "at least one dot" in str(exc_info.value)

    def test_capabilities_invalid_pattern_uppercase_rejected(self) -> None:
        """Test that capabilities with uppercase letters are rejected."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelProviderDescriptor(
                provider_id=uuid4(),
                capabilities=["Database.Relational"],
                adapter="test.Adapter",
                connection_ref="secrets://test",
            )

        assert "must be lowercase" in str(exc_info.value)

    def test_capabilities_invalid_pattern_special_chars_rejected(self) -> None:
        """Test that capabilities with special characters are rejected."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelProviderDescriptor(
                provider_id=uuid4(),
                capabilities=["data_base.rela-tional"],
                adapter="test.Adapter",
                connection_ref="secrets://test",
            )

        assert "must be lowercase" in str(exc_info.value)

    def test_capabilities_normalized_and_deduped(self) -> None:
        """Test that capabilities are deduplicated."""
        descriptor = ModelProviderDescriptor(
            provider_id=uuid4(),
            capabilities=["database.relational", "database.relational"],
            adapter="test.Adapter",
            connection_ref="secrets://test",
        )

        assert len(descriptor.capabilities) == 1
        assert descriptor.capabilities == ["database.relational"]

    def test_capabilities_sorted(self) -> None:
        """Test that capabilities are sorted alphabetically."""
        descriptor = ModelProviderDescriptor(
            provider_id=uuid4(),
            capabilities=["z.service", "a.service", "m.service"],
            adapter="test.Adapter",
            connection_ref="secrets://test",
        )

        assert descriptor.capabilities == ["a.service", "m.service", "z.service"]

    def test_capabilities_whitespace_stripped(self) -> None:
        """Test that whitespace is stripped from capabilities."""
        descriptor = ModelProviderDescriptor(
            provider_id=uuid4(),
            capabilities=["  database.relational  "],
            adapter="test.Adapter",
            connection_ref="secrets://test",
        )

        assert descriptor.capabilities == ["database.relational"]


@pytest.mark.unit
class TestModelProviderDescriptorTags:
    """Tests for tag validation."""

    def test_tags_default_empty_list(self, valid_descriptor_kwargs: dict) -> None:
        """Test that tags default to empty list."""
        descriptor = ModelProviderDescriptor(**valid_descriptor_kwargs)
        assert descriptor.tags == []

    def test_tags_normalized_and_deduped(self, valid_descriptor_kwargs: dict) -> None:
        """Test that tags are deduplicated."""
        descriptor = ModelProviderDescriptor(
            **valid_descriptor_kwargs,
            tags=["production", "production", "primary"],
        )

        assert len(descriptor.tags) == 2
        assert "production" in descriptor.tags
        assert "primary" in descriptor.tags

    def test_tags_sorted(self, valid_descriptor_kwargs: dict) -> None:
        """Test that tags are sorted alphabetically."""
        descriptor = ModelProviderDescriptor(
            **valid_descriptor_kwargs,
            tags=["zebra", "alpha", "middle"],
        )

        assert descriptor.tags == ["alpha", "middle", "zebra"]

    def test_tags_empty_strings_rejected(self, valid_descriptor_kwargs: dict) -> None:
        """Test that empty string tags are rejected."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelProviderDescriptor(
                **valid_descriptor_kwargs,
                tags=["valid", ""],
            )

        assert "cannot be empty" in str(exc_info.value)

    def test_tags_whitespace_only_rejected(self, valid_descriptor_kwargs: dict) -> None:
        """Test that whitespace-only tags are rejected."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelProviderDescriptor(
                **valid_descriptor_kwargs,
                tags=["valid", "   "],
            )

        assert "cannot be empty" in str(exc_info.value)

    def test_tags_whitespace_stripped(self, valid_descriptor_kwargs: dict) -> None:
        """Test that whitespace is stripped from tags."""
        descriptor = ModelProviderDescriptor(
            **valid_descriptor_kwargs,
            tags=["  production  ", "  staging  "],
        )

        assert "production" in descriptor.tags
        assert "staging" in descriptor.tags


@pytest.mark.unit
class TestModelProviderDescriptorConnectionRef:
    """Tests for connection_ref validation."""

    def test_connection_ref_valid_scheme_accepted(self) -> None:
        """Test that valid connection refs with schemes are accepted."""
        valid_refs = [
            "secrets://postgres/primary",
            "env://DB_CONNECTION_STRING",
            "vault://secret/data/postgres",
            "file:///etc/postgres/connection.yaml",
        ]

        for ref in valid_refs:
            descriptor = ModelProviderDescriptor(
                provider_id=uuid4(),
                capabilities=["database.relational"],
                adapter="test.Adapter",
                connection_ref=ref,
            )
            assert descriptor.connection_ref == ref

    def test_connection_ref_missing_scheme_rejected(self) -> None:
        """Test that connection refs without scheme separator are rejected."""
        invalid_refs = [
            "postgres/primary",
            "just-a-string",
            "no-scheme-here",
            "almost:missing-slashes",
        ]

        for ref in invalid_refs:
            with pytest.raises(ModelOnexError) as exc_info:
                ModelProviderDescriptor(
                    provider_id=uuid4(),
                    capabilities=["database.relational"],
                    adapter="test.Adapter",
                    connection_ref=ref,
                )

            assert "://" in str(exc_info.value)

    def test_connection_ref_empty_scheme_rejected(self) -> None:
        """Test that connection refs with empty scheme are rejected."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelProviderDescriptor(
                provider_id=uuid4(),
                capabilities=["database.relational"],
                adapter="test.Adapter",
                connection_ref="://no-scheme",
            )

        assert "scheme cannot be empty" in str(exc_info.value)

    def test_connection_ref_uppercase_scheme_rejected(self) -> None:
        """Test that connection refs with uppercase scheme are rejected."""
        invalid_refs = [
            "SECRETS://path",
            "Env://VAR",
            "VAULT://secret/path",
            "HTTP://server/endpoint",
        ]

        for ref in invalid_refs:
            with pytest.raises(ModelOnexError) as exc_info:
                ModelProviderDescriptor(
                    provider_id=uuid4(),
                    capabilities=["database.relational"],
                    adapter="test.Adapter",
                    connection_ref=ref,
                )

            assert "lowercase alphanumeric" in str(exc_info.value)

    def test_connection_ref_empty_path_rejected(self) -> None:
        """Test that connection refs with empty path are rejected."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelProviderDescriptor(
                provider_id=uuid4(),
                capabilities=["database.relational"],
                adapter="test.Adapter",
                connection_ref="secrets://",
            )

        assert "path cannot be empty" in str(exc_info.value)

    def test_connection_ref_scheme_starting_with_number_rejected(self) -> None:
        """Test that schemes starting with a number are rejected."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelProviderDescriptor(
                provider_id=uuid4(),
                capabilities=["database.relational"],
                adapter="test.Adapter",
                connection_ref="123scheme://path",
            )

        assert "lowercase alphanumeric, starting with a letter" in str(exc_info.value)

    def test_connection_ref_scheme_with_special_chars_rejected(self) -> None:
        """Test that schemes with special characters are rejected."""
        invalid_refs = [
            "sec-rets://path",
            "my_scheme://path",
            "scheme.name://path",
            "scheme+ext://path",
        ]

        for ref in invalid_refs:
            with pytest.raises(ModelOnexError) as exc_info:
                ModelProviderDescriptor(
                    provider_id=uuid4(),
                    capabilities=["database.relational"],
                    adapter="test.Adapter",
                    connection_ref=ref,
                )

            assert "lowercase alphanumeric" in str(exc_info.value)

    def test_connection_ref_scheme_with_digits_accepted(self) -> None:
        """Test that schemes with digits (after first letter) are accepted."""
        valid_refs = [
            "s3://bucket/key",
            "http2://server/path",
            "v1beta://api/endpoint",
        ]

        for ref in valid_refs:
            descriptor = ModelProviderDescriptor(
                provider_id=uuid4(),
                capabilities=["database.relational"],
                adapter="test.Adapter",
                connection_ref=ref,
            )
            assert descriptor.connection_ref == ref


@pytest.mark.unit
class TestModelProviderDescriptorAdapter:
    """Tests for adapter validation."""

    def test_adapter_valid_paths_accepted(self) -> None:
        """Test that valid Python import paths are accepted."""
        valid_adapters = [
            "omnibase_infra.adapters.PostgresAdapter",
            "test.Adapter",
            "my_module.sub.Class",
            "_private.Module",
            "a.b",
            "module_name.ClassName",
            "pkg.sub_pkg.Module123",
            "_hidden._internal.Impl",
        ]

        for adapter in valid_adapters:
            descriptor = ModelProviderDescriptor(
                provider_id=uuid4(),
                capabilities=["database.relational"],
                adapter=adapter,
                connection_ref="secrets://test",
            )
            assert descriptor.adapter == adapter

    def test_adapter_no_dot_rejected(self) -> None:
        """Test that adapter without dots is rejected."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelProviderDescriptor(
                provider_id=uuid4(),
                capabilities=["database.relational"],
                adapter="NoDotsHere",
                connection_ref="secrets://test",
            )

        assert "at least one dot" in str(exc_info.value)
        assert "NoDotsHere" in str(exc_info.value)

    def test_adapter_starts_with_number_rejected(self) -> None:
        """Test that adapter with segment starting with number is rejected."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelProviderDescriptor(
                provider_id=uuid4(),
                capabilities=["database.relational"],
                adapter="123module.Adapter",
                connection_ref="secrets://test",
            )

        assert "not a valid Python identifier" in str(exc_info.value)
        assert "123module" in str(exc_info.value)

    def test_adapter_number_in_later_segment_rejected(self) -> None:
        """Test that adapter with later segment starting with number is rejected."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelProviderDescriptor(
                provider_id=uuid4(),
                capabilities=["database.relational"],
                adapter="valid.123invalid",
                connection_ref="secrets://test",
            )

        assert "not a valid Python identifier" in str(exc_info.value)
        assert "123invalid" in str(exc_info.value)

    def test_adapter_with_spaces_rejected(self) -> None:
        """Test that adapter with spaces is rejected."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelProviderDescriptor(
                provider_id=uuid4(),
                capabilities=["database.relational"],
                adapter="has spaces.invalid",
                connection_ref="secrets://test",
            )

        assert "not a valid Python identifier" in str(exc_info.value)

    def test_adapter_with_hyphen_rejected(self) -> None:
        """Test that adapter with hyphens is rejected."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelProviderDescriptor(
                provider_id=uuid4(),
                capabilities=["database.relational"],
                adapter="my-module.Adapter",
                connection_ref="secrets://test",
            )

        assert "not a valid Python identifier" in str(exc_info.value)

    def test_adapter_with_special_chars_rejected(self) -> None:
        """Test that adapter with special characters is rejected."""
        invalid_adapters = [
            "module@.Class",
            "pkg$.Adapter",
            "mod!ule.Class",
            "mod#.Class",
        ]

        for adapter in invalid_adapters:
            with pytest.raises(ModelOnexError):
                ModelProviderDescriptor(
                    provider_id=uuid4(),
                    capabilities=["database.relational"],
                    adapter=adapter,
                    connection_ref="secrets://test",
                )

    def test_adapter_empty_segment_rejected(self) -> None:
        """Test that adapter with empty segment (double dot) is rejected."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelProviderDescriptor(
                provider_id=uuid4(),
                capabilities=["database.relational"],
                adapter="module..Class",
                connection_ref="secrets://test",
            )

        assert "not a valid Python identifier" in str(exc_info.value)

    def test_adapter_leading_dot_rejected(self) -> None:
        """Test that adapter with leading dot is rejected."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelProviderDescriptor(
                provider_id=uuid4(),
                capabilities=["database.relational"],
                adapter=".module.Class",
                connection_ref="secrets://test",
            )

        assert "not a valid Python identifier" in str(exc_info.value)

    def test_adapter_trailing_dot_rejected(self) -> None:
        """Test that adapter with trailing dot is rejected."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelProviderDescriptor(
                provider_id=uuid4(),
                capabilities=["database.relational"],
                adapter="module.Class.",
                connection_ref="secrets://test",
            )

        assert "not a valid Python identifier" in str(exc_info.value)


@pytest.mark.unit
class TestModelProviderDescriptorFeatures:
    """Tests for feature resolution."""

    def test_get_effective_features_prefers_observed(self) -> None:
        """Test that observed_features takes precedence over declared_features."""
        descriptor = ModelProviderDescriptor(
            provider_id=uuid4(),
            capabilities=["database.relational"],
            adapter="test.Adapter",
            connection_ref="secrets://test",
            declared_features={"feature_a": True, "feature_b": "declared"},
            observed_features={"feature_c": True, "feature_b": "observed"},
        )

        effective = descriptor.get_effective_features()

        # Should return observed_features entirely, not merged
        assert effective == {"feature_c": True, "feature_b": "observed"}
        assert "feature_a" not in effective

    def test_get_effective_features_falls_back_to_declared(self) -> None:
        """Test that declared_features is used when observed_features is empty."""
        descriptor = ModelProviderDescriptor(
            provider_id=uuid4(),
            capabilities=["database.relational"],
            adapter="test.Adapter",
            connection_ref="secrets://test",
            declared_features={"feature_a": True, "feature_b": 100},
        )

        effective = descriptor.get_effective_features()

        assert effective == {"feature_a": True, "feature_b": 100}

    def test_get_effective_features_empty_when_both_empty(self) -> None:
        """Test that empty dict is returned when both feature dicts are empty."""
        descriptor = ModelProviderDescriptor(
            provider_id=uuid4(),
            capabilities=["database.relational"],
            adapter="test.Adapter",
            connection_ref="secrets://test",
        )

        effective = descriptor.get_effective_features()

        assert effective == {}

    def test_features_accept_json_values_string(
        self, valid_descriptor_kwargs: dict
    ) -> None:
        """Test that string values are accepted in features."""
        descriptor = ModelProviderDescriptor(
            **valid_descriptor_kwargs,
            declared_features={"version": "15.4", "region": "us-east-1"},
        )

        assert descriptor.declared_features["version"] == "15.4"

    def test_features_accept_json_values_int(
        self, valid_descriptor_kwargs: dict
    ) -> None:
        """Test that integer values are accepted in features."""
        descriptor = ModelProviderDescriptor(
            **valid_descriptor_kwargs,
            declared_features={"max_connections": 100, "timeout_ms": 5000},
        )

        assert descriptor.declared_features["max_connections"] == 100

    def test_features_accept_json_values_bool(
        self, valid_descriptor_kwargs: dict
    ) -> None:
        """Test that boolean values are accepted in features."""
        descriptor = ModelProviderDescriptor(
            **valid_descriptor_kwargs,
            declared_features={"supports_json": True, "read_only": False},
        )

        assert descriptor.declared_features["supports_json"] is True
        assert descriptor.declared_features["read_only"] is False

    def test_features_accept_json_values_list(
        self, valid_descriptor_kwargs: dict
    ) -> None:
        """Test that list values are accepted in features."""
        descriptor = ModelProviderDescriptor(
            **valid_descriptor_kwargs,
            declared_features={"supported_formats": ["json", "xml", "csv"]},
        )

        assert descriptor.declared_features["supported_formats"] == [
            "json",
            "xml",
            "csv",
        ]

    def test_features_accept_json_values_dict(
        self, valid_descriptor_kwargs: dict
    ) -> None:
        """Test that dict values are accepted in features."""
        descriptor = ModelProviderDescriptor(
            **valid_descriptor_kwargs,
            declared_features={"config": {"host": "localhost", "port": 5432}},
        )

        assert descriptor.declared_features["config"]["host"] == "localhost"
        assert descriptor.declared_features["config"]["port"] == 5432

    def test_features_accept_json_values_none(
        self, valid_descriptor_kwargs: dict
    ) -> None:
        """Test that None values are accepted in features."""
        descriptor = ModelProviderDescriptor(
            **valid_descriptor_kwargs,
            declared_features={"optional_setting": None},
        )

        assert descriptor.declared_features["optional_setting"] is None


@pytest.mark.unit
class TestModelProviderDescriptorAttributes:
    """Tests for attributes field with JsonType (aliased as JsonValue).

    The attributes field uses dict[str, JsonValue] where JsonValue is an alias
    for JsonType. JsonType is the recursive PEP 695 type:
        type JsonType = JsonPrimitive | list[JsonType] | dict[str, JsonType]
    where JsonPrimitive = str | int | float | bool | None

    These tests verify that all JSON-compatible value types work correctly
    in the attributes dictionary.
    """

    def test_attributes_default_empty_dict(self, valid_descriptor_kwargs: dict) -> None:
        """Test that attributes default to empty dict."""
        descriptor = ModelProviderDescriptor(**valid_descriptor_kwargs)
        assert descriptor.attributes == {}

    def test_attributes_accept_string_values(
        self, valid_descriptor_kwargs: dict
    ) -> None:
        """Test that string values are accepted in attributes."""
        descriptor = ModelProviderDescriptor(
            **valid_descriptor_kwargs,
            attributes={"version": "15.4", "region": "us-east-1", "tier": "premium"},
        )

        assert descriptor.attributes["version"] == "15.4"
        assert descriptor.attributes["region"] == "us-east-1"
        assert descriptor.attributes["tier"] == "premium"

    def test_attributes_accept_int_values(self, valid_descriptor_kwargs: dict) -> None:
        """Test that integer values are accepted in attributes."""
        descriptor = ModelProviderDescriptor(
            **valid_descriptor_kwargs,
            attributes={"max_connections": 100, "port": 5432, "timeout_ms": 5000},
        )

        assert descriptor.attributes["max_connections"] == 100
        assert descriptor.attributes["port"] == 5432
        assert descriptor.attributes["timeout_ms"] == 5000

    def test_attributes_accept_float_values(
        self, valid_descriptor_kwargs: dict
    ) -> None:
        """Test that float values are accepted in attributes."""
        descriptor = ModelProviderDescriptor(
            **valid_descriptor_kwargs,
            attributes={
                "uptime_percent": 99.95,
                "latency_ms": 0.5,
                "threshold": 0.75,
            },
        )

        assert descriptor.attributes["uptime_percent"] == 99.95
        assert descriptor.attributes["latency_ms"] == 0.5
        assert descriptor.attributes["threshold"] == 0.75

    def test_attributes_accept_bool_values(self, valid_descriptor_kwargs: dict) -> None:
        """Test that boolean values are accepted in attributes."""
        descriptor = ModelProviderDescriptor(
            **valid_descriptor_kwargs,
            attributes={
                "ssl_enabled": True,
                "read_only": False,
                "auto_reconnect": True,
            },
        )

        assert descriptor.attributes["ssl_enabled"] is True
        assert descriptor.attributes["read_only"] is False
        assert descriptor.attributes["auto_reconnect"] is True

    def test_attributes_accept_none_values(self, valid_descriptor_kwargs: dict) -> None:
        """Test that None values are accepted in attributes."""
        descriptor = ModelProviderDescriptor(
            **valid_descriptor_kwargs,
            attributes={
                "optional_config": None,
                "fallback_host": None,
            },
        )

        assert descriptor.attributes["optional_config"] is None
        assert descriptor.attributes["fallback_host"] is None

    def test_attributes_accept_list_values(self, valid_descriptor_kwargs: dict) -> None:
        """Test that list values are accepted in attributes."""
        descriptor = ModelProviderDescriptor(
            **valid_descriptor_kwargs,
            attributes={
                "supported_formats": ["json", "xml", "csv"],
                "replica_hosts": ["host1.db.local", "host2.db.local"],
                "ports": [5432, 5433, 5434],
            },
        )

        assert descriptor.attributes["supported_formats"] == ["json", "xml", "csv"]
        assert descriptor.attributes["replica_hosts"] == [
            "host1.db.local",
            "host2.db.local",
        ]
        assert descriptor.attributes["ports"] == [5432, 5433, 5434]

    def test_attributes_accept_dict_values(self, valid_descriptor_kwargs: dict) -> None:
        """Test that dict values are accepted in attributes."""
        descriptor = ModelProviderDescriptor(
            **valid_descriptor_kwargs,
            attributes={
                "connection_pool": {"min_size": 5, "max_size": 20},
                "retry_config": {"max_retries": 3, "backoff_ms": 1000},
            },
        )

        assert descriptor.attributes["connection_pool"]["min_size"] == 5
        assert descriptor.attributes["connection_pool"]["max_size"] == 20
        assert descriptor.attributes["retry_config"]["max_retries"] == 3
        assert descriptor.attributes["retry_config"]["backoff_ms"] == 1000

    def test_attributes_accept_deeply_nested_structures(
        self, valid_descriptor_kwargs: dict
    ) -> None:
        """Test that deeply nested JSON structures are accepted in attributes.

        This tests the recursive nature of JsonType:
            type JsonType = JsonPrimitive | list[JsonType] | dict[str, JsonType]
        """
        descriptor = ModelProviderDescriptor(
            **valid_descriptor_kwargs,
            attributes={
                "database": {
                    "hosts": ["host1", "host2"],
                    "settings": {
                        "timeout": 30,
                        "retry": True,
                        "nested": {
                            "deep_value": 42,
                            "deep_list": [1, 2, {"even_deeper": "value"}],
                        },
                    },
                },
            },
        )

        # Verify deep nesting works
        assert descriptor.attributes["database"]["hosts"] == ["host1", "host2"]
        assert descriptor.attributes["database"]["settings"]["timeout"] == 30
        assert descriptor.attributes["database"]["settings"]["retry"] is True
        assert (
            descriptor.attributes["database"]["settings"]["nested"]["deep_value"] == 42
        )
        assert (
            descriptor.attributes["database"]["settings"]["nested"]["deep_list"][2][
                "even_deeper"
            ]
            == "value"
        )

    def test_attributes_accept_mixed_value_types(
        self, valid_descriptor_kwargs: dict
    ) -> None:
        """Test that mixed value types work together in attributes."""
        descriptor = ModelProviderDescriptor(
            **valid_descriptor_kwargs,
            attributes={
                "name": "primary-db",
                "port": 5432,
                "uptime": 99.9,
                "enabled": True,
                "deprecated_field": None,
                "hosts": ["host1", "host2"],
                "config": {"retries": 3, "timeout_ms": 5000},
            },
        )

        assert isinstance(descriptor.attributes["name"], str)
        assert isinstance(descriptor.attributes["port"], int)
        assert isinstance(descriptor.attributes["uptime"], float)
        assert isinstance(descriptor.attributes["enabled"], bool)
        assert descriptor.attributes["deprecated_field"] is None
        assert isinstance(descriptor.attributes["hosts"], list)
        assert isinstance(descriptor.attributes["config"], dict)

    def test_attributes_accept_list_with_mixed_types(
        self, valid_descriptor_kwargs: dict
    ) -> None:
        """Test that lists with mixed JSON types work in attributes."""
        descriptor = ModelProviderDescriptor(
            **valid_descriptor_kwargs,
            attributes={
                "mixed_list": [
                    "string",
                    42,
                    3.14,
                    True,
                    None,
                    {"key": "value"},
                    ["nested", "list"],
                ],
            },
        )

        mixed = descriptor.attributes["mixed_list"]
        assert mixed[0] == "string"
        assert mixed[1] == 42
        assert mixed[2] == 3.14
        assert mixed[3] is True
        assert mixed[4] is None
        assert mixed[5] == {"key": "value"}
        assert mixed[6] == ["nested", "list"]

    def test_attributes_preserved_in_serialization_roundtrip(
        self, valid_descriptor_kwargs: dict
    ) -> None:
        """Test that attributes survive JSON serialization roundtrip."""
        original = ModelProviderDescriptor(
            **valid_descriptor_kwargs,
            attributes={
                "string": "value",
                "int": 42,
                "float": 3.14,
                "bool": True,
                "null": None,
                "list": [1, 2, 3],
                "dict": {"nested": "value"},
            },
        )

        # Roundtrip through JSON
        json_str = original.model_dump_json()
        restored = ModelProviderDescriptor.model_validate_json(json_str)

        assert restored.attributes == original.attributes

    def test_attributes_preserved_in_model_dump_roundtrip(
        self, valid_descriptor_kwargs: dict
    ) -> None:
        """Test that attributes survive model_dump/validate roundtrip."""
        original = ModelProviderDescriptor(
            **valid_descriptor_kwargs,
            attributes={
                "complex": {
                    "nested": {
                        "values": [1, 2, {"deep": True}],
                    },
                },
            },
        )

        # Roundtrip through dict
        data = original.model_dump()
        restored = ModelProviderDescriptor(**data)

        assert restored.attributes == original.attributes


@pytest.mark.unit
class TestModelProviderDescriptorImmutability:
    """Tests for ModelProviderDescriptor frozen immutability."""

    def test_frozen_model_cannot_be_modified(
        self, valid_descriptor_kwargs: dict
    ) -> None:
        """Test that fields cannot be modified after creation."""
        descriptor = ModelProviderDescriptor(**valid_descriptor_kwargs)

        with pytest.raises(ValidationError, match="frozen"):
            descriptor.provider_id = TEST_UUID_2  # type: ignore[misc]

    def test_frozen_model_capabilities_cannot_be_modified(
        self, valid_descriptor_kwargs: dict
    ) -> None:
        """Test that capabilities list cannot be modified."""
        descriptor = ModelProviderDescriptor(**valid_descriptor_kwargs)

        with pytest.raises(ValidationError, match="frozen"):
            descriptor.capabilities = ["new.capability"]  # type: ignore[misc]

    def test_extra_fields_rejected(self) -> None:
        """Test that extra fields are rejected (extra='forbid')."""
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            ModelProviderDescriptor(
                provider_id=uuid4(),
                capabilities=["database.relational"],
                adapter="test.Adapter",
                connection_ref="secrets://test",
                extra_field="should_fail",  # type: ignore[call-arg]
            )


@pytest.mark.unit
class TestModelProviderDescriptorSerialization:
    """Tests for ModelProviderDescriptor serialization."""

    def test_model_dump_roundtrip(self) -> None:
        """Test serialization and deserialization roundtrip."""
        ModelHealthStatus = _get_health_status_class()
        health = ModelHealthStatus.create_healthy(score=1.0)
        original = ModelProviderDescriptor(
            provider_id=TEST_UUID,
            capabilities=["database.relational", "database.postgresql"],
            adapter="omnibase_infra.adapters.PostgresAdapter",
            connection_ref="secrets://postgres/primary",
            attributes={"version": "15.4"},
            declared_features={"supports_json": True},
            observed_features={"connection_count": 25},
            tags=["production", "primary"],
            health=health,
        )

        data = original.model_dump()
        restored = ModelProviderDescriptor(**data)

        assert restored.provider_id == original.provider_id
        assert restored.capabilities == original.capabilities
        assert restored.adapter == original.adapter
        assert restored.connection_ref == original.connection_ref
        assert restored.attributes == original.attributes
        assert restored.declared_features == original.declared_features
        assert restored.observed_features == original.observed_features
        assert restored.tags == original.tags
        assert restored.health is not None
        # After roundtrip, health is restored as a dict (due to Any type at runtime)
        # Check the data is preserved correctly
        if isinstance(restored.health, dict):
            assert restored.health["status"] == "healthy"
        else:
            assert restored.health.status == "healthy"

    def test_model_dump_minimal(self, valid_descriptor_kwargs: dict) -> None:
        """Test model_dump with minimal fields."""
        descriptor = ModelProviderDescriptor(**valid_descriptor_kwargs)
        data = descriptor.model_dump()

        # model_dump() returns UUID object (not string)
        assert data["provider_id"] == TEST_UUID
        assert data["capabilities"] == ["database.relational"]
        assert data["adapter"] == "test.adapters.TestAdapter"
        assert data["connection_ref"] == "secrets://test/connection"
        assert data["attributes"] == {}
        assert data["declared_features"] == {}
        assert data["observed_features"] == {}
        assert data["tags"] == []
        assert data["health"] is None

    def test_json_serialization(self, valid_descriptor_kwargs: dict) -> None:
        """Test JSON serialization and deserialization."""
        original = ModelProviderDescriptor(
            **valid_descriptor_kwargs,
            tags=["test"],
            declared_features={"enabled": True},
        )

        json_str = original.model_dump_json()
        restored = ModelProviderDescriptor.model_validate_json(json_str)

        assert restored.provider_id == original.provider_id
        assert restored.capabilities == original.capabilities
        assert restored.tags == original.tags
        assert restored.declared_features == original.declared_features


@pytest.mark.unit
class TestModelProviderDescriptorRepr:
    """Tests for ModelProviderDescriptor string representation."""

    def test_repr_shows_provider_id_and_capabilities_count(
        self, valid_descriptor_kwargs: dict
    ) -> None:
        """Test repr shows provider_id and capabilities count."""
        descriptor = ModelProviderDescriptor(**valid_descriptor_kwargs)
        repr_str = repr(descriptor)

        assert "ModelProviderDescriptor" in repr_str
        # UUID repr includes the UUID('...') format
        assert "12345678-1234-5678-1234-567812345678" in repr_str
        assert "capabilities=1" in repr_str

    def test_repr_with_multiple_capabilities(self) -> None:
        """Test repr with multiple capabilities shows correct count."""
        descriptor = ModelProviderDescriptor(
            provider_id=TEST_UUID_2,
            capabilities=["a.b", "c.d", "e.f"],
            adapter="test.Adapter",
            connection_ref="env://TEST",
        )
        repr_str = repr(descriptor)

        # UUID repr includes the UUID('...') format
        assert "87654321-4321-8765-4321-876543218765" in repr_str
        assert "capabilities=3" in repr_str


@pytest.mark.unit
class TestModelProviderDescriptorCapabilityMatching:
    """Tests for capability matching utility methods."""

    def test_has_capability_exact_match(self) -> None:
        """Test has_capability returns True for exact match."""
        descriptor = ModelProviderDescriptor(
            provider_id=uuid4(),
            capabilities=["database.relational", "database.postgresql"],
            adapter="test.Adapter",
            connection_ref="env://TEST",
        )

        assert descriptor.has_capability("database.relational") is True
        assert descriptor.has_capability("database.postgresql") is True

    def test_has_capability_no_match(self) -> None:
        """Test has_capability returns False when capability not present."""
        descriptor = ModelProviderDescriptor(
            provider_id=uuid4(),
            capabilities=["database.relational", "database.postgresql"],
            adapter="test.Adapter",
            connection_ref="env://TEST",
        )

        assert descriptor.has_capability("cache.redis") is False
        assert descriptor.has_capability("database.mysql") is False

    def test_has_capability_partial_match_not_matched(self) -> None:
        """Test has_capability does not match partial strings."""
        descriptor = ModelProviderDescriptor(
            provider_id=uuid4(),
            capabilities=["database.relational"],
            adapter="test.Adapter",
            connection_ref="env://TEST",
        )

        # Partial matches should not work with has_capability
        assert descriptor.has_capability("database") is False
        assert descriptor.has_capability("relational") is False
        assert descriptor.has_capability("database.rel") is False

    def test_matches_any_capability_wildcard_patterns(self) -> None:
        """Test matches_any_capability with wildcard patterns."""
        descriptor = ModelProviderDescriptor(
            provider_id=uuid4(),
            capabilities=["database.relational", "database.postgresql"],
            adapter="test.Adapter",
            connection_ref="env://TEST",
        )

        # Wildcard should match all database capabilities
        assert descriptor.matches_any_capability(["database.*"]) is True

        # Multiple patterns, one matches
        assert descriptor.matches_any_capability(["cache.*", "database.*"]) is True

    def test_matches_any_capability_exact_patterns(self) -> None:
        """Test matches_any_capability with exact patterns (no wildcards)."""
        descriptor = ModelProviderDescriptor(
            provider_id=uuid4(),
            capabilities=["database.relational", "database.postgresql"],
            adapter="test.Adapter",
            connection_ref="env://TEST",
        )

        # Exact match should work
        assert descriptor.matches_any_capability(["database.relational"]) is True
        assert descriptor.matches_any_capability(["database.postgresql"]) is True

    def test_matches_any_capability_no_matches(self) -> None:
        """Test matches_any_capability returns False when no patterns match."""
        descriptor = ModelProviderDescriptor(
            provider_id=uuid4(),
            capabilities=["database.relational", "database.postgresql"],
            adapter="test.Adapter",
            connection_ref="env://TEST",
        )

        assert descriptor.matches_any_capability(["cache.*"]) is False
        assert descriptor.matches_any_capability(["storage.s3"]) is False
        assert descriptor.matches_any_capability(["messaging.*", "queue.*"]) is False

    def test_matches_any_capability_empty_patterns(self) -> None:
        """Test matches_any_capability returns False for empty patterns list."""
        descriptor = ModelProviderDescriptor(
            provider_id=uuid4(),
            capabilities=["database.relational", "database.postgresql"],
            adapter="test.Adapter",
            connection_ref="env://TEST",
        )

        assert descriptor.matches_any_capability([]) is False

    def test_matches_any_capability_complex_wildcards(self) -> None:
        """Test matches_any_capability with complex wildcard patterns."""
        descriptor = ModelProviderDescriptor(
            provider_id=uuid4(),
            capabilities=["storage.s3.us.east.1", "database.postgresql.cluster"],
            adapter="test.Adapter",
            connection_ref="env://TEST",
        )

        # Wildcards at different positions
        assert descriptor.matches_any_capability(["storage.s3.*"]) is True
        assert descriptor.matches_any_capability(["*.cluster"]) is True
        assert descriptor.matches_any_capability(["storage.*.*.*"]) is True

        # Pattern that doesn't match
        assert descriptor.matches_any_capability(["storage.s3.us.west.*"]) is False

    def test_matches_any_capability_question_mark_wildcard(self) -> None:
        """Test matches_any_capability with ? wildcard (matches single char)."""
        descriptor = ModelProviderDescriptor(
            provider_id=uuid4(),
            capabilities=["database.v1", "database.v2", "database.v10"],
            adapter="test.Adapter",
            connection_ref="env://TEST",
        )

        # ? matches exactly one character
        assert descriptor.matches_any_capability(["database.v?"]) is True
        # v10 has two chars after v, so v? shouldn't match it alone
        # but v1 and v2 should match
        assert descriptor.matches_any_capability(["database.v?"]) is True

    def test_matches_any_capability_mixed_patterns(self) -> None:
        """Test matches_any_capability with mix of wildcard and exact patterns."""
        descriptor = ModelProviderDescriptor(
            provider_id=uuid4(),
            capabilities=["database.relational", "cache.redis"],
            adapter="test.Adapter",
            connection_ref="env://TEST",
        )

        # Mix of patterns - first doesn't match, second does
        assert descriptor.matches_any_capability(["storage.s3", "cache.redis"]) is True

        # Mix of patterns - wildcards and exact, one matches
        assert (
            descriptor.matches_any_capability(["messaging.*", "database.relational"])
            is True
        )
