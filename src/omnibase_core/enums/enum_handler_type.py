from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumHandlerType(StrValueHelper, str, Enum):
    """Handler type classification for the ONEX handler registry.

    This enum classifies handlers by the type of I/O or external system
    they interact with. Used by the handler registry in omnibase_infra
    to organize and retrieve handlers.

    Location:
        ``omnibase_core.enums.enum_handler_type.EnumHandlerType``

    Import Example:
        .. code-block:: python

            from omnibase_core.enums.enum_handler_type import EnumHandlerType

            # Or via the enums package
            from omnibase_core.enums import EnumHandlerType

    Values:
        **Abstract Types** (foundational handler categories):
            - ``EXTENSION`` ("extension"): Handlers that work with file extensions
            - ``SPECIAL`` ("special"): Handlers for special cases
            - ``NAMED`` ("named"): Handlers identified by specific names

        **Concrete Handler Types** (v0.3.6+):
            - ``HTTP`` ("http"): HTTP/REST API handlers for web service communication
            - ``DATABASE`` ("database"): Relational database handlers (PostgreSQL, MySQL, etc.)
            - ``KAFKA`` ("kafka"): Apache Kafka message queue handlers
            - ``FILESYSTEM`` ("filesystem"): File system handlers for local/remote file operations
            - ``VAULT`` ("vault"): Secret management handlers (HashiCorp Vault, etc.)
            - ``VECTOR_STORE`` ("vector_store"): Vector database handlers (Qdrant, Pinecone, etc.)
            - ``GRAPH_DATABASE`` ("graph_database"): Graph database handlers (Memgraph, Neo4j, etc.)
            - ``REDIS`` ("redis"): Redis cache and data structure handlers
            - ``EVENT_BUS`` ("event_bus"): Event bus handlers for pub/sub messaging

        **Development/Testing Types** (v0.4.0+):
            - ``LOCAL`` ("local"): Local echo handler for dev/test only.
              WARNING: Not for production use.

    See Also:
        - :class:`~omnibase_core.protocols.runtime.protocol_handler.ProtocolHandler`:
          Protocol that uses this enum for handler classification
        - :class:`~omnibase_core.runtime.runtime_envelope_router.EnvelopeRouter`:
          Router that registers handlers by this type

    .. versionchanged:: 0.3.6
        Added concrete handler types (HTTP, DATABASE, KAFKA, etc.)

    .. versionchanged:: 0.4.0
        Added LOCAL handler type for dev/test only.
    """

    # Abstract types (foundational handler categories)
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

    # Development/Testing types (v0.4.0+)
    LOCAL = "local"
    """Local echo handler for dev/test only. WARNING: Not for production use."""


__all__ = ["EnumHandlerType"]
