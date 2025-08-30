# === OmniNode:Metadata ===
# author: OmniNode Team
# copyright: OmniNode.ai
# created_at: '2025-05-28T12:36:27.191573'
# description: Stamped by ToolPython
# entrypoint: python://protocol_fixture_loader
# hash: bf5bb8cf880cf140076cac1fdadb36e90d73eea09ea58a688afd214438208636
# last_modified_at: '2025-05-29T14:14:00.262385+00:00'
# lifecycle: active
# meta_type: tool
# metadata_version: 0.1.0
# name: protocol_fixture_loader.py
# namespace: python://omnibase.protocol.protocol_fixture_loader
# owner: OmniNode Team
# protocol_version: 0.1.0
# runtime_language_hint: python>=3.11
# schema_version: 0.1.0
# state_contract: state_contract://default
# tools: null
# uuid: 25f39f39-7b34-472f-8741-9b7a05cdd32f
# version: 1.0.0
# === /OmniNode:Metadata ===


"""
Protocol for fixture loading and discovery.

This module defines the minimal interface for fixture loaders that can
discover and load test fixtures from various sources (central, node-local).
"""

from typing import List, Protocol

from omnibase_core.model.validation.model_fixture_data import ModelFixtureData


class ProtocolFixtureLoader(Protocol):
    """
    Protocol for fixture loading and discovery.

    This minimal interface supports fixture discovery and loading for both
    central and node-scoped fixture directories, enabling extensibility
    and plugin scenarios.
    """

    def discover_fixtures(self) -> List[str]:
        """
        Return a list of available fixture names.

        Returns:
            List of fixture names that can be loaded by this loader.
        """
        ...

    def load_fixture(self, name: str) -> ModelFixtureData:
        """
        Load and return the fixture by name.

        Args:
            name: The name of the fixture to load.

        Returns:
            The loaded fixture object as a ModelFixtureData.

        Raises:
            FileNotFoundError: If the fixture is not found.
            OnexError: If the fixture cannot be loaded or parsed.
        """
        ...
