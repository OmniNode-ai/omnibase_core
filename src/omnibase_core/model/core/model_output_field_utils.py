from typing import Any, TypeVar

from pydantic import BaseModel

from omnibase_core.constants import (
    BACKEND_KEY,
    CUSTOM_KEY,
    DEFAULT_PROCESSED_VALUE,
    INTEGRATION_KEY,
    PROCESSED_KEY,
)
from omnibase_core.model.core.model_output_field import ModelOnexField

# Import the protocol from either node (assume canonical location for now)
try:
    from omnibase_core.protocol.protocol_output_field_tool import OutputFieldTool
except ImportError:
    from omnibase_core.protocol.protocol_output_field_tool import OutputFieldTool

T = TypeVar("T", bound=BaseModel)


def make_output_field(field_value: Any, output_field_model_cls: type[T]) -> T:
    """
    Converts/wraps any field_value (dict, Pydantic model, etc.) into the canonical output field model.
    Args:
        field_value: The value to wrap (dict, model, etc.)
        output_field_model_cls: The canonical output field model class for the node
    Returns:
        An instance of output_field_model_cls
    Raises:
        ValueError: If the value cannot be converted to the output field model
    """
    if isinstance(field_value, output_field_model_cls):
        return field_value
    if isinstance(field_value, BaseModel):
        # Try to convert via dict
        return output_field_model_cls(**field_value.model_dump())
    if isinstance(field_value, dict):
        return output_field_model_cls(**field_value)
    # Fallback: wrap in 'data' field if model supports it
    try:
        return output_field_model_cls(data=field_value)
    except Exception as e:
        msg = (
            f"Cannot convert {field_value!r} to {output_field_model_cls.__name__}: {e}"
        )
        raise ValueError(
            msg,
        )


def build_output_field_kwargs(input_state: dict, event_bus: any) -> dict:
    """
    Build canonical output_field kwargs for a node, handling backend, custom, integration, processed keys.
    Args:
        input_state: The input state dict
        event_bus: The event bus instance (for backend name)
    Returns:
        dict of kwargs for output field model
    """
    kwargs = {BACKEND_KEY: event_bus.__class__.__name__ if event_bus else "unknown"}
    if CUSTOM_KEY in input_state:
        return {BACKEND_KEY: kwargs[BACKEND_KEY], CUSTOM_KEY: input_state[CUSTOM_KEY]}
    if INTEGRATION_KEY in input_state:
        return {
            BACKEND_KEY: kwargs[BACKEND_KEY],
            INTEGRATION_KEY: input_state[INTEGRATION_KEY],
        }
    kwargs[PROCESSED_KEY] = DEFAULT_PROCESSED_VALUE
    return kwargs


class ModelComputeOutputFieldTool(OutputFieldTool):
    def __call__(self, state, input_state_dict: dict[str, Any]) -> ModelOnexField:
        # If 'output_field' is present in the input dict, always use it
        val = input_state_dict.get("output_field")
        if val is not None:
            if isinstance(val, ModelOnexField):
                return val
            if isinstance(val, dict):
                if "data" in val:
                    return ModelOnexField(**val)
                return ModelOnexField(data=val)
            return ModelOnexField(data=val)
        # If 'external_dependency' is present and True in either model or dict, return integration
        if (
            getattr(state, "external_dependency", None) is True
            or input_state_dict.get("external_dependency") is True
        ):
            return ModelOnexField(data={"integration": True})
        # Default: processed
        return ModelOnexField(data={"processed": getattr(state, "input_field", None)})


# Backward compatibility alias
ComputeOutputFieldTool = ModelComputeOutputFieldTool

compute_output_field = ModelComputeOutputFieldTool()
