"""Effect type enumeration for side effect operations."""

from enum import Enum, unique


@unique
class EnumEffectType(Enum):
    """Types of side effects that can be managed."""

    FILE_OPERATION = "file_operation"
    DATABASE_OPERATION = "database_operation"
    API_CALL = "api_call"
    EVENT_EMISSION = "event_emission"
    DIRECTORY_OPERATION = "directory_operation"
    TICKET_STORAGE = "ticket_storage"
    METRICS_COLLECTION = "metrics_collection"
