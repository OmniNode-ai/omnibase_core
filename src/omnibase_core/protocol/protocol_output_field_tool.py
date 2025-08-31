from typing import Protocol

from omnibase_core.model.core.model_output_field import ModelOnexField


class OutputFieldTool(Protocol):
    def __call__(self, state, input_state_dict) -> ModelOnexField: ...
