"""
Payload size validation utilities for ONEX event publishing.

Provides validation and limits for event payloads to prevent memory issues
in memory-constrained environments.
"""

import json
import logging
from typing import Any

from omnibase_core.core.errors.core_errors import CoreErrorCode, OnexError
from omnibase_core.models.model_publisher_config import ModelPublisherConfig

logger = logging.getLogger(__name__)


def validate_payload_size(
    payload: dict[str, Any] | str | bytes,
    config: ModelPublisherConfig,
    compress_large_payloads: bool = True,
) -> dict[str, Any] | str | bytes:
    """
    Validate and optionally compress payload based on size limits.

    Args:
        payload: Event payload to validate
        config: Publisher configuration with size limits
        compress_large_payloads: Whether to attempt compression for large payloads

    Returns:
        Validated (and possibly compressed) payload

    Raises:
        OnexError: When payload exceeds limits and cannot be compressed
    """
    # Calculate payload size
    if isinstance(payload, dict):
        payload_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        payload_size = len(payload_bytes)
        payload_type = "json"
    elif isinstance(payload, str):
        payload_bytes = payload.encode("utf-8")
        payload_size = len(payload_bytes)
        payload_type = "string"
    elif isinstance(payload, bytes):
        payload_bytes = payload
        payload_size = len(payload_bytes)
        payload_type = "bytes"
    else:
        # Try to serialize as JSON
        try:
            payload_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
            payload_size = len(payload_bytes)
            payload_type = "serialized"
        except (TypeError, ValueError) as e:
            msg = (
                f"Cannot determine payload size for type {type(payload).__name__}: {e}"
            )
            raise OnexError(
                msg,
                error_code=CoreErrorCode.VALIDATION_ERROR,
            ) from e

    max_size = config.max_payload_size_bytes

    # Log payload size for monitoring
    if payload_size > max_size * 0.8:  # Warn when approaching limit
        logger.warning(
            f"Large payload detected: {payload_size:,} bytes ({payload_size/max_size*100:.1f}% of limit)",
        )

    # Check if payload exceeds limit
    if payload_size <= max_size:
        logger.debug(f"Payload size valid: {payload_size:,} bytes ({payload_type})")
        return payload

    # Payload exceeds limit - try compression if enabled
    if compress_large_payloads and payload_type in ["json", "string", "serialized"]:
        compressed_payload = _try_compress_payload(
            payload,
            payload_bytes,
            max_size,
            config,
        )
        if compressed_payload is not None:
            return compressed_payload

    # Cannot compress or compression didn't help enough
    size_mb = payload_size / (1024 * 1024)
    limit_mb = max_size / (1024 * 1024)

    error_msg = (
        f"Payload size ({size_mb:.2f}MB) exceeds limit ({limit_mb:.2f}MB). "
        f"Consider reducing payload size or increasing ONEX_MAX_PAYLOAD_SIZE_KB limit."
    )

    if config.environment == "production":
        # Strict enforcement in production
        raise OnexError(error_msg, error_code=CoreErrorCode.VALIDATION_ERROR)
    # Warning in non-production environments
    logger.warning(f"{error_msg} Allowing in {config.environment} environment.")
    return payload


def _try_compress_payload(
    original_payload: Any,
    payload_bytes: bytes,
    max_size: int,
    config: ModelPublisherConfig,
) -> dict[str, Any] | str | None:
    """
    Try to compress payload using various strategies.

    Args:
        original_payload: Original payload object
        payload_bytes: Serialized payload bytes
        max_size: Maximum allowed size in bytes
        config: Publisher configuration

    Returns:
        Compressed payload if successful, None if compression failed
    """
    import gzip
    import zlib

    # Try different compression methods
    compression_methods = [
        ("gzip", gzip.compress),
        ("zlib", zlib.compress),
    ]

    best_compressed = None
    best_size = len(payload_bytes)
    best_method = None

    for method_name, compress_func in compression_methods:
        try:
            compressed_bytes = compress_func(payload_bytes)
            compressed_size = len(compressed_bytes)

            if compressed_size < best_size:
                best_compressed = compressed_bytes
                best_size = compressed_size
                best_method = method_name

        except Exception as e:
            logger.debug(f"Compression method {method_name} failed: {e}")
            continue

    # Check if best compression is good enough
    if best_compressed and best_size <= max_size:
        compression_ratio = (1 - best_size / len(payload_bytes)) * 100
        logger.info(
            f"Payload compressed with {best_method}: {len(payload_bytes):,} -> {best_size:,} bytes ({compression_ratio:.1f}% reduction)",
        )

        # Return compressed payload with metadata
        if isinstance(original_payload, dict):
            return {
                "__compressed__": True,
                "__compression_method__": best_method,
                "__original_size__": len(payload_bytes),
                "__compressed_data__": best_compressed.hex(),  # Hex encode for JSON safety
            }
        # For non-dict payloads, return as compressed string
        return f"__COMPRESSED__{best_method}__{best_compressed.hex()}__"

    return None


