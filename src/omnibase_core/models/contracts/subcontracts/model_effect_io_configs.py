"""
Effect IO Configuration Models.

This module re-exports the IO configuration models from their individual files
and defines the EffectIOConfig discriminated union type.

Each model provides configuration for a specific type of external I/O operation:
- HTTP: REST API calls with URL templates and request configuration
- DB: Database operations with SQL templates and connection management
- Kafka: Message production with topic, payload, and delivery settings
- Filesystem: File operations with path templates and atomicity controls

DISCRIMINATED UNION:
The EffectIOConfig union type uses handler_type as the discriminator field,
enabling Pydantic to automatically select the correct model during validation.

Thread Safety:
    All IO configuration models are immutable (frozen=True) after creation,
    making them thread-safe for concurrent read access.

See Also:
    - :class:`ModelEffectSubcontract`: Parent contract using these IO configs
    - :mod:`omnibase_core.models.contracts.subcontracts.model_effect_resolved_context`:
        Resolved context models after template substitution
    - :class:`NodeEffect`: The primary node using these configurations
    - docs/architecture/CONTRACT_DRIVEN_NODEEFFECT_V1_0.md: Full specification
    - examples/contracts/effect/: Example YAML contracts

Author: ONEX Framework Team
"""

from typing import Annotated

from pydantic import Discriminator

from omnibase_core.models.contracts.subcontracts.model_db_io_config import (
    ModelDbIOConfig,
)
from omnibase_core.models.contracts.subcontracts.model_filesystem_io_config import (
    ModelFilesystemIOConfig,
)
from omnibase_core.models.contracts.subcontracts.model_http_io_config import (
    ModelHttpIOConfig,
)
from omnibase_core.models.contracts.subcontracts.model_kafka_io_config import (
    ModelKafkaIOConfig,
)

__all__ = [
    "ModelHttpIOConfig",
    "ModelDbIOConfig",
    "ModelKafkaIOConfig",
    "ModelFilesystemIOConfig",
    "EffectIOConfig",
]


# Discriminated union type for all IO configurations
# Pydantic uses handler_type as the discriminator to select the correct model
EffectIOConfig = Annotated[
    ModelHttpIOConfig | ModelDbIOConfig | ModelKafkaIOConfig | ModelFilesystemIOConfig,
    Discriminator("handler_type"),
]
