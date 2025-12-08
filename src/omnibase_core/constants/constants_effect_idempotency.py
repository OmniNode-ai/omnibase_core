"""
Effect idempotency defaults - ONEX Standards Compliant.

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

# Default idempotency by handler type and operation
IDEMPOTENCY_DEFAULTS: dict[str, dict[str, bool]] = {
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

__all__ = ["IDEMPOTENCY_DEFAULTS"]
