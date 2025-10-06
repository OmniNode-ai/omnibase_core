from typing import Any, Protocol


class HasModelDump(Protocol):
    def model_dump(self, mode: str = "json") -> dict[str, Any]: ...
