# === OmniNode:Metadata ===
# author: OmniNode Team
# copyright: OmniNode.ai
# created_at: '2025-05-28T13:24:08.164181'
# description: Stamped by ToolPython
# entrypoint: python://protocol_testable
# hash: e1782b2f9a3a9201f9035f8e5312fbe5ad2f46bf4702e2157c139ca38202c0f2
# last_modified_at: '2025-05-29T14:14:00.374254+00:00'
# lifecycle: active
# meta_type: tool
# metadata_version: 0.1.0
# name: protocol_testable.py
# namespace: python://omnibase.protocol.protocol_testable
# owner: OmniNode Team
# protocol_version: 0.1.0
# runtime_language_hint: python>=3.11
# schema_version: 0.1.0
# state_contract: state_contract://default
# tools: {}
# uuid: a608c2da-e860-4156-8bd7-cc615284eefb
# version: 1.0.0
# === /OmniNode:Metadata ===


"""
ProtocolTestable: Base protocol for all testable ONEX components.
This is a marker protocol for testable objects (registries, CLIs, tools, etc.).
Extend this for specific testable interfaces as needed.
"""

from typing import Protocol


class ProtocolTestable(Protocol):
    """
    Marker protocol for testable ONEX components.
    Extend for specific testable interfaces.
    """

    pass
