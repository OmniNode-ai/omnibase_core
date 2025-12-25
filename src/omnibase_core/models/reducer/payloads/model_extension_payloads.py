"""
Extension intent payloads for plugins and experimental features.

This module provides typed payloads for extension-related intents:
- PayloadExtension: Generic extension payload for plugins and webhooks

Design Pattern:
    Extension payloads provide a flexible escape hatch for plugin and
    experimental intent types that don't fit the core typed payload system.
    They maintain type safety while allowing arbitrary extension data.

    Unlike core payloads with fixed schemas, PayloadExtension uses an
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

Example:
    >>> from omnibase_core.models.reducer.payloads import PayloadExtension
    >>>
    >>> # Plugin execution payload
    >>> plugin_payload = PayloadExtension(
    ...     extension_type="plugin.transform",
    ...     plugin_name="data-enricher",
    ...     data={"source": "user_db", "transform": "enrich_profile"},
    ... )
    >>>
    >>> # Webhook payload
    >>> webhook_payload = PayloadExtension(
    ...     extension_type="webhook.outbound",
    ...     plugin_name="slack-notifier",
    ...     data={"url": "https://hooks.slack.com/...", "message": "Alert!"},
    ... )

See Also:
    omnibase_core.models.reducer.payloads.ModelIntentPayloadBase: Base class
    omnibase_core.models.reducer.payloads.model_intent_payload_union: Union type
    omnibase_core.models.reducer.model_intent: Extension intent model
"""

from typing import Literal

from pydantic import Field

from omnibase_core.models.reducer.payloads.model_intent_payload_base import (
    ModelIntentPayloadBase,
)


class PayloadExtension(ModelIntentPayloadBase):
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
        >>> payload = PayloadExtension(
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

    data: dict[str, object] = Field(
        default_factory=dict,
        description=(
            "Arbitrary extension-specific data. Schema is defined by the extension. "
            "Must be JSON-serializable."
        ),
    )

    config: dict[str, object] = Field(
        default_factory=dict,
        description=(
            "Optional configuration overrides for this execution. Allows per-call "
            "customization of extension behavior."
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


__all__ = [
    "PayloadExtension",
]
