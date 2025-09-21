"""
UUID Helper Utilities.

Provides deterministic UUID generation for entity transformation.
"""

import hashlib
from uuid import UUID


def uuid_from_string(input_string: str, namespace: str = "omnibase") -> UUID:
    """
    Generate deterministic UUID from string using SHA-256.

    Args:
        input_string: The string to convert to UUID
        namespace: Namespace prefix for uniqueness

    Returns:
        Deterministic UUID based on input string
    """
    # Create deterministic string with namespace
    combined_string = f"{namespace}:{input_string}"

    # Generate SHA-256 hash
    hash_object = hashlib.sha256(combined_string.encode("utf-8"))
    hex_digest = hash_object.hexdigest()

    # Use first 32 characters to create UUID
    uuid_hex = hex_digest[:32]

    # Format as UUID (8-4-4-4-12)
    formatted_uuid = f"{uuid_hex[:8]}-{uuid_hex[8:12]}-{uuid_hex[12:16]}-{uuid_hex[16:20]}-{uuid_hex[20:32]}"

    return UUID(formatted_uuid)


# Export utility
__all__ = ["uuid_from_string"]