def estimate_memory_usage(
    payload_count: int,
    average_payload_size: int,
    overhead_factor: float = 1.5,
) -> int:
    """
    Estimate memory usage for a given number of payloads.

    Args:
        payload_count: Number of payloads in memory
        average_payload_size: Average size per payload in bytes
        overhead_factor: Memory overhead factor (default 1.5 for 50% overhead)

    Returns:
        Estimated memory usage in bytes
    """
    return int(payload_count * average_payload_size * overhead_factor)


def calculate_max_concurrent_events(
    max_memory_bytes: int,
    max_payload_size_bytes: int,
    overhead_factor: float = 1.5,
) -> int:
    """
    Calculate maximum number of concurrent events based on memory constraints.

    Args:
        max_memory_bytes: Maximum available memory in bytes
        max_payload_size_bytes: Maximum payload size in bytes
        overhead_factor: Memory overhead factor for processing

    Returns:
        Maximum number of concurrent events
    """
    memory_per_event = int(max_payload_size_bytes * overhead_factor)
    max_events = max_memory_bytes // memory_per_event
    return max(1, max_events)  # Always allow at least 1 event


def get_payload_size_recommendations(environment: str) -> dict[str, int]:
    """
    Get recommended payload size limits for different environments.

    Args:
        environment: Deployment environment

    Returns:
        Dictionary with recommended size limits in bytes
    """
    recommendations = {
        "development": {
            "max_payload_kb": 5120,  # 5MB
            "warning_threshold_kb": 4096,  # 4MB
            "compress_threshold_kb": 2048,  # 2MB
        },
        "test": {
            "max_payload_kb": 2048,  # 2MB
            "warning_threshold_kb": 1536,  # 1.5MB
            "compress_threshold_kb": 1024,  # 1MB
        },
        "staging": {
            "max_payload_kb": 1024,  # 1MB
            "warning_threshold_kb": 768,  # 768KB
            "compress_threshold_kb": 512,  # 512KB
        },
        "production": {
            "max_payload_kb": 1024,  # 1MB
            "warning_threshold_kb": 512,  # 512KB
            "compress_threshold_kb": 256,  # 256KB
        },
    }

    # Convert to bytes
    env_config = recommendations.get(environment, recommendations["production"])
    return {k: v * 1024 for k, v in env_config.items()}


def validate_payload_runtime(
    payload: Any,
    expected_schema: dict[str, Any] | None = None,
    strict_types: bool = True,
    max_depth: int = 10,
    allow_extra_fields: bool = False,
) -> tuple[bool, list[str]]:
    """
    Comprehensive runtime payload validation with schema checking.

    Addresses PR feedback requirement for enhanced runtime validation beyond
    just size limits. Validates structure, types, depth, and schema compliance.

    Args:
        payload: The payload to validate
        expected_schema: Optional schema dictionary for structure validation
        strict_types: Whether to enforce strict type checking
        max_depth: Maximum allowed nesting depth
        allow_extra_fields: Whether to allow fields not in schema

    Returns:
        tuple: (is_valid, list_of_errors)

    Example:
        schema = {
            "event_type": str,
            "data": {
                "user_id": int,
                "action": str,
                "metadata": dict  # Allow any dict
            }
        }

        is_valid, errors = validate_payload_runtime(payload, schema)
        if not is_valid:
            raise OnexError(f"Payload validation failed: {errors}")
    """
    errors = []

    try:
        # Basic type validation
        if payload is None:
            errors.append("Payload cannot be None")
            return False, errors

        # Check depth to prevent stack overflow attacks
        depth = _calculate_payload_depth(payload)
        if depth > max_depth:
            errors.append(
                f"Payload depth {depth} exceeds maximum allowed depth {max_depth}"
            )

        # If no schema provided, just do basic checks
        if expected_schema is None:
            # Basic checks - ensure payload is serializable
            try:
                json.dumps(payload)
            except (TypeError, ValueError) as e:
                errors.append(f"Payload is not JSON serializable: {e}")
        else:
            # Schema validation
            schema_errors = _validate_against_schema(
                payload, expected_schema, strict_types, allow_extra_fields, ""
            )
            errors.extend(schema_errors)

        # Security checks
        security_errors = _validate_payload_security(payload)
        errors.extend(security_errors)

        return len(errors) == 0, errors

    except Exception as e:
        errors.append(f"Runtime validation error: {e}")
        return False, errors


