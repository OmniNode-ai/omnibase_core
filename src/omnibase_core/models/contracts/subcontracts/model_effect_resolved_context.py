"""
Resolved Context Models for NodeEffect Handler Contract.

This module re-exports resolved context models from their individual files
for convenience and unified imports.

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

from .model_resolved_db_context import ModelResolvedDbContext
from .model_resolved_filesystem_context import ModelResolvedFilesystemContext
from .model_resolved_http_context import ModelResolvedHttpContext
from .model_resolved_kafka_context import ModelResolvedKafkaContext

__all__ = [
    "ModelResolvedHttpContext",
    "ModelResolvedDbContext",
    "ModelResolvedKafkaContext",
    "ModelResolvedFilesystemContext",
    "ResolvedIOContext",
]


# Union type for handler signatures
ResolvedIOContext = (
    ModelResolvedHttpContext
    | ModelResolvedDbContext
    | ModelResolvedKafkaContext
    | ModelResolvedFilesystemContext
)
