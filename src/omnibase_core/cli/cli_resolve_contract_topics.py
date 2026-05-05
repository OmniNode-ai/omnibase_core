# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Reusable contract-to-topics resolver for ONEX CLI dispatch (OMN-10512).

Provides two functions usable outside Click commands:
- resolve_node_contract: entry-point name → contract.yaml Path
- resolve_contract_topics: contract.yaml Path → (command_topic, terminal_topic)

Key distinction from dispatch_bus_client._resolve_command_topic: that function
reads publish_topics (what the node publishes TO). This reads subscribe_topics
(what the node listens ON), because the CLI is the sender.
"""

from __future__ import annotations

import importlib.util
import warnings
from importlib.metadata import entry_points
from pathlib import Path

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.core.model_generic_yaml import ModelGenericYaml
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.utils.util_safe_yaml_loader import load_and_validate_yaml_model


def resolve_node_contract(node_id: str) -> Path:
    """Resolve a node ID via the ``onex.nodes`` entry-point group to its contract.yaml.

    Raises:
        ModelOnexError: If the node is unknown, duplicated, the module cannot be
            found, or the packaged contract.yaml is missing.
    """
    matches = [ep for ep in entry_points(group="onex.nodes") if ep.name == node_id]
    if not matches:
        known = sorted({ep.name for ep in entry_points(group="onex.nodes")})
        raise ModelOnexError(
            message=f"Unknown node '{node_id}'. Known nodes: {', '.join(known) or '(none)'}",
            error_code=EnumCoreErrorCode.NOT_FOUND,
        )
    if len(matches) > 1:
        sources = ", ".join(str(ep.dist) for ep in matches)
        raise ModelOnexError(
            message=(
                f"Duplicate entry-point name '{node_id}' registered by: {sources}. "
                "Disambiguate by uninstalling the conflicting package."
            ),
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        )

    module_path = matches[0].value.split(":", 1)[0].strip()
    spec = importlib.util.find_spec(module_path)
    if spec is None:
        raise ModelOnexError(
            message=f"Failed to resolve node module '{module_path}' from installed metadata.",
            error_code=EnumCoreErrorCode.MODULE_NOT_FOUND,
        )

    if spec.submodule_search_locations:
        module_dir = Path(next(iter(spec.submodule_search_locations))).resolve()
    elif spec.origin is not None:
        module_dir = Path(spec.origin).resolve().parent
    else:
        raise ModelOnexError(
            message=(
                f"Node '{node_id}' module '{module_path}' has no origin; "
                "cannot locate packaged contract.yaml under current packaging convention."
            ),
            error_code=EnumCoreErrorCode.MODULE_NOT_FOUND,
        )

    contract = module_dir / "contract.yaml"
    if not contract.exists():
        raise ModelOnexError(
            message=(
                f"Node '{node_id}' resolved to {module_dir} but no contract.yaml found there. "
                "This violates the current packaging convention (colocated contract.yaml)."
            ),
            error_code=EnumCoreErrorCode.FILE_NOT_FOUND,
        )
    return contract


def resolve_contract_topics(contract_path: Path) -> tuple[str, str]:
    """Resolve command and terminal topics from a contract.yaml.

    Command topic resolution priority:
      (a) explicit event_bus.command_topic if present
      (b) subscribe_topics[0] as compatibility fallback (warns to stderr if
          multiple subscribe topics exist)

    Returns:
        (command_topic, terminal_topic)

    Raises:
        ModelOnexError: If subscribe_topics or terminal_event is missing or
            cannot be resolved, with a message naming the contract path.
    """
    raw_model = load_and_validate_yaml_model(contract_path, ModelGenericYaml)
    data: dict[str, object] = raw_model.model_dump(mode="json", exclude_none=True)

    command_topic = _resolve_subscribe_topic(data, contract_path)
    terminal_topic = _resolve_terminal_topic(data, contract_path)
    return command_topic, terminal_topic


def _resolve_subscribe_topic(data: dict[str, object], contract_path: Path) -> str:
    # Priority (a): explicit event_bus.command_topic
    event_bus = data.get("event_bus")
    if isinstance(event_bus, dict):
        command_topic = event_bus.get("command_topic")
        if isinstance(command_topic, str) and command_topic:
            return command_topic

    # Priority (b): subscribe_topics[0]
    subscribe_topics = data.get("subscribe_topics")
    if not isinstance(subscribe_topics, list) or not subscribe_topics:
        raise ModelOnexError(
            message=(
                f"Contract at {contract_path} has no subscribe_topics. "
                "Cannot resolve command topic for CLI dispatch."
            ),
            error_code=EnumCoreErrorCode.CONTRACT_VALIDATION_ERROR,
        )

    first = subscribe_topics[0]
    if not isinstance(first, str) or not first:
        raise ModelOnexError(
            message=(
                f"Contract at {contract_path} subscribe_topics[0] is not a non-empty string."
            ),
            error_code=EnumCoreErrorCode.CONTRACT_VALIDATION_ERROR,
        )

    if len(subscribe_topics) > 1:
        warnings.warn(
            f"Contract at {contract_path} has multiple subscribe_topics; "
            f"using first: {first!r}",
            stacklevel=3,
        )

    return first


def _resolve_terminal_topic(data: dict[str, object], contract_path: Path) -> str:
    terminal_event = data.get("terminal_event")
    if isinstance(terminal_event, str) and terminal_event:
        return terminal_event
    if isinstance(terminal_event, dict):
        topic = terminal_event.get("topic")
        if isinstance(topic, str) and topic:
            return topic

    raise ModelOnexError(
        message=(
            f"Contract at {contract_path} has no terminal_event. "
            "Cannot resolve terminal topic for CLI dispatch."
        ),
        error_code=EnumCoreErrorCode.CONTRACT_VALIDATION_ERROR,
    )


__all__ = [
    "resolve_contract_topics",
    "resolve_node_contract",
]
