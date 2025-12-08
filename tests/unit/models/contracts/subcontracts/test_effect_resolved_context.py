"""
Unit tests for Effect Resolved Context Models - ONEX Standards Compliant.

Comprehensive test coverage for resolved context models including:
- Basic model instantiation and field validation
- Frozen model behavior (immutability)
- Extra field rejection (extra="forbid")
- Union type acceptance
- Handler type discrimination
- Edge cases and boundary conditions

VERSION: 1.0.0 - Tests for Contract-Driven NodeEffect resolved contexts (OMN-523)
"""

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_effect_handler_type import EnumEffectHandlerType
from omnibase_core.models.contracts.subcontracts.model_effect_resolved_context import (
    ModelResolvedDbContext,
    ModelResolvedFilesystemContext,
    ModelResolvedHttpContext,
    ModelResolvedKafkaContext,
    ResolvedIOContext,
)


class TestModelResolvedHttpContext:
    """Test ModelResolvedHttpContext creation and validation."""

    def test_basic_creation(self) -> None:
        """Test basic HTTP context creation with required fields."""
        context = ModelResolvedHttpContext(
            url="https://api.example.com/users/123",
            method="GET",
        )

        assert context.url == "https://api.example.com/users/123"
        assert context.method == "GET"
        assert context.handler_type == EnumEffectHandlerType.HTTP
        assert context.headers == {}
        assert context.body is None
        assert context.query_params == {}
        assert context.timeout_ms == 30000
        assert context.follow_redirects is True
        assert context.verify_ssl is True

    def test_full_creation(self) -> None:
        """Test HTTP context with all fields specified."""
        context = ModelResolvedHttpContext(
            url="https://api.example.com/users",
            method="POST",
            headers={"Authorization": "Bearer token123", "Content-Type": "application/json"},
            body='{"name": "John", "email": "john@example.com"}',
            query_params={"page": "1", "limit": "10"},
            timeout_ms=60000,
            follow_redirects=False,
            verify_ssl=False,
        )

        assert context.method == "POST"
        assert context.headers["Authorization"] == "Bearer token123"
        assert context.body is not None
        assert context.query_params["page"] == "1"
        assert context.timeout_ms == 60000
        assert context.follow_redirects is False
        assert context.verify_ssl is False

    def test_all_http_methods(self) -> None:
        """Test all supported HTTP methods."""
        for method in ["GET", "POST", "PUT", "PATCH", "DELETE"]:
            context = ModelResolvedHttpContext(
                url="https://api.example.com/resource",
                method=method,  # type: ignore[arg-type]
            )
            assert context.method == method

    def test_invalid_http_method(self) -> None:
        """Test that invalid HTTP methods are rejected."""
        with pytest.raises(ValidationError):
            ModelResolvedHttpContext(
                url="https://api.example.com/resource",
                method="INVALID",  # type: ignore[arg-type]
            )

    def test_url_required(self) -> None:
        """Test that URL is required."""
        with pytest.raises(ValidationError):
            ModelResolvedHttpContext(method="GET")  # type: ignore[call-arg]

    def test_empty_url_rejected(self) -> None:
        """Test that empty URL is rejected."""
        with pytest.raises(ValidationError):
            ModelResolvedHttpContext(url="", method="GET")

    def test_timeout_bounds(self) -> None:
        """Test timeout_ms bounds validation."""
        # Valid minimum
        context = ModelResolvedHttpContext(
            url="https://example.com", method="GET", timeout_ms=100
        )
        assert context.timeout_ms == 100

        # Valid maximum
        context = ModelResolvedHttpContext(
            url="https://example.com", method="GET", timeout_ms=600000
        )
        assert context.timeout_ms == 600000

        # Below minimum
        with pytest.raises(ValidationError):
            ModelResolvedHttpContext(
                url="https://example.com", method="GET", timeout_ms=99
            )

        # Above maximum
        with pytest.raises(ValidationError):
            ModelResolvedHttpContext(
                url="https://example.com", method="GET", timeout_ms=600001
            )

    def test_frozen_prevents_modification(self) -> None:
        """Test that frozen=True prevents attribute modification."""
        context = ModelResolvedHttpContext(
            url="https://example.com", method="GET"
        )

        with pytest.raises(ValidationError):
            context.url = "https://other.com"  # type: ignore[misc]

        with pytest.raises(ValidationError):
            context.method = "POST"  # type: ignore[misc]

    def test_extra_fields_forbidden(self) -> None:
        """Test that extra fields are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelResolvedHttpContext(
                url="https://example.com",
                method="GET",
                unknown_field="should_fail",  # type: ignore[call-arg]
            )
        assert "Extra inputs are not permitted" in str(exc_info.value)


class TestModelResolvedDbContext:
    """Test ModelResolvedDbContext creation and validation."""

    def test_basic_creation(self) -> None:
        """Test basic DB context creation with required fields."""
        context = ModelResolvedDbContext(
            operation="select",
            connection_name="primary_db",
            query="SELECT * FROM users WHERE id = $1",
        )

        assert context.operation == "select"
        assert context.connection_name == "primary_db"
        assert context.query == "SELECT * FROM users WHERE id = $1"
        assert context.handler_type == EnumEffectHandlerType.DB
        assert context.params == []
        assert context.timeout_ms == 30000
        assert context.fetch_size is None
        assert context.read_only is False

    def test_full_creation(self) -> None:
        """Test DB context with all fields specified."""
        context = ModelResolvedDbContext(
            operation="insert",
            connection_name="replica_db",
            query="INSERT INTO users (name, age, active) VALUES ($1, $2, $3)",
            params=["John", 30, True],
            timeout_ms=10000,
            fetch_size=100,
            read_only=False,
        )

        assert context.operation == "insert"
        assert context.params == ["John", 30, True]
        assert context.fetch_size == 100

    def test_all_operations(self) -> None:
        """Test all supported database operations."""
        for op in ["select", "insert", "update", "delete", "upsert", "raw"]:
            context = ModelResolvedDbContext(
                operation=op,  # type: ignore[arg-type]
                connection_name="db",
                query="QUERY",
            )
            assert context.operation == op

    def test_invalid_operation(self) -> None:
        """Test that invalid operations are rejected."""
        with pytest.raises(ValidationError):
            ModelResolvedDbContext(
                operation="drop",  # type: ignore[arg-type]
                connection_name="db",
                query="DROP TABLE users",
            )

    def test_params_with_various_types(self) -> None:
        """Test params accepts all supported types."""
        context = ModelResolvedDbContext(
            operation="select",
            connection_name="db",
            query="SELECT * FROM table WHERE a=$1 AND b=$2 AND c=$3 AND d=$4 AND e=$5",
            params=["string", 123, 45.67, True, None],
        )

        assert context.params[0] == "string"
        assert context.params[1] == 123
        assert context.params[2] == 45.67
        assert context.params[3] is True
        assert context.params[4] is None

    def test_empty_connection_name_rejected(self) -> None:
        """Test that empty connection_name is rejected."""
        with pytest.raises(ValidationError):
            ModelResolvedDbContext(
                operation="select",
                connection_name="",
                query="SELECT 1",
            )

    def test_empty_query_rejected(self) -> None:
        """Test that empty query is rejected."""
        with pytest.raises(ValidationError):
            ModelResolvedDbContext(
                operation="select",
                connection_name="db",
                query="",
            )

    def test_frozen_prevents_modification(self) -> None:
        """Test that frozen=True prevents attribute modification."""
        context = ModelResolvedDbContext(
            operation="select",
            connection_name="db",
            query="SELECT 1",
        )

        with pytest.raises(ValidationError):
            context.query = "SELECT 2"  # type: ignore[misc]

    def test_extra_fields_forbidden(self) -> None:
        """Test that extra fields are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelResolvedDbContext(
                operation="select",
                connection_name="db",
                query="SELECT 1",
                database_name="extra",  # type: ignore[call-arg]
            )
        assert "Extra inputs are not permitted" in str(exc_info.value)


