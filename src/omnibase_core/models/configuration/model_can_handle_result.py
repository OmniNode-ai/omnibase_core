"""
CanHandleResult model.
"""

from pydantic import BaseModel, Field


class ModelCanHandleResult(BaseModel):
    """Result model for can_handle protocol method.

    Warning:
        This model overrides ``__bool__`` to return the value of ``can_handle``.
        Unlike standard Pydantic models, ``bool(instance)`` may return ``False``
        even when the instance exists.
    """

    can_handle: bool = Field(
        default=...,
        description="Whether the handler can process the file/content.",
    )

    def __bool__(self) -> bool:
        """Return True if handler can process the content.

        Warning:
            This differs from standard Pydantic behavior where ``bool(model)``
            always returns ``True``. Here, ``bool(result)`` returns the value
            of ``can_handle``, enabling idiomatic conditional checks.

        Returns:
            bool: The value of the ``can_handle`` field.

        Example:
            >>> result = ModelCanHandleResult(can_handle=True)
            >>> if result:
            ...     print("Handler can process this content")
            Handler can process this content
        """
        return self.can_handle
