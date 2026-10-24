# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed ONEX metadata encoding measured from the skill corpus (OMN-21373)."""

import json
from typing import cast

from pydantic import JsonValue

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError

METADATA_PREFIX_ONEX = "onex."
METADATA_PREFIX_CLAUDE_CODE = "claude-code."
DECLARED_ONEX_KEY_TYPES: dict[str, str] = {
    **dict.fromkeys(
        (
            "mode",
            "version",
            "level",
            "category",
            "author",
            "skill_kind",
            "process_catalogue_row",
            "overlay_env",
            "runtime",
            "node_dispatch",
            "node_dispatch_dimensions",
            "ticket",
            "worker_template_version",
        ),
        "str",
    ),
    **dict.fromkeys(
        (
            "debug",
            "composable",
            "boundary_exempt",
            "user_invocable",
            "index",
            "foreground_orchestrator",
        ),
        "bool",
    ),
    "tags": "list[str]",
    **dict.fromkeys(("args", "inputs", "outputs"), "list[object]"),
}


def onex_value_error(key: str, value: object) -> str | None:
    """Return the rule message for an invalid declared ONEX value."""
    if key not in DECLARED_ONEX_KEY_TYPES:
        return f"reserved-metadata-prefix: onex.{key}"
    tag = DECLARED_ONEX_KEY_TYPES[key]
    valid = (
        (tag == "str" and isinstance(value, str))
        or (tag == "bool" and type(value) is bool)
        or (
            tag == "list[str]"
            and isinstance(value, list)
            and all(isinstance(v, str) for v in value)
        )
        or (
            tag == "list[object]"
            and isinstance(value, list)
            and all(isinstance(v, dict) for v in value)
        )
    )
    if not valid:
        return f"onex-value-type: {key}"
    return None


def encode_onex_value(key: str, value: JsonValue) -> str:
    """Encode every ONEX value as compact JSON, including strings."""
    error = onex_value_error(key, value)
    if error is not None:
        raise ModelOnexError(error, error_code=EnumCoreErrorCode.VALIDATION_ERROR)
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def decode_onex_value_result(key: str, text: str) -> tuple[JsonValue, str | None]:
    """Decode JSON and return a rule message without raising for invalid values."""
    if key not in DECLARED_ONEX_KEY_TYPES:
        return None, f"reserved-metadata-prefix: onex.{key}"
    try:
        value = json.loads(text)
    except ValueError:
        return None, f"onex-value-type: {key}"
    return cast("JsonValue", value), onex_value_error(key, value)


def decode_onex_value(key: str, text: str) -> JsonValue:
    """Decode JSON and check the corpus type for a declared ONEX key."""
    value, error = decode_onex_value_result(key, text)
    if error is not None:
        raise ModelOnexError(error, error_code=EnumCoreErrorCode.VALIDATION_ERROR)
    return value
