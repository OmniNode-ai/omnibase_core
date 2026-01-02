"""Configuration for custom callable invariant.

Allows user-defined validation logic via a Python callable.
"""

from pydantic import BaseModel, Field


class ModelCustomInvariantConfig(BaseModel):
    """Configuration for custom callable invariant.

    Allows user-defined validation logic via a Python callable.
    The callable should accept the value to validate and return
    a boolean indicating validity.
    """

    callable_path: str = Field(
        ...,
        description="Python callable path (e.g., 'mymodule.validators.check_output')",
    )
    kwargs: dict[str, str | int | float | bool | None] = Field(
        default_factory=dict,
        description="Additional keyword arguments to pass to the callable",
    )


__all__ = ["ModelCustomInvariantConfig"]
