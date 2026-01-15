"""
Extension intent payloads for plugins and experimental features.

This module provides typed payloads for extension-related intents:
- ModelPayloadExtension: Generic extension payload for plugins and webhooks

Design Pattern:
    Extension payloads provide a flexible escape hatch for plugin and
    experimental intent types that don't fit the core typed payload system.
    They maintain type safety while allowing arbitrary extension data.

    Unlike core payloads with fixed schemas, ModelPayloadExtension uses an
    `extension_type` field to classify the extension category while
    storing arbitrary data in the `data` field.

Extension Integration:
    - Supports plugin.* namespaced intents
    - Supports webhook.* namespaced intents
    - Supports experimental.* namespaced intents
    - Supports custom.* user-defined intents

Thread Safety:
    All payloads are immutable (frozen=True) after creation, making them
    thread-safe for concurrent read access.

JSON Serialization:
    The `data` field enforces strict JSON serializability at runtime.
    Only primitive JSON types are allowed:
    - str, int, float, bool, None (scalars)
    - list (arrays of JSON values)
    - dict with str keys (objects)

    Non-JSON types are REJECTED with actionable error messages:
    - datetime: Use `.isoformat()` before assignment
    - UUID: Use `str(uuid)` before assignment
    - Path: Use `str(path)` before assignment
    - Custom objects: Use `.model_dump()` or manual serialization

Example:
    >>> from omnibase_core.models.reducer.payloads import ModelPayloadExtension
    >>>
    >>> # Plugin execution payload
    >>> plugin_payload = ModelPayloadExtension(
    ...     extension_type="plugin.transform",
    ...     plugin_name="data-enricher",
    ...     data={"source": "user_db", "transform": "enrich_profile"},
    ... )
    >>>
    >>> # Webhook payload
    >>> webhook_payload = ModelPayloadExtension(
    ...     extension_type="webhook.outbound",
    ...     plugin_name="slack-notifier",
    ...     data={"url": "https://hooks.slack.com/...", "message": "Alert!"},
    ... )

See Also:
    omnibase_core.models.reducer.payloads.ModelIntentPayloadBase: Base class
    omnibase_core.models.reducer.payloads.model_protocol_intent_payload: Protocol for intent payloads
    omnibase_core.models.reducer.model_intent: Extension intent model
"""

import math
from typing import Any, Literal

from pydantic import Field, field_validator

from omnibase_core.models.reducer.payloads.model_intent_payload_base import (
    ModelIntentPayloadBase,
)
from omnibase_core.types import StrictJsonType

# Public API - listed immediately after imports per Python convention
__all__ = ["ModelPayloadExtension"]


# ==============================================================================
# Strict JSON Validation Helpers
# ==============================================================================

# Types that are commonly mistaken for JSON-serializable but are NOT.
# These require explicit conversion before assignment to `data`.
_NON_JSON_TYPE_HINTS: dict[str, str] = {
    "datetime": "Use .isoformat() to convert to ISO-8601 string",
    "date": "Use .isoformat() to convert to ISO-8601 string",
    "time": "Use .isoformat() to convert to ISO-8601 string",
    "timedelta": "Use .total_seconds() or str() to convert",
    "UUID": "Use str(uuid) to convert to string",
    "Path": "Use str(path) to convert to string",
    "PosixPath": "Use str(path) to convert to string",
    "WindowsPath": "Use str(path) to convert to string",
    "PurePath": "Use str(path) to convert to string",
    "Decimal": "Use float(decimal) or str(decimal) to convert",
    "bytes": "Use .decode('utf-8') or base64.b64encode().decode() to convert",
    "bytearray": "Use bytes(ba).decode('utf-8') or base64 encoding to convert",
    "set": "Use list(set_value) to convert to list",
    "frozenset": "Use list(frozenset_value) to convert to list",
    "tuple": "Use list(tuple_value) to convert to list",
}


def _find_non_json_serializable_path(
    value: Any, path: str = ""
) -> tuple[str, str, str] | None:
    """Find the first non-JSON-serializable value in a nested structure.

    This function enforces STRICT JSON serializability - only the primitive
    JSON types are allowed. Non-JSON types like datetime, UUID, Path, etc.
    are rejected with actionable hints for common conversions.

    Returns a tuple of (path, type_name, hint) if found, None if all values valid.
    Uses recursive traversal to provide accurate key-paths for error messages.

    Args:
        value: The value to check for JSON serializability.
        path: The current key-path (for nested structures).

    Returns:
        Tuple of (path, type_name, hint) if non-serializable value found,
        None otherwise. The hint provides actionable conversion advice.
    """
    # NOTE: This validates STRICT JSON serializability (RFC 8259).
    # Unlike JsonPrimitive (which includes UUID/datetime for Pydantic compatibility),
    # this validator only accepts: str, int, float, bool, None, list, dict.
    if value is None or isinstance(value, (str, int, bool)):
        return None

    # Check floats separately to reject non-finite values (inf, -inf, nan)
    # RFC 8259 JSON does not support Infinity or NaN - these must be converted
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return (
                path or "root",
                "non-finite float",
                "Use a finite number or None for undefined values",
            )
        return None

    # Check dict recursively (JSON objects must have string keys)
    if isinstance(value, dict):
        for key, val in value.items():
            if not isinstance(key, str):
                # Format non-string keys with brackets to distinguish from string keys
                key_repr = f"[{key!r}]"
                key_path = f"{path}{key_repr}" if path else key_repr
                return (
                    key_path,
                    f"non-string key ({type(key).__name__})",
                    "JSON object keys must be strings",
                )
            key_path = f"{path}.{key}" if path else key
            result = _find_non_json_serializable_path(val, key_path)
            if result is not None:
                return result
        return None

    # Check list recursively (JSON arrays)
    if isinstance(value, list):
        for idx, item in enumerate(value):
            item_path = f"{path}[{idx}]" if path else f"[{idx}]"
            result = _find_non_json_serializable_path(item, item_path)
            if result is not None:
                return result
        return None

    # Non-serializable type found - get hint for common types
    type_name = type(value).__name__
    hint = _NON_JSON_TYPE_HINTS.get(type_name, "Convert to JSON-compatible type")
    return (path or "root", type_name, hint)


