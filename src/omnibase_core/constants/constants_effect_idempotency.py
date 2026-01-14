"""
Effect idempotency defaults.

Default idempotency settings by handler type and operation.
Used by ModelEffectOperation to determine if an operation is safe to retry.

CRITICAL for retry safety:
- Idempotent operations can be safely retried without causing duplicate side effects
- Non-idempotent operations may cause duplicate side effects if retried

References:
- HTTP RFC 7231: GET, HEAD, OPTIONS, PUT, DELETE are idempotent
- Database semantics: SELECT, UPDATE (same values), DELETE are idempotent
- Kafka: Standard produce is NOT idempotent (use idempotent producer config)
- Filesystem: Read, delete are idempotent; write, move, copy are NOT
"""

from types import MappingProxyType
from typing import Literal

# Type aliases for handler types (used for type-safe lookups)
HandlerType = Literal[  # enum-ok: constant type definition
    "http", "db", "kafka", "filesystem"
]
HttpMethod = Literal["GET", "HEAD", "OPTIONS", "PUT", "DELETE", "POST", "PATCH"]
DbOperation = Literal["SELECT", "INSERT", "UPDATE", "DELETE", "UPSERT"]
KafkaOperation = Literal["produce"]
FilesystemOperation = Literal["read", "write", "delete", "move", "copy"]

# Private mutable dict used only for initialization
_IDEMPOTENCY_DEFAULTS_MUTABLE: dict[HandlerType, dict[str, bool]] = {
    "http": {
        "GET": True,
        "HEAD": True,
        "OPTIONS": True,
        "PUT": True,  # PUT is idempotent by HTTP spec
        "DELETE": True,  # DELETE is idempotent by HTTP spec
        "POST": False,  # POST is NOT idempotent
        "PATCH": False,  # PATCH is NOT idempotent
    },
    "db": {
        "SELECT": True,
        "INSERT": False,  # May create duplicates
        "UPDATE": True,  # Same update = same result
        "DELETE": True,  # Deleting deleted = no-op
        "UPSERT": True,  # Idempotent by design
    },
    "kafka": {
        "produce": False,  # Produces duplicate messages (unless idempotent producer)
    },
    "filesystem": {
        "read": True,
        "write": False,  # Overwrites may corrupt data on retry with different content
        "delete": True,  # Deleting deleted = no-op
        "move": False,  # Source may not exist after first move
        "copy": False,  # Dest may exist after first attempt, causing failure
    },
}

# Immutable nested MappingProxyType - both outer and inner dicts are read-only
# Note: Uses `str` key type for runtime compatibility with dynamic handler lookups
# HandlerType is exported for static type checking when desired
IDEMPOTENCY_DEFAULTS: MappingProxyType[str, MappingProxyType[str, bool]] = (
    MappingProxyType(
        {k: MappingProxyType(v) for k, v in _IDEMPOTENCY_DEFAULTS_MUTABLE.items()}
    )
)

__all__ = [
    "IDEMPOTENCY_DEFAULTS",
    "HandlerType",
    "HttpMethod",
    "DbOperation",
    "KafkaOperation",
    "FilesystemOperation",
]
