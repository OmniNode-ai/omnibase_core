"""Configuration for custom callable invariant.

Allows user-defined validation logic via a Python callable.

Thread Safety:
    ModelCustomInvariantConfig is immutable (frozen=True) after creation,
    making it thread-safe for concurrent read access.
"""

import re
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

# Pattern for valid Python identifiers (simplified)
# Each segment must be a valid Python identifier: starts with letter or underscore,
# followed by letters, digits, or underscores
_PYTHON_IDENTIFIER_PATTERN = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


class ModelCustomInvariantConfig(BaseModel):
    """Configuration for custom callable invariant.

    Allows user-defined validation logic via a Python callable. The callable
    should accept the value to validate and return a boolean indicating
    validity.

    Attributes:
        callable_path: Fully qualified Python path to the validation callable
            (e.g., 'mymodule.validators.check_output'). The callable will be
            imported and invoked at validation time. Must be in dotted notation
            with at least a module and function name (e.g., 'module.function').
        kwargs: Additional keyword arguments to pass to the callable. Values
            must be JSON-serializable primitive types (str, int, float, bool,
            or None).

    Raises:
        ValueError: If callable_path is not a valid Python import path.

    Thread Safety:
        This model is immutable (frozen=True) after creation, making it
        thread-safe for concurrent read access. No synchronization is needed
        when sharing instances across threads.
    """

    model_config = ConfigDict(frozen=True, extra="ignore", from_attributes=True)

    callable_path: str = Field(
        ...,
        description="Python callable path (e.g., 'mymodule.validators.check_output')",
        min_length=1,
    )
    kwargs: dict[str, str | int | float | bool | None] = Field(
        default_factory=dict,
        description="Additional keyword arguments to pass to the callable",
    )

    @model_validator(mode="after")
    def validate_callable_path_format(self) -> Self:
        """Validate that callable_path is a valid Python import path.

        A valid callable path must:
        - Contain at least one dot (module.function format)
        - Not start or end with a dot
        - Not contain consecutive dots
        - Have valid Python identifiers for each segment

        Returns:
            Self if validation passes.

        Raises:
            ValueError: If callable_path format is invalid.
        """
        path = self.callable_path

        # Check for required dot (module.function format)
        if "." not in path:
            # error-ok: Pydantic model_validator requires ValueError
            raise ValueError(
                f"callable_path '{path}' must be a fully qualified Python path "
                "in dotted notation (e.g., 'mymodule.validators.check_output'). "
                "A valid path requires at least a module and function name."
            )

        # Check for leading/trailing dots
        if path.startswith(".") or path.endswith("."):
            # error-ok: Pydantic model_validator requires ValueError
            raise ValueError(
                f"callable_path '{path}' cannot start or end with a dot. "
                "Provide a complete path like 'mymodule.function'."
            )

        # Check for consecutive dots
        if ".." in path:
            # error-ok: Pydantic model_validator requires ValueError
            raise ValueError(
                f"callable_path '{path}' contains consecutive dots. "
                "Each segment must be a valid Python identifier."
            )

        # Validate each segment is a valid Python identifier
        segments = path.split(".")
        invalid_segments = [
            seg for seg in segments if not _PYTHON_IDENTIFIER_PATTERN.match(seg)
        ]
        if invalid_segments:
            # error-ok: Pydantic model_validator requires ValueError
            raise ValueError(
                f"callable_path '{path}' contains invalid Python identifiers: "
                f"{invalid_segments}. Each segment must be a valid Python "
                "identifier (letters, digits, underscores; cannot start with digit)."
            )

        return self


__all__ = ["ModelCustomInvariantConfig"]
