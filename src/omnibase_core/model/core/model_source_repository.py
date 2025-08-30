"""
Source repository model.
"""

from typing import Annotated, Any, Callable, Iterator, Optional

from pydantic import BaseModel, StringConstraints


class ModelSourceRepository(BaseModel):
    """Source repository information."""

    url: Optional[str] = None
    commit_hash: Optional[
        Annotated[str, StringConstraints(pattern=r"^[a-fA-F0-9]{40}$")]
    ] = None
    path: Optional[str] = None

    @classmethod
    def __get_validators__(cls) -> Iterator[Callable[[Any], Any]]:
        yield cls._debug_commit_hash

    @staticmethod
    def _debug_commit_hash(value: Any) -> Any:
        if value is not None:
            value = value.strip() if isinstance(value, str) else value
        return value