def _calculate_payload_depth(payload: Any, current_depth: int = 0) -> int:
    """Calculate the nesting depth of a payload to prevent DoS attacks."""
    if current_depth > 50:  # Safety limit to prevent infinite recursion
        return current_depth

    if isinstance(payload, dict):
        if not payload:
            return current_depth
        max_child_depth = 0
        for value in payload.values():
            child_depth = _calculate_payload_depth(value, current_depth + 1)
            max_child_depth = max(max_child_depth, child_depth)
        return max_child_depth
    elif isinstance(payload, (list, tuple)):
        if not payload:
            return current_depth
        max_child_depth = 0
        for item in payload:
            child_depth = _calculate_payload_depth(item, current_depth + 1)
            max_child_depth = max(max_child_depth, child_depth)
        return max_child_depth
    else:
        return current_depth


def _validate_against_schema(
    payload: Any,
    schema: dict[str, Any],
    strict_types: bool,
    allow_extra_fields: bool,
    path: str,
) -> list[str]:
    """Validate payload against schema definition."""
    errors = []

    if not isinstance(payload, dict):
        errors.append(
            f"Expected dict at {path or 'root'}, got {type(payload).__name__}"
        )
        return errors

    # Check required fields
    for field_name, field_type in schema.items():
        field_path = f"{path}.{field_name}" if path else field_name

        if field_name not in payload:
            errors.append(f"Missing required field: {field_path}")
            continue

        field_value = payload[field_name]

        # Type checking
        if isinstance(field_type, dict):
            # Nested schema
            nested_errors = _validate_against_schema(
                field_value, field_type, strict_types, allow_extra_fields, field_path
            )
            errors.extend(nested_errors)
        elif isinstance(field_type, type):
            # Simple type check
            if strict_types and not isinstance(field_value, field_type):
                errors.append(
                    f"Type mismatch at {field_path}: expected {field_type.__name__}, "
                    f"got {type(field_value).__name__}"
                )
        # Handle Union types, Optional, etc. could be added here

    # Check for extra fields if not allowed
    if not allow_extra_fields:
        extra_fields = set(payload.keys()) - set(schema.keys())
        if extra_fields:
            for extra_field in extra_fields:
                field_path = f"{path}.{extra_field}" if path else extra_field
                errors.append(f"Unexpected field: {field_path}")

    return errors


def _validate_payload_security(payload: Any) -> list[str]:
    """Security validation for payloads to prevent common attacks."""
    errors = []

    try:
        # Check for extremely large string values that could cause memory issues
        if isinstance(payload, str) and len(payload) > 1_000_000:  # 1MB string limit
            errors.append(f"String value too large: {len(payload)} characters")
        elif isinstance(payload, dict):
            for key, value in payload.items():
                # Prevent key-based attacks
                if len(str(key)) > 1000:
                    errors.append(
                        f"Dictionary key too long: {len(str(key))} characters"
                    )

                # Recursive check
                if isinstance(value, (dict, list, str)):
                    sub_errors = _validate_payload_security(value)
                    errors.extend(sub_errors)
        elif isinstance(payload, list):
            # Check for excessively large lists
            if len(payload) > 10_000:  # 10k item limit
                errors.append(f"List too large: {len(payload)} items")

            for item in payload:
                if isinstance(item, (dict, list, str)):
                    sub_errors = _validate_payload_security(item)
                    errors.extend(sub_errors)

    except Exception as e:
        errors.append(f"Security validation error: {e}")

    return errors


