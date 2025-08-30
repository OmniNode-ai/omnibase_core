"""
Source repository model.
"""

from collections.abc import Callable, Iterator
from typing import Annotated, Any

from pydantic import BaseModel, StringConstraints


class ModelSourceRepository(BaseModel):
    """Source repository information."""

    url: str | None = None
    commit_hash: (
        Annotated[str, StringConstraints(pattern=r"^[a-fA-F0-9]{40}$")] | None
    ) = None
    path: str | None = None

    @classmethod
    def __get_validators__(cls) -> Iterator[Callable[[Any], Any]]:
        yield cls._debug_commit_hash

    @staticmethod
    def _debug_commit_hash(value: Any) -> Any:
        if value is not None:
            value = value.strip() if isinstance(value, str) else value
        return value