class TestModelResolvedKafkaContext:
    """Test ModelResolvedKafkaContext creation and validation."""

    def test_basic_creation(self) -> None:
        """Test basic Kafka context creation with required fields."""
        context = ModelResolvedKafkaContext(
            topic="user-events",
            payload='{"event": "user_created", "user_id": 123}',
        )

        assert context.topic == "user-events"
        assert context.payload == '{"event": "user_created", "user_id": 123}'
        assert context.handler_type == EnumEffectHandlerType.KAFKA
        assert context.partition_key is None
        assert context.headers == {}
        assert context.timeout_ms == 30000
        assert context.acks == "all"
        assert context.compression == "none"

    def test_full_creation(self) -> None:
        """Test Kafka context with all fields specified."""
        context = ModelResolvedKafkaContext(
            topic="orders",
            partition_key="order-123",
            headers={"correlation-id": "abc", "source": "checkout"},
            payload='{"order_id": "123", "amount": 99.99}',
            timeout_ms=5000,
            acks="1",
            compression="gzip",
        )

        assert context.partition_key == "order-123"
        assert context.headers["correlation-id"] == "abc"
        assert context.acks == "1"
        assert context.compression == "gzip"

    def test_all_acks_values(self) -> None:
        """Test all supported acks values."""
        for acks in ["0", "1", "all"]:
            context = ModelResolvedKafkaContext(
                topic="test",
                payload="data",
                acks=acks,  # type: ignore[arg-type]
            )
            assert context.acks == acks

    def test_invalid_acks(self) -> None:
        """Test that invalid acks values are rejected."""
        with pytest.raises(ValidationError):
            ModelResolvedKafkaContext(
                topic="test",
                payload="data",
                acks="2",  # type: ignore[arg-type]
            )

    def test_all_compression_values(self) -> None:
        """Test all supported compression values."""
        for compression in ["none", "gzip", "snappy", "lz4", "zstd"]:
            context = ModelResolvedKafkaContext(
                topic="test",
                payload="data",
                compression=compression,  # type: ignore[arg-type]
            )
            assert context.compression == compression

    def test_invalid_compression(self) -> None:
        """Test that invalid compression values are rejected."""
        with pytest.raises(ValidationError):
            ModelResolvedKafkaContext(
                topic="test",
                payload="data",
                compression="bzip2",  # type: ignore[arg-type]
            )

    def test_empty_topic_rejected(self) -> None:
        """Test that empty topic is rejected."""
        with pytest.raises(ValidationError):
            ModelResolvedKafkaContext(
                topic="",
                payload="data",
            )

    def test_frozen_prevents_modification(self) -> None:
        """Test that frozen=True prevents attribute modification."""
        context = ModelResolvedKafkaContext(
            topic="test",
            payload="data",
        )

        with pytest.raises(ValidationError):
            context.topic = "other"  # type: ignore[misc]

    def test_extra_fields_forbidden(self) -> None:
        """Test that extra fields are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelResolvedKafkaContext(
                topic="test",
                payload="data",
                consumer_group="extra",  # type: ignore[call-arg]
            )
        assert "Extra inputs are not permitted" in str(exc_info.value)


class TestModelResolvedFilesystemContext:
    """Test ModelResolvedFilesystemContext creation and validation."""

    def test_basic_creation(self) -> None:
        """Test basic filesystem context creation with required fields."""
        context = ModelResolvedFilesystemContext(
            file_path="/data/exports/report.csv",
            operation="read",
        )

        assert context.file_path == "/data/exports/report.csv"
        assert context.operation == "read"
        assert context.handler_type == EnumEffectHandlerType.FILESYSTEM
        assert context.content is None
        assert context.timeout_ms == 30000
        assert context.atomic is True
        assert context.create_dirs is True
        assert context.encoding == "utf-8"
        assert context.mode is None

    def test_full_creation(self) -> None:
        """Test filesystem context with all fields specified."""
        context = ModelResolvedFilesystemContext(
            file_path="/tmp/output.json",
            operation="write",
            content='{"status": "success"}',
            timeout_ms=10000,
            atomic=False,
            create_dirs=False,
            encoding="latin-1",
            mode="0644",
        )

        assert context.content == '{"status": "success"}'
        assert context.atomic is False
        assert context.create_dirs is False
        assert context.encoding == "latin-1"
        assert context.mode == "0644"

    def test_all_operations(self) -> None:
        """Test all supported filesystem operations."""
        for op in ["read", "write", "delete", "move", "copy"]:
            context = ModelResolvedFilesystemContext(
                file_path="/test/file.txt",
                operation=op,  # type: ignore[arg-type]
            )
            assert context.operation == op

    def test_invalid_operation(self) -> None:
        """Test that invalid operations are rejected."""
        with pytest.raises(ValidationError):
            ModelResolvedFilesystemContext(
                file_path="/test/file.txt",
                operation="chmod",  # type: ignore[arg-type]
            )

    def test_empty_file_path_rejected(self) -> None:
        """Test that empty file_path is rejected."""
        with pytest.raises(ValidationError):
            ModelResolvedFilesystemContext(
                file_path="",
                operation="read",
            )

    def test_frozen_prevents_modification(self) -> None:
        """Test that frozen=True prevents attribute modification."""
        context = ModelResolvedFilesystemContext(
            file_path="/test/file.txt",
            operation="read",
        )

        with pytest.raises(ValidationError):
            context.file_path = "/other/file.txt"  # type: ignore[misc]

    def test_extra_fields_forbidden(self) -> None:
        """Test that extra fields are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelResolvedFilesystemContext(
                file_path="/test/file.txt",
                operation="read",
                owner="extra",  # type: ignore[call-arg]
            )
        assert "Extra inputs are not permitted" in str(exc_info.value)


