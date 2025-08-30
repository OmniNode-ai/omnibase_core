from typing import Protocol

from omnibase_core.enums.enum_metadata import ToolRegistryModeEnum
from omnibase_core.protocol.protocol_logger import ProtocolLogger
from omnibase_core.protocol.protocol_tool import ProtocolTool


class ProtocolNodeRegistry(Protocol):
    """
    Protocol for node-local tool registries in ONEX nodes.
    Supports registering, looking up, and listing pluggable tools (formatters, backends, handlers, etc.).
    Now supports real/mock mode and optional trace logging.
    Extend this protocol in your node if you need to support additional tool types or metadata.
    """

    mode: ToolRegistryModeEnum
    logger: ProtocolLogger | None

    def set_mode(self, mode: ToolRegistryModeEnum) -> None: ...

    def set_logger(self, logger: ProtocolLogger | None) -> None: ...

    def register_tool(self, name: str, tool_cls: type[ProtocolTool]) -> None: ...

    def get_tool(self, name: str) -> type[ProtocolTool] | None: ...

    def list_tools(self) -> dict[str, type[ProtocolTool]]: ...
