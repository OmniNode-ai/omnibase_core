from typing import Optional, Protocol, Tuple

from omnibase_core.model.core.model_semver import ModelSemVer
from omnibase_core.nodes.node_kafka_event_bus.v1_0_0.models.state import (
    KafkaEventBusInputState, KafkaEventBusOutputState)

# If needed, import from .models.state instead


class ProtocolInputValidationTool(Protocol):
    def validate_input_state(
        self, input_state: dict, semver: ModelSemVer, event_bus
    ) -> Tuple[Optional[KafkaEventBusInputState], Optional[KafkaEventBusOutputState]]:
        """
        Validates the input_state dict against ModelEventBusInputState.
        Returns (state, None) if valid, or (None, error_output) if invalid.
        """
        ...
