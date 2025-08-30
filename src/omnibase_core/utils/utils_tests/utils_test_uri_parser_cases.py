# === OmniNode:Metadata ===
# metadata_version: 0.1.0
# protocol_version: 0.1.0
# owner: OmniNode Team
# copyright: OmniNode Team
# schema_version: 0.1.0
# name: utils_test_uri_parser_cases.py
# version: 1.0.0
# uuid: 5e1e9cb0-83f7-4455-be5f-49cc5ce3a632
# author: OmniNode Team
# created_at: 2025-05-21T12:41:40.173231
# last_modified_at: 2025-05-21T16:42:46.045168
# description: Stamped by ToolPython
# state_contract: state_contract://default
# lifecycle: active
# hash: f645d1711e95b985e09a2040d27fee1bfd1de62fadf8a2976ba3c7489922b172
# entrypoint: python@utils_test_uri_parser_cases.py
# runtime_language_hint: python>=3.11
# namespace: onex.stamped.utils_test_uri_parser_cases
# meta_type: tool
# === /OmniNode:Metadata ===


from typing import Any, Callable

import pytest

from omnibase_core.enums import UriTypeEnum  # type: ignore[import-untyped]
from omnibase_core.exceptions import \
    OmniBaseError  # type: ignore[import-untyped]
from omnibase_core.model.core.model_uri import \
    ModelOnexUri  # type: ignore[import-untyped]

URI_PARSER_TEST_CASES: dict[str, type] = {}


def register_uri_parser_test_case(name: str) -> Callable[[type], type]:
    """Decorator to register a test case class in the URI parser test case registry."""

    def decorator(cls: type) -> type:
        URI_PARSER_TEST_CASES[name] = cls
        return cls

    return decorator


@register_uri_parser_test_case("valid_tool_uri")
class ValidToolUriCase:
    def run(self, parser: Any, context: Any) -> None:
        uri = "tool://core.schema_validator@1.0.0"
        result = parser.parse(uri)
        assert isinstance(result, ModelOnexUri)
        assert result.type == UriTypeEnum.TOOL
        assert result.namespace == "core.schema_validator"
        assert result.version_spec == "1.0.0"
        assert result.original == uri


@register_uri_parser_test_case("valid_validator_uri")
class ValidValidatorUriCase:
    def run(self, parser: Any, context: Any) -> None:
        uri = "validator://core.base@^1.0"
        result = parser.parse(uri)
        assert isinstance(result, ModelOnexUri)
        assert result.type == UriTypeEnum.VALIDATOR
        assert result.namespace == "core.base"
        assert result.version_spec == "^1.0"
        assert result.original == uri


@register_uri_parser_test_case("invalid_type_uri")
class InvalidTypeUriCase:
    def run(self, parser: Any, context: Any) -> None:
        uri = "notatype://foo.bar@1.0.0"
        with pytest.raises(OmniBaseError):
            parser.parse(uri)


@register_uri_parser_test_case("missing_version_uri")
class MissingVersionUriCase:
    def run(self, parser: Any, context: Any) -> None:
        uri = "tool://core.schema_validator"
        with pytest.raises(OmniBaseError):
            parser.parse(uri)


# TODO: Protocol-based extension and negative/edge cases in M1+
