"""
Source repository model.
"""

from collections.abc import Callable, Iterator
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints


class ModelSourceRepository(BaseModel):
    """Immutable source repository information.

    This model is frozen and hashable, suitable for use as dict keys or in sets.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    url: str | None = None
    commit_hash: (
        Annotated[str, StringConstraints(pattern=r"^[a-fA-F0-9]{40}$")] | None
    ) = None
    path: str | None = None

    @classmethod
    def __get_validators__(cls) -> Iterator[Callable[[object], object]]:
        yield cls._debug_commit_hash

    @staticmethod
    def _debug_commit_hash(value: object) -> object:
        if value is not None:
            value = value.strip() if isinstance(value, str) else value
        return value