class TestResolvedIOContextUnion:
    """Test ResolvedIOContext union type behavior."""

    def test_union_accepts_http_context(self) -> None:
        """Test union type accepts HTTP context."""
        context: ResolvedIOContext = ModelResolvedHttpContext(
            url="https://example.com",
            method="GET",
        )

        assert isinstance(context, ModelResolvedHttpContext)
        assert context.handler_type == EnumEffectHandlerType.HTTP

    def test_union_accepts_db_context(self) -> None:
        """Test union type accepts DB context."""
        context: ResolvedIOContext = ModelResolvedDbContext(
            operation="select",
            connection_name="db",
            query="SELECT 1",
        )

        assert isinstance(context, ModelResolvedDbContext)
        assert context.handler_type == EnumEffectHandlerType.DB

    def test_union_accepts_kafka_context(self) -> None:
        """Test union type accepts Kafka context."""
        context: ResolvedIOContext = ModelResolvedKafkaContext(
            topic="events",
            payload="data",
        )

        assert isinstance(context, ModelResolvedKafkaContext)
        assert context.handler_type == EnumEffectHandlerType.KAFKA

    def test_union_accepts_filesystem_context(self) -> None:
        """Test union type accepts filesystem context."""
        context: ResolvedIOContext = ModelResolvedFilesystemContext(
            file_path="/test/file.txt",
            operation="read",
        )

        assert isinstance(context, ModelResolvedFilesystemContext)
        assert context.handler_type == EnumEffectHandlerType.FILESYSTEM

    def test_handler_type_discrimination(self) -> None:
        """Test handler type can be used for discrimination."""
        contexts: list[ResolvedIOContext] = [
            ModelResolvedHttpContext(url="https://example.com", method="GET"),
            ModelResolvedDbContext(operation="select", connection_name="db", query="SELECT 1"),
            ModelResolvedKafkaContext(topic="events", payload="data"),
            ModelResolvedFilesystemContext(file_path="/test.txt", operation="read"),
        ]

        handler_types = [ctx.handler_type for ctx in contexts]

        assert handler_types == [
            EnumEffectHandlerType.HTTP,
            EnumEffectHandlerType.DB,
            EnumEffectHandlerType.KAFKA,
            EnumEffectHandlerType.FILESYSTEM,
        ]


