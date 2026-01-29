"""Contract registration event model.

Published when a node registers its contract for dynamic discovery.
Carries the full contract YAML for replay capability (OMN-1651).
"""

from pydantic import ConfigDict, Field

from omnibase_core.models.events.model_runtime_event_base import ModelRuntimeEventBase
from omnibase_core.models.primitives.model_semver import ModelSemVer

__all__ = ["ModelContractRegisteredEvent", "CONTRACT_REGISTERED_EVENT"]

# Full topic name for Kafka/event bus publishing (onex.evt.<type>.v1 format).
# The short event type identifier ("contract-registered") is in constants_event_types.py.
CONTRACT_REGISTERED_EVENT = "onex.evt.contract-registered.v1"


class ModelContractRegisteredEvent(ModelRuntimeEventBase):
    """Contract registration event - carries full contract for replay.

    Published when a node registers its contract with the platform.
    The contract_yaml field contains the complete contract for replay
    capability, enabling late-joining consumers to reconstruct state.

    Inherits from ModelRuntimeEventBase:
        event_id, correlation_id, timestamp, source_node_id
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        from_attributes=True,
    )

    event_type: str = Field(
        default=CONTRACT_REGISTERED_EVENT,
        description="Event type identifier",
    )
    node_name: str = Field(
        description="Name of the registering node",
    )
    node_version: ModelSemVer = Field(
        description="Semantic version of the registering node",
    )
    contract_hash: str = Field(
        min_length=1,
        description="Hash of the contract for deduplication/validation",
    )
    contract_yaml: str = Field(
        description="Full contract YAML content for replay capability",
    )