def decompress_payload(payload: dict[str, Any] | str) -> Any:
    """
    Decompress a compressed payload.

    Args:
        payload: Compressed payload

    Returns:
        Decompressed payload

    Raises:
        OnexError: If decompression fails
    """
    import gzip
    import zlib

    try:
        if isinstance(payload, dict) and payload.get("__compressed__"):
            # Compressed dict format
            method = payload["__compression_method__"]
            compressed_data = bytes.fromhex(payload["__compressed_data__"])
            original_size = payload["__original_size__"]

            if method == "gzip":
                decompressed_bytes = gzip.decompress(compressed_data)
            elif method == "zlib":
                decompressed_bytes = zlib.decompress(compressed_data)
            else:
                msg = f"Unknown compression method: {method}"
                raise OnexError(
                    msg,
                    error_code=CoreErrorCode.VALIDATION_ERROR,
                )

            # Verify size matches
            if len(decompressed_bytes) != original_size:
                msg = f"Decompressed size mismatch: expected {original_size}, got {len(decompressed_bytes)}"
                raise OnexError(
                    msg,
                    error_code=CoreErrorCode.VALIDATION_ERROR,
                )

            # Try to deserialize as JSON
            try:
                return json.loads(decompressed_bytes.decode("utf-8"))
            except json.JSONDecodeError:
                return decompressed_bytes.decode("utf-8")

        elif isinstance(payload, str) and payload.startswith("__COMPRESSED__"):
            # Compressed string format
            parts = payload.split("__", 4)
            if len(parts) != 5 or parts[0] != "" or parts[1] != "COMPRESSED":
                msg = "Invalid compressed string format"
                raise OnexError(
                    msg,
                    error_code=CoreErrorCode.VALIDATION_ERROR,
                )

            method = parts[2]
            compressed_data = bytes.fromhex(parts[3])

            if method == "gzip":
                decompressed_bytes = gzip.decompress(compressed_data)
            elif method == "zlib":
                decompressed_bytes = zlib.decompress(compressed_data)
            else:
                msg = f"Unknown compression method: {method}"
                raise OnexError(
                    msg,
                    error_code=CoreErrorCode.VALIDATION_ERROR,
                )

            return decompressed_bytes.decode("utf-8")

        else:
            # Not compressed
            return payload

    except Exception as e:
        msg = f"Failed to decompress payload: {e}"
        raise OnexError(
            msg,
            error_code=CoreErrorCode.VALIDATION_ERROR,
        ) from e


def is_compressed_payload(payload: dict[str, Any] | str) -> bool:
    """
    Check if a payload is compressed.

    Args:
        payload: Payload to check

    Returns:
        True if payload is compressed, False otherwise
    """
    if isinstance(payload, dict):
        return payload.get("__compressed__", False)
    if isinstance(payload, str):
        return payload.startswith("__COMPRESSED__")
    return False


def get_system_memory_info() -> dict[str, int]:
    """
    Get system memory information for capacity planning.

    Returns:
        Dictionary with memory information in bytes
    """
    try:
        import psutil

        memory = psutil.virtual_memory()
        return {
            "total_bytes": memory.total,
            "available_bytes": memory.available,
            "used_bytes": memory.used,
            "free_bytes": memory.free,
            "percent_used": memory.percent,
        }
    except ImportError:
        # Fallback for systems without psutil
        logger.warning("psutil not available, using system memory info fallback")
        try:
            with open("/proc/meminfo") as f:
                meminfo = {}
                for line in f:
                    key, value = line.strip().split(":", 1)
                    meminfo[key] = int(value.split()[0]) * 1024  # Convert KB to bytes

                return {
                    "total_bytes": meminfo.get("MemTotal", 0),
                    "available_bytes": meminfo.get(
                        "MemAvailable",
                        meminfo.get("MemFree", 0),
                    ),
                    "used_bytes": meminfo.get("MemTotal", 0)
                    - meminfo.get("MemFree", 0),
                    "free_bytes": meminfo.get("MemFree", 0),
                    "percent_used": 0,  # Calculate if needed
                }
        except (FileNotFoundError, ValueError, KeyError):
            logger.warning("Cannot read system memory info")
            return {
                "total_bytes": 0,
                "available_bytes": 0,
                "used_bytes": 0,
                "free_bytes": 0,
                "percent_used": 0,
            }