class TestModelSerializationDeserialization:
    """Test model serialization and deserialization."""

    def test_http_context_roundtrip(self) -> None:
        """Test HTTP context can be serialized and deserialized."""
        original = ModelResolvedHttpContext(
            url="https://api.example.com/users",
            method="POST",
            headers={"Authorization": "Bearer token"},
            body='{"name": "John"}',
            timeout_ms=15000,
        )

        data = original.model_dump()
        restored = ModelResolvedHttpContext(**data)

        assert restored.url == original.url
        assert restored.method == original.method
        assert restored.headers == original.headers
        assert restored.body == original.body
        assert restored.timeout_ms == original.timeout_ms

    def test_db_context_roundtrip(self) -> None:
        """Test DB context can be serialized and deserialized."""
        original = ModelResolvedDbContext(
            operation="insert",
            connection_name="primary",
            query="INSERT INTO users (name, age) VALUES ($1, $2)",
            params=["John", 30],
            read_only=False,
        )

        data = original.model_dump()
        restored = ModelResolvedDbContext(**data)

        assert restored.operation == original.operation
        assert restored.query == original.query
        assert restored.params == original.params

    def test_kafka_context_roundtrip(self) -> None:
        """Test Kafka context can be serialized and deserialized."""
        original = ModelResolvedKafkaContext(
            topic="user-events",
            partition_key="user-123",
            payload='{"event": "created"}',
            acks="all",
            compression="gzip",
        )

        data = original.model_dump()
        restored = ModelResolvedKafkaContext(**data)

        assert restored.topic == original.topic
        assert restored.partition_key == original.partition_key
        assert restored.payload == original.payload
        assert restored.acks == original.acks
        assert restored.compression == original.compression

    def test_filesystem_context_roundtrip(self) -> None:
        """Test filesystem context can be serialized and deserialized."""
        original = ModelResolvedFilesystemContext(
            file_path="/data/output.csv",
            operation="write",
            content="header1,header2\nvalue1,value2",
            encoding="utf-8",
            mode="0644",
        )

        data = original.model_dump()
        restored = ModelResolvedFilesystemContext(**data)

        assert restored.file_path == original.file_path
        assert restored.operation == original.operation
        assert restored.content == original.content
        assert restored.encoding == original.encoding
        assert restored.mode == original.mode


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_http_context_with_special_characters_in_url(self) -> None:
        """Test HTTP context handles special characters in URL."""
        context = ModelResolvedHttpContext(
            url="https://api.example.com/search?q=hello%20world&filter=a%3Db",
            method="GET",
        )
        assert "%20" in context.url

    def test_db_context_with_empty_params(self) -> None:
        """Test DB context with empty params list."""
        context = ModelResolvedDbContext(
            operation="select",
            connection_name="db",
            query="SELECT * FROM config",
            params=[],
        )
        assert context.params == []

    def test_kafka_context_with_empty_payload(self) -> None:
        """Test Kafka context with empty string payload."""
        context = ModelResolvedKafkaContext(
            topic="heartbeat",
            payload="",
        )
        assert context.payload == ""

    def test_filesystem_context_write_without_content(self) -> None:
        """Test filesystem write operation with None content (creates empty file)."""
        context = ModelResolvedFilesystemContext(
            file_path="/test/empty.txt",
            operation="write",
            content=None,
        )
        assert context.content is None

    def test_all_contexts_have_consistent_timeout_bounds(self) -> None:
        """Test all contexts use same timeout bounds."""
        min_timeout = 100
        max_timeout = 600000

        # HTTP
        http_ctx = ModelResolvedHttpContext(
            url="https://example.com", method="GET", timeout_ms=min_timeout
        )
        assert http_ctx.timeout_ms == min_timeout

        # DB
        db_ctx = ModelResolvedDbContext(
            operation="select",
            connection_name="db",
            query="SELECT 1",
            timeout_ms=max_timeout,
        )
        assert db_ctx.timeout_ms == max_timeout

        # Kafka
        kafka_ctx = ModelResolvedKafkaContext(
            topic="test", payload="data", timeout_ms=min_timeout
        )
        assert kafka_ctx.timeout_ms == min_timeout

        # Filesystem
        fs_ctx = ModelResolvedFilesystemContext(
            file_path="/test.txt", operation="read", timeout_ms=max_timeout
        )
        assert fs_ctx.timeout_ms == max_timeout
