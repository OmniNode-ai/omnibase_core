# === OmniNode:Metadata ===
# metadata_version: 0.1.0
# protocol_version: 0.1.0
# owner: OmniNode Team
# copyright: OmniNode Team
# schema_version: 0.1.0
# name: utils_test_stamper_cases.py
# version: 1.0.0
# uuid: cdf74585-303a-4659-9c43-09b081d02ae2
# author: OmniNode Team
# created_at: 2025-05-21T12:41:40.173164
# last_modified_at: 2025-05-21T16:42:46.091223
# description: Stamped by ToolPython
# state_contract: state_contract://default
# lifecycle: active
# hash: 165d3bbebdb249c24cfc7e02d7ea25bb70b7b5c128b7c9ff4cfd1e595fe116dc
# entrypoint: python@utils_test_stamper_cases.py
# runtime_language_hint: python>=3.11
# namespace: onex.stamped.utils_test_stamper_cases
# meta_type: tool
# === /OmniNode:Metadata ===


"""
Registry-driven test case definitions for CLIStamper protocol tests.
Each case defines file content, type, expected status, and expected message.

Sticky field rule: 'created_at' is always preserved from the previous metadata block if present. If no previous block exists, the file's creation date is used. It is never updated on restamp.
"""

from collections.abc import Callable
from typing import Any

from omnibase_core.enums.enum_onex_status import EnumOnexStatus

STAMPER_TEST_CASES: dict[str, type] = {}


def register_stamper_test_case(name: str) -> Callable[[type], type]:
    """Decorator to register a test case class in the stamper test case registry."""

    def decorator(cls: type) -> type:
        STAMPER_TEST_CASES[name] = cls
        return cls

    return decorator


@register_stamper_test_case("valid_node_yaml")
class ValidNodeYaml:
    file_type: str = "yaml"

    def __init__(self) -> None:
        self.content: dict[str, Any] = {
            "metadata_version": "0.1.0",
            "protocol_version": "0.1.0",
            "owner": "foundation",
            "copyright": "Copyright foundation",
            "schema_version": "0.0.1",
            "name": "Stub Node",
            "version": "0.0.1",
            "uuid": "00000000-0000-0000-0000-000000000000",
            "author": "OmniNode Team",
            "created_at": "2024-01-01T00:00:00Z",
            "last_modified_at": "2024-01-01T00:00:00Z",
            "description": "Stub node for testing.",
            "state_contract": "stub://contract",
            "lifecycle": "draft",
            "hash": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
            "entrypoint": {"type": "python", "target": "main.py"},
            "namespace": "omninode.stub",
            "meta_type": "tool",
            "contract_type": "io_schema",
            "contract": {"inputs": {}, "outputs": {}},
        }
        self.expected_status: EnumOnexStatus = EnumOnexStatus.SUCCESS
        self.expected_message: str = "Simulated stamping for M0:"


@register_stamper_test_case("invalid_node_yaml")
class InvalidNodeYaml:
    file_type: str = "yaml"

    def __init__(self) -> None:
        self.content: dict[str, Any] = {
            "node_id": "test-node-id",
        }  # Missing required fields
        self.expected_status: EnumOnexStatus = EnumOnexStatus.ERROR
        self.expected_message: str = "Semantic validation failed:"


@register_stamper_test_case("empty_yaml")
class EmptyYaml:
    file_type: str = "yaml"

    def __init__(self) -> None:
        self.content: None = None
        self.expected_status: EnumOnexStatus = EnumOnexStatus.WARNING
        self.expected_message: str = "File is empty; stamped with empty status."


@register_stamper_test_case("malformed_yaml")
class MalformedYaml:
    file_type: str = "yaml"

    def __init__(self) -> None:
        self.content: str = "::not:yaml::"
        self.expected_status: EnumOnexStatus = EnumOnexStatus.ERROR
        self.expected_message: str = "Malformed YAML: not a mapping or sequence"


@register_stamper_test_case("valid_node_json")
class ValidNodeJson:
    file_type: str = "json"

    def __init__(self) -> None:
        self.content: dict[str, Any] = {
            "metadata_version": "0.1.0",
            "protocol_version": "0.1.0",
            "owner": "foundation",
            "copyright": "Copyright foundation",
            "schema_version": "0.0.1",
            "name": "Stub Node",
            "version": "0.0.1",
            "uuid": "00000000-0000-0000-0000-000000000000",
            "author": "OmniNode Team",
            "created_at": "2024-01-01T00:00:00Z",
            "last_modified_at": "2024-01-01T00:00:00Z",
            "description": "Stub node for testing.",
            "state_contract": "stub://contract",
            "lifecycle": "draft",
            "hash": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
            "entrypoint": {"type": "python", "target": "main.py"},
            "namespace": "omninode.stub",
            "meta_type": "tool",
            "contract_type": "io_schema",
            "contract": {"inputs": {}, "outputs": {}},
        }
        self.expected_status: EnumOnexStatus = EnumOnexStatus.SUCCESS
        self.expected_message: str = "Simulated stamping for M0:"


@register_stamper_test_case("invalid_node_json")
class InvalidNodeJson:
    file_type: str = "json"

    def __init__(self) -> None:
        self.content: dict[str, Any] = {"node_id": "test-node-id"}
        self.expected_status: EnumOnexStatus = EnumOnexStatus.ERROR
        self.expected_message: str = "Semantic validation failed:"


@register_stamper_test_case("empty_json")
class EmptyJson:
    file_type: str = "json"

    def __init__(self) -> None:
        self.content: None = None
        self.expected_status: EnumOnexStatus = EnumOnexStatus.WARNING
        self.expected_message: str = "File is empty; stamped with empty status."


@register_stamper_test_case("malformed_json")
class MalformedJson:
    file_type: str = "json"

    def __init__(self) -> None:
        self.content: str = "{not: json,]"
        self.expected_status: EnumOnexStatus = EnumOnexStatus.ERROR
        self.expected_message: str = "Malformed JSON: not a mapping or sequence"