class ModelPayloadExtension(ModelIntentPayloadBase):
    """Payload for extension/plugin intents.

    Provides a flexible payload structure for plugin, webhook, and experimental
    intent types. Uses `extension_type` for classification and `data` for
    arbitrary extension-specific content.

    This is the "escape hatch" for intent types not covered by core payloads.
    Effects should dispatch on `extension_type` or `plugin_name` for routing.

    Extension Type Conventions:
        - plugin.*: Plugin execution intents (plugin.transform, plugin.validate)
        - webhook.*: Webhook delivery intents (webhook.send, webhook.inbound)
        - experimental.*: Experimental feature intents
        - custom.*: User-defined custom intents

    Attributes:
        intent_type: Discriminator literal for intent routing. Always "extension".
            Placed first for optimal union type resolution performance.
        extension_type: Extension category following namespace conventions.
            Used for routing to the appropriate extension handler.
        plugin_name: Name of the plugin or extension handling this intent.
        version: Optional version of the plugin or extension.
        data: Arbitrary extension-specific data. Schema is defined by the extension.
        config: Optional configuration overrides for this execution.
        timeout_seconds: Optional timeout for extension execution.

    Example:
        >>> payload = ModelPayloadExtension(
        ...     extension_type="plugin.ml_inference",
        ...     plugin_name="sentiment-analyzer",
        ...     version="2.1.0",
        ...     data={"text": "This product is amazing!", "model": "bert-base"},
        ...     config={"threshold": 0.8},
        ...     timeout_seconds=30,
        ... )
    """

    # NOTE: Discriminator field is placed FIRST for optimal union type resolution.
    intent_type: Literal["extension"] = Field(
        default="extension",
        description=(
            "Discriminator literal for intent routing. Used by Pydantic's "
            "discriminated union to dispatch to the correct Effect handler."
        ),
    )

    extension_type: str = Field(
        ...,
        description=(
            "Extension category following namespace conventions. Examples: "
            "'plugin.transform', 'webhook.send', 'experimental.feature'."
        ),
        min_length=1,
        max_length=128,
        pattern=r"^[a-zA-Z][a-zA-Z0-9_]*\.[a-zA-Z][a-zA-Z0-9_]*$",
    )

    plugin_name: str = Field(
        ...,
        description=(
            "Name of the plugin or extension handling this intent. Used for "
            "routing to the appropriate handler."
        ),
        min_length=1,
        max_length=128,
    )

    version: str | None = Field(
        default=None,
        description=(
            "Optional version of the plugin or extension. Allows version-specific "
            "routing or compatibility checks."
        ),
        max_length=32,
    )

    # NOTE(OMN-1266): StrictJsonType is used instead of JsonType because runtime
    # validation rejects UUID/datetime - this ensures static type matches runtime behavior.
    # JsonType includes UUID/datetime for Pydantic model_dump() compatibility, but this
    # field requires strict RFC 8259 JSON compliance for cross-service serialization.
    data: dict[str, StrictJsonType] = Field(
        default_factory=dict,
        description=(
            "Arbitrary extension-specific data. Schema is defined by the extension. "
            "Must be JSON-serializable (str, int, float, bool, None, list, dict only). "
            "Non-JSON types like datetime, UUID, Path are rejected with actionable hints."
        ),
    )

    # NOTE(OMN-1266): StrictJsonType is used instead of object because runtime
    # validation rejects non-JSON types - this ensures static type matches runtime behavior.
    # The config field has identical JSON validation to the data field.
    config: dict[str, StrictJsonType] = Field(
        default_factory=dict,
        description=(
            "Optional configuration overrides for this execution. Allows per-call "
            "customization of extension behavior. Must be JSON-serializable "
            "(str, int, float, bool, None, list, dict only)."
        ),
    )

    timeout_seconds: int | None = Field(
        default=None,
        description=(
            "Optional timeout for extension execution in seconds. If not provided, "
            "the extension's default timeout is used."
        ),
        ge=1,
        le=3600,
    )

    @field_validator("data", mode="before")
    @classmethod
    def validate_data_json_serializable(cls, v: object) -> dict[str, StrictJsonType]:
        """Validate that data values are strictly JSON-serializable.

        Enforces strict JSON serializability - only primitive JSON types are allowed:
        str, int, float (finite only), bool, None, list (of JSON values), dict (with str keys).

        Non-JSON types like datetime, UUID, Path, or custom objects are REJECTED
        with actionable error messages that include the key-path and conversion hints.
        Non-finite floats (inf, -inf, nan) are also rejected per RFC 8259.

        No auto-coercion is performed - callers must explicitly convert types.

        Args:
            v: The dict to validate.

        Returns:
            The validated dict (unchanged if valid), typed as dict[str, StrictJsonType].

        Raises:
            ValueError: If any value is not JSON-serializable, with key-path and hint.
        """
        if not isinstance(v, dict):
            raise ValueError(f"data must be a dict, got {type(v).__name__}")

        result = _find_non_json_serializable_path(v)
        if result is not None:
            path, type_name, hint = result
            raise ValueError(
                f"Non-JSON-serializable value at 'data.{path}': {type_name}. {hint}."
            )
        # NOTE(OMN-1266): Type narrowing - validator confirms all values are StrictJsonType
        # primitives. Mypy accepts this return because the isinstance(v, dict) check above
        # narrows the type sufficiently for the dict[str, JsonType] return annotation.
        return v

    @field_validator("config", mode="before")
    @classmethod
    def validate_config_json_serializable(cls, v: object) -> dict[str, StrictJsonType]:
        """Validate that config values are strictly JSON-serializable.

        Applies the same JSON-serializability rules as the data field.

        Args:
            v: The dict to validate.

        Returns:
            The validated dict (unchanged if valid), typed as dict[str, StrictJsonType].

        Raises:
            ValueError: If any value is not JSON-serializable, with key-path and hint.
        """
        if not isinstance(v, dict):
            raise ValueError(f"config must be a dict, got {type(v).__name__}")

        result = _find_non_json_serializable_path(v)
        if result is not None:
            path, type_name, hint = result
            raise ValueError(
                f"Non-JSON-serializable value at 'config.{path}': {type_name}. {hint}."
            )
        # NOTE(OMN-1266): Type narrowing - validator confirms all values are StrictJsonType
        # primitives. The isinstance(v, dict) check above narrows the type sufficiently.
        return v
