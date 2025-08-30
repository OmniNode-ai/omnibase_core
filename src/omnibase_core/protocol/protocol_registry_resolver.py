from typing import Optional, Protocol

from omnibase_core.protocol.protocol_registry import ProtocolRegistry


class ProtocolRegistryResolver(Protocol):
    def resolve_registry(
        self,
        registry_class: type,
        scenario_path: Optional[str] = None,
        logger: Optional[object] = None,
        fallback_tools: Optional[dict] = None,
    ) -> ProtocolRegistry:
        """
        Canonical protocol for registry resolution.
        If scenario_path is provided and valid, loads scenario YAML, extracts registry_tools or registry_configs from the config block, and returns a constructed registry instance.
        If not, constructs the registry and registers fallback_tools (if provided).
        Returns the constructed registry. All standards-compliant logic is centralized here.
        """
        ...
