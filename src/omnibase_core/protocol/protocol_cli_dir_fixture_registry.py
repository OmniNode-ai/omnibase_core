# === OmniNode:Metadata ===
# author: OmniNode Team
# copyright: OmniNode.ai
# created_at: '2025-05-28T12:36:27.107363'
# description: Stamped by ToolPython
# entrypoint: python://protocol_cli_dir_fixture_registry
# hash: 4daa909a56d9715e10891fe06652b3047c4213e1e68626bfd89a9e9a9a34ae54
# last_modified_at: '2025-05-29T14:14:00.199570+00:00'
# lifecycle: active
# meta_type: tool
# metadata_version: 0.1.0
# name: protocol_cli_dir_fixture_registry.py
# namespace: python://omnibase.protocol.protocol_cli_dir_fixture_registry
# owner: OmniNode Team
# protocol_version: 0.1.0
# runtime_language_hint: python>=3.11
# schema_version: 0.1.0
# state_contract: state_contract://default
# tools: null
# uuid: 7d1d402a-1d9f-4beb-bd31-4675534a97fb
# version: 1.0.0
# === /OmniNode:Metadata ===


from collections.abc import Callable
from typing import Protocol
from unittest import mock

import pytest

from omnibase_core.protocol.protocol_cli_dir_fixture_case import (
    ProtocolCLIDirFixtureCase,
)


class ProtocolCLIDirFixtureRegistry(Protocol):
    def all_cases(self) -> list[ProtocolCLIDirFixtureCase]: ...

    def get_case(self, case_id: str) -> ProtocolCLIDirFixtureCase: ...

    def filter_cases(
        self,
        predicate: Callable[[ProtocolCLIDirFixtureCase], bool],
    ) -> list[ProtocolCLIDirFixtureCase]: ...


@pytest.fixture
def cli_fixture_registry() -> ProtocolCLIDirFixtureRegistry:
    # Implementation of the fixture
    return mock.MagicMock(spec=ProtocolCLIDirFixtureRegistry)
