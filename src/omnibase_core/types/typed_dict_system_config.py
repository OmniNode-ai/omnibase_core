"""TypedDict for system configuration in baseline health reports."""

from typing import TypedDict


class TypedDictSystemConfig(TypedDict, total=False):
    """System configuration for baseline health reporting.

    This TypedDict captures LLM and system configuration parameters
    used during the measurement period. All fields are optional to
    accommodate varying configuration schemas.

    Note:
        Uses ``total=False`` to make all fields optional. This is preferred
        over wrapping each field with ``NotRequired`` for cleaner syntax
        when all fields should be optional.

    Attributes:
        model: The model identifier (e.g., "gpt-4", "claude-3").
        temperature: Sampling temperature for the model.
        max_tokens: Maximum tokens for responses.
        top_p: Top-p sampling parameter.
        frequency_penalty: Frequency penalty for sampling.
        presence_penalty: Presence penalty for sampling.
        system_prompt: The system prompt used.
        tools_enabled: Whether tools/functions are enabled.
        streaming: Whether streaming responses are enabled.

    Example:
        >>> config: TypedDictSystemConfig = {
        ...     "model": "gpt-4",
        ...     "temperature": 0.7,
        ...     "max_tokens": 1000,
        ... }
    """

    model: str
    temperature: float
    max_tokens: int
    top_p: float
    frequency_penalty: float
    presence_penalty: float
    system_prompt: str
    tools_enabled: bool
    streaming: bool
