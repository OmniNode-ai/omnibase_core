"""Registry Error Code Enumeration.

Canonical error codes for ONEX tool/handler registries.
"""

import re
from enum import unique

from omnibase_core.enums.enum_cli_exit_code import EnumCLIExitCode
from omnibase_core.enums.enum_onex_error_code import EnumOnexErrorCode


@unique
class EnumRegistryErrorCode(EnumOnexErrorCode):
    """
    Canonical error codes for ONEX tool/handler registries.
    Use these for all registry-driven error handling (tool not found, duplicate, etc.).
    """

    TOOL_NOT_FOUND = "ONEX_REGISTRY_001_TOOL_NOT_FOUND"
    DUPLICATE_TOOL = "ONEX_REGISTRY_002_DUPLICATE_TOOL"
    INVALID_MODE = "ONEX_REGISTRY_003_INVALID_MODE"
    REGISTRY_UNAVAILABLE = "ONEX_REGISTRY_004_REGISTRY_UNAVAILABLE"

    def get_component(self) -> str:
        return "REGISTRY"

    def get_number(self) -> int:
        match = re.search(r"ONEX_REGISTRY_(\d+)_", self.value)
        return int(match.group(1)) if match else 0

    def get_description(self) -> str:
        descriptions = {
            self.TOOL_NOT_FOUND: "Requested tool is not registered in the registry.",
            self.DUPLICATE_TOOL: "A tool with this name is already registered.",
            self.INVALID_MODE: "The requested registry mode is invalid or unsupported.",
            self.REGISTRY_UNAVAILABLE: "The registry is unavailable or not initialized.",
        }
        return descriptions.get(self, "Unknown registry error.")

    def get_exit_code(self) -> int:
        return EnumCLIExitCode.ERROR.value


__all__ = ["EnumRegistryErrorCode", "EnumOnexErrorCode"]
