"""Configuration for custom callable invariant.

Allows user-defined validation logic via a Python callable.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelCustomInvariantConfig(BaseModel):
    """Configuration for custom callable invariant.

    Allows user-defined validation logic via a Python callable. The callable
    should accept the value to validate and return a boolean indicating
    validity.

    Attributes:
        callable_path: Fully qualified Python path to the validation callable
            (e.g., 'mymodule.validators.check_output'). The callable will be
            imported and invoked at validation time.
        kwargs: Additional keyword arguments to pass to the callable. Values
            must be JSON-serializable primitive types (str, int, float, bool,
            or None).
    """

    model_config = ConfigDict(frozen=True, extra="ignore", from_attributes=True)

    callable_path: str = Field(
        ...,
        description="Python callable path (e.g., 'mymodule.validators.check_output')",
    )
    kwargs: dict[str, str | int | float | bool | None] = Field(
        default_factory=dict,
        description="Additional keyword arguments to pass to the callable",
    )


__all__ = ["ModelCustomInvariantConfig"]
