"""
Manifest Runner Protocol.

Protocol definition for manifest-based service runners.
"""

from typing import Any, Protocol

from omnibase_core.core.model_onex_container import ModelOnexContainer


class ProtocolManifestRunner(Protocol):
    """Protocol for manifest-based service runners."""

    def __init__(self, container: ModelOnexContainer) -> None:
        """Initialize the manifest runner with container."""
        ...

    async def run_from_manifest(self, manifest_path: str) -> Any:
        """Run services from a manifest file."""
        ...

    async def validate_manifest(self, manifest_path: str) -> bool:
        """Validate a manifest file."""
        ...

    async def load_manifest(self, manifest_path: str) -> dict[str, Any]:
        """Load and parse a manifest file."""
        ...

    async def execute_services(self, manifest_data: dict[str, Any]) -> Any:
        """Execute services defined in manifest data."""
        ...

    async def shutdown(self) -> None:
        """Shutdown the manifest runner and cleanup resources."""
        ...