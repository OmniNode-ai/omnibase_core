from enum import Enum


class EnumHandlerType(str, Enum):
    """Handler type classification for the ONEX handler registry.

    This enum classifies handlers by the type of I/O or external system
    they interact with. Used by the handler registry in omnibase_infra
    to organize and retrieve handlers.

    Abstract Types (legacy, for backwards compatibility):
        EXTENSION: Handlers that work with file extensions
        SPECIAL: Handlers for special cases
        NAMED: Handlers identified by specific names

    Concrete Handler Types (v0.3.6+):
        HTTP: HTTP/REST API handlers for web service communication
        DATABASE: Relational database handlers (PostgreSQL, MySQL, etc.)
        KAFKA: Apache Kafka message queue handlers
        FILESYSTEM: File system handlers for local/remote file operations
        VAULT: Secret management handlers (HashiCorp Vault, etc.)
        VECTOR_STORE: Vector database handlers (Qdrant, Pinecone, etc.)
        GRAPH_DATABASE: Graph database handlers (Memgraph, Neo4j, etc.)
        REDIS: Redis cache and data structure handlers
        EVENT_BUS: Event bus handlers for pub/sub messaging

    .. versionchanged:: 0.3.6
        Added concrete handler types (HTTP, DATABASE, KAFKA, etc.)
    """

    # Abstract/legacy types (backwards compatibility)
    EXTENSION = "extension"
    SPECIAL = "special"
    NAMED = "named"

    # Concrete handler types (v0.3.6+)
    HTTP = "http"
    """HTTP/REST API handlers for web service communication."""

    DATABASE = "database"
    """Relational database handlers (PostgreSQL, MySQL, etc.)."""

    KAFKA = "kafka"
    """Apache Kafka message queue handlers."""

    FILESYSTEM = "filesystem"
    """File system handlers for local/remote file operations."""

    VAULT = "vault"
    """Secret management handlers (HashiCorp Vault, etc.)."""

    VECTOR_STORE = "vector_store"
    """Vector database handlers (Qdrant, Pinecone, etc.)."""

    GRAPH_DATABASE = "graph_database"
    """Graph database handlers (Memgraph, Neo4j, etc.)."""

    REDIS = "redis"
    """Redis cache and data structure handlers."""

    EVENT_BUS = "event_bus"
    """Event bus handlers for pub/sub messaging."""
