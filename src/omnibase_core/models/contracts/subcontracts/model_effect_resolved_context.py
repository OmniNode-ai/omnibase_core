"""
Resolved Context Models for NodeEffect Handler Contract.



These models represent resolved (template-free) contexts that handlers receive
after template resolution by the effect executor.

CRITICAL DESIGN PRINCIPLES:
- Handler Contract: Handlers MUST NOT perform template resolution
- Single Responsibility: Template resolution happens in ONE place (effect_executor.py)
- Retry Semantics: Templates are resolved INSIDE retry loop (secrets refresh, env changes)
- Type Safety: Resolved contexts have stricter types (e.g., url: str not url_template: str)
- Immutability: All contexts are frozen after creation (no runtime modification)

These models are passed to specialized handlers after the executor resolves all
template placeholders (${...}) from the configuration layer.

ZERO TOLERANCE: No Any types allowed. No template placeholders in resolved values.

Thread Safety:
    All resolved context models are immutable (frozen=True) after creation,
    making them thread-safe for concurrent read access. Handlers can safely
    receive and process these contexts from multiple async tasks.

See Also:
    - :mod:`omnibase_core.models.contracts.subcontracts.model_effect_io_configs`:
        IO configuration models with template placeholders
    - :class:`MixinEffectExecution`: Mixin that performs template resolution
    - :class:`NodeEffect`: The primary node using resolved contexts
    - docs/architecture/CONTRACT_DRIVEN_NODEEFFECT_V1_0.md: Full specification
    - docs/guides/THREADING.md: Thread safety guidelines

Author: ONEX Framework Team
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.constants.constants_effect_limits import (
    EFFECT_TIMEOUT_DEFAULT_MS,
    EFFECT_TIMEOUT_MAX_MS,
    EFFECT_TIMEOUT_MIN_MS,
)
from omnibase_core.enums.enum_effect_handler_type import EnumEffectHandlerType

__all__ = [
    "ModelResolvedHttpContext",
    "ModelResolvedDbContext",
    "ModelResolvedKafkaContext",
    "ModelResolvedFilesystemContext",
    "ResolvedIOContext",
]


class ModelResolvedHttpContext(BaseModel):
    """
    Resolved HTTP context for API calls and webhooks.

    All template placeholders have been resolved by the effect executor.
    The handler receives fully-resolved values ready for execution.

    Attributes:
        handler_type: Discriminator field for HTTP handler type.
        url: Fully resolved URL (no template placeholders).
        method: HTTP method for the request (GET, POST, PUT, PATCH, DELETE).
        headers: Resolved HTTP headers (all template values substituted).
        body: Resolved request body (None for GET requests).
        query_params: Resolved query parameters.
        timeout_ms: Request timeout in milliseconds (1s - 10min).
        follow_redirects: Whether to follow HTTP redirects.
        verify_ssl: Whether to verify SSL certificates.

    Example resolved values:
        - url: "https://api.example.com/users/123" (was: "${API_BASE}/users/${user_id}")
        - headers: {"Authorization": "Bearer abc123"} (was: {"Authorization": "Bearer ${API_TOKEN}"})
    """

    handler_type: Literal[EnumEffectHandlerType.HTTP] = Field(
        default=EnumEffectHandlerType.HTTP,
        description="Handler type discriminator for HTTP operations",
    )

    url: str = Field(
        ...,
        min_length=1,
        description="Fully resolved URL (no template placeholders)",
    )

    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"] = Field(
        ...,
        description="HTTP method for the request",
    )

    headers: dict[str, str] = Field(
        default_factory=dict,
        description="Resolved HTTP headers (all template values substituted)",
    )

    body: str | None = Field(
        default=None,
        description="Resolved request body (None for GET requests)",
    )

    query_params: dict[str, str] = Field(
        default_factory=dict,
        description="Resolved query parameters",
    )

    # Timeout bounds: 1s minimum (realistic production I/O), 10min maximum
    # Matches IO config timeout bounds for consistency across the effect layer
    timeout_ms: int = Field(
        default=EFFECT_TIMEOUT_DEFAULT_MS,
        ge=EFFECT_TIMEOUT_MIN_MS,
        le=EFFECT_TIMEOUT_MAX_MS,
        description="Request timeout in milliseconds (1s - 10min)",
    )

    follow_redirects: bool = Field(
        default=True,
        description="Whether to follow HTTP redirects",
    )

    verify_ssl: bool = Field(
        default=True,
        description="Whether to verify SSL certificates",
    )

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        use_enum_values=False,
    )


class ModelResolvedDbContext(BaseModel):
    """
    Resolved database context for SQL operations.

    All template placeholders have been resolved by the effect executor.
    Query parameters are resolved to actual values ready for execution.

    Attributes:
        handler_type: Discriminator field for database handler type.
        operation: Database operation type (select, insert, update, delete, upsert, raw).
        connection_name: Name of the database connection to use.
        query: Fully resolved SQL query (no template placeholders).
        params: Resolved query parameter values in order.
        timeout_ms: Query timeout in milliseconds (1s - 10min).
        fetch_size: Number of rows to fetch per batch (None for default).
        read_only: Whether the operation is read-only (enables optimizations).

    Example resolved values:
        - query: "SELECT * FROM users WHERE id = $1" (was: "${QUERY_TEMPLATE}")
        - params: [123] (was: ["${user_id}"])
    """

    handler_type: Literal[EnumEffectHandlerType.DB] = Field(
        default=EnumEffectHandlerType.DB,
        description="Handler type discriminator for database operations",
    )

    operation: Literal["select", "insert", "update", "delete", "upsert", "raw"] = Field(
        ...,
        description="Database operation type",
    )

    connection_name: str = Field(
        ...,
        min_length=1,
        description="Name of the database connection to use",
    )

    query: str = Field(
        ...,
        min_length=1,
        description="Fully resolved SQL query (no template placeholders)",
    )

    params: list[str | int | float | bool | None] = Field(
        default_factory=list,
        description="Resolved query parameter values in order",
    )

    # Timeout bounds: 1s minimum (realistic production I/O), 10min maximum
    # Matches IO config timeout bounds for consistency across the effect layer
    timeout_ms: int = Field(
        default=EFFECT_TIMEOUT_DEFAULT_MS,
        ge=EFFECT_TIMEOUT_MIN_MS,
        le=EFFECT_TIMEOUT_MAX_MS,
        description="Query timeout in milliseconds (1s - 10min)",
    )

    fetch_size: int | None = Field(
        default=None,
        ge=1,
        description="Number of rows to fetch per batch (None for default)",
    )

    read_only: bool = Field(
        default=False,
        description="Whether the operation is read-only (enables optimizations)",
    )

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        use_enum_values=False,
    )


class ModelResolvedKafkaContext(BaseModel):
    """
    Resolved Kafka context for message queue operations.

    All template placeholders have been resolved by the effect executor.
    Message payload and headers are ready for immediate publishing.

    Attributes:
        handler_type: Discriminator field for Kafka handler type.
        topic: Kafka topic name.
        partition_key: Resolved partition key for message ordering.
        headers: Resolved Kafka message headers.
        payload: Fully resolved message payload.
        timeout_ms: Publish timeout in milliseconds (1s - 10min).
        acks: Acknowledgment level (0=none, 1=leader, all=all replicas).
        compression: Message compression algorithm.

    Example resolved values:
        - topic: "user-events" (was: "${KAFKA_TOPIC_PREFIX}-events")
        - payload: '{"user_id": 123}' (was: '{"user_id": ${user_id}}')
    """

    handler_type: Literal[EnumEffectHandlerType.KAFKA] = Field(
        default=EnumEffectHandlerType.KAFKA,
        description="Handler type discriminator for Kafka operations",
    )

    topic: str = Field(
        ...,
        min_length=1,
        description="Kafka topic name",
    )

    partition_key: str | None = Field(
        default=None,
        description="Resolved partition key for message ordering",
    )

    headers: dict[str, str] = Field(
        default_factory=dict,
        description="Resolved Kafka message headers",
    )

    payload: str = Field(
        ...,
        description="Fully resolved message payload",
    )

    # Timeout bounds: 1s minimum (realistic production I/O), 10min maximum
    # Matches IO config timeout bounds for consistency across the effect layer
    timeout_ms: int = Field(
        default=EFFECT_TIMEOUT_DEFAULT_MS,
        ge=EFFECT_TIMEOUT_MIN_MS,
        le=EFFECT_TIMEOUT_MAX_MS,
        description="Publish timeout in milliseconds (1s - 10min)",
    )

    acks: Literal["0", "1", "all"] = Field(
        default="all",
        description="Acknowledgment level: 0=none, 1=leader, all=all replicas",
    )

    compression: Literal["none", "gzip", "snappy", "lz4", "zstd"] = Field(
        default="none",
        description="Message compression algorithm",
    )

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        use_enum_values=False,
    )


class ModelResolvedFilesystemContext(BaseModel):
    """
    Resolved filesystem context for file and directory operations.

    All template placeholders have been resolved by the effect executor.
    File paths and content are ready for immediate I/O operations.

    Attributes:
        handler_type: Discriminator field for filesystem handler type.
        file_path: Fully resolved file path (no template placeholders).
        operation: Filesystem operation type (read, write, delete, move, copy).
        content: Resolved content for write operations.
        timeout_ms: Operation timeout in milliseconds (1s - 10min).
        atomic: Whether to use atomic write operations (write to temp, then rename).
        create_dirs: Whether to create parent directories if they don't exist.
        encoding: File encoding for text operations.
        mode: Unix file mode (e.g., '0644') for created files.

    Example resolved values:
        - file_path: "/data/exports/report_2024.csv" (was: "${DATA_DIR}/exports/${filename}")
        - content: "id,name,value\\n123,test,100" (was: "${HEADER}\\n${ROW_DATA}")
    """

    handler_type: Literal[EnumEffectHandlerType.FILESYSTEM] = Field(
        default=EnumEffectHandlerType.FILESYSTEM,
        description="Handler type discriminator for filesystem operations",
    )

    file_path: str = Field(
        ...,
        min_length=1,
        description="Fully resolved file path (no template placeholders)",
    )

    operation: Literal["read", "write", "delete", "move", "copy"] = Field(
        ...,
        description="Filesystem operation type",
    )

    content: str | None = Field(
        default=None,
        description="Resolved content for write operations",
    )

    # Timeout bounds: 1s minimum (realistic production I/O), 10min maximum
    # Matches IO config timeout bounds for consistency across the effect layer
    timeout_ms: int = Field(
        default=EFFECT_TIMEOUT_DEFAULT_MS,
        ge=EFFECT_TIMEOUT_MIN_MS,
        le=EFFECT_TIMEOUT_MAX_MS,
        description="Operation timeout in milliseconds (1s - 10min)",
    )

    atomic: bool = Field(
        default=True,
        description="Whether to use atomic write operations (write to temp, then rename)",
    )

    create_dirs: bool = Field(
        default=True,
        description="Whether to create parent directories if they don't exist",
    )

    encoding: str = Field(
        default="utf-8",
        description="File encoding for text operations",
    )

    mode: str | None = Field(
        default=None,
        description="Unix file mode (e.g., '0644') for created files",
    )

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        use_enum_values=False,
    )


# Union type for handler signatures
ResolvedIOContext = (
    ModelResolvedHttpContext
    | ModelResolvedDbContext
    | ModelResolvedKafkaContext
    | ModelResolvedFilesystemContext
)
