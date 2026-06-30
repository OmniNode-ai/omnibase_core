# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Tests for the command-category 'event_model' field guard (OMN-13028).

A handler_routing entry tagged ``message_category: command`` must declare a
non-empty ``event_model`` block. This closes ladder layer 1 of OMN-13003/13005
(a command handler whose contract omitted ``event_model``) at commit time.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.validators.command_category_requires_event_model import (
    main,
    validate_file,
    validate_paths,
)

pytestmark = pytest.mark.unit


_COMPLIANT_COMMAND = """\
name: example_orchestrator
node_type: orchestrator
handler_routing:
  routing_strategy: payload_type_match
  handlers:
    - message_category: command
      event_model:
        name: ModelExampleCommand
        module: pkg.nodes.node_example.models.model_example_command
      handler:
        name: HandlerExample
        module: pkg.nodes.node_example.handlers.handler_example
"""

_MISSING_EVENT_MODEL = """\
name: example_broken
node_type: orchestrator
handler_routing:
  routing_strategy: payload_type_match
  handlers:
    - message_category: command
      handler:
        name: HandlerBroken
        module: pkg.nodes.node_broken.handlers.handler_broken
"""

_EVENT_CATEGORY_NO_EVENT_MODEL = """\
name: example_event
node_type: orchestrator
handler_routing:
  routing_strategy: payload_type_match
  handlers:
    - message_category: event
      handler:
        name: HandlerEvent
        module: pkg.handlers.handler_event
"""

_NO_CATEGORY = """\
name: example_no_category
node_type: compute
handler_routing:
  routing_strategy: operation_match
  handlers:
    - operation: scan
      handler:
        name: HandlerScan
        module: pkg.handlers.handler_scan
"""

_COMMAND_EMPTY_EVENT_MODEL = """\
name: example_empty
node_type: orchestrator
handler_routing:
  routing_strategy: payload_type_match
  handlers:
    - message_category: command
      event_model: {}
      handler:
        name: HandlerEmpty
        module: pkg.handlers.handler_empty
"""

_MULTI_HANDLER_PARTIAL = """\
name: example_multi
node_type: orchestrator
handler_routing:
  routing_strategy: payload_type_match
  handlers:
    - message_category: command
      event_model:
        name: ModelGoodCommand
        module: pkg.models.model_good_command
      handler:
        name: HandlerGood
        module: pkg.handlers.handler_good
    - message_category: command
      handler:
        name: HandlerBad
        module: pkg.handlers.handler_bad
"""

_LEGACY_FLAT_COMMAND_MISSING = """\
name: example_flat
node_type: compute
handler_routing:
  routing_strategy: payload_type_match
  handlers:
    - routing_key: ModelExampleCommand
      handler_key: handle_example
      message_category: command
"""


def _write(tmp_path: Path, body: str) -> Path:
    contract = tmp_path / "contract.yaml"
    contract.write_text(body, encoding="utf-8")
    return contract


def test_compliant_command_has_no_findings(tmp_path: Path) -> None:
    contract = _write(tmp_path, _COMPLIANT_COMMAND)
    assert validate_file(contract) == []


def test_command_missing_event_model_is_flagged(tmp_path: Path) -> None:
    contract = _write(tmp_path, _MISSING_EVENT_MODEL)
    findings = validate_file(contract)
    assert len(findings) == 1
    assert findings[0].handler_index == 0
    assert findings[0].handler_name == "HandlerBroken"


def test_event_category_is_exempt(tmp_path: Path) -> None:
    # Only command-category entries require event_model; event-category does not.
    contract = _write(tmp_path, _EVENT_CATEGORY_NO_EVENT_MODEL)
    assert validate_file(contract) == []


def test_absent_category_is_exempt(tmp_path: Path) -> None:
    # An entry with no message_category at all is out of scope for this guard.
    contract = _write(tmp_path, _NO_CATEGORY)
    assert validate_file(contract) == []


def test_command_with_empty_event_model_is_flagged(tmp_path: Path) -> None:
    # An empty event_model block is as bad as an absent one.
    contract = _write(tmp_path, _COMMAND_EMPTY_EVENT_MODEL)
    findings = validate_file(contract)
    assert len(findings) == 1
    assert findings[0].handler_name == "HandlerEmpty"


def test_multi_handler_only_flags_missing_entries(tmp_path: Path) -> None:
    contract = _write(tmp_path, _MULTI_HANDLER_PARTIAL)
    findings = validate_file(contract)
    assert len(findings) == 1
    assert findings[0].handler_index == 1
    assert findings[0].handler_name == "HandlerBad"


def test_legacy_flat_command_missing_event_model_is_flagged(tmp_path: Path) -> None:
    # Legacy routing_key/handler_key shape still requires event_model when the
    # entry is tagged message_category: command.
    contract = _write(tmp_path, _LEGACY_FLAT_COMMAND_MISSING)
    findings = validate_file(contract)
    assert len(findings) == 1
    assert findings[0].handler_name == "handle_example"


def test_main_returns_nonzero_on_violation(tmp_path: Path) -> None:
    _write(tmp_path, _MISSING_EVENT_MODEL)
    assert main([str(tmp_path)]) == 1


def test_main_returns_zero_when_clean(tmp_path: Path) -> None:
    _write(tmp_path, _COMPLIANT_COMMAND)
    assert main([str(tmp_path)]) == 0


def test_validate_paths_scans_directory_recursively(tmp_path: Path) -> None:
    nested = tmp_path / "nodes" / "node_broken"
    nested.mkdir(parents=True)
    (nested / "contract.yaml").write_text(_MISSING_EVENT_MODEL, encoding="utf-8")
    good = tmp_path / "nodes" / "node_ok"
    good.mkdir(parents=True)
    (good / "contract.yaml").write_text(_COMPLIANT_COMMAND, encoding="utf-8")
    findings = validate_paths([tmp_path])
    assert len(findings) == 1
    assert findings[0].handler_name == "HandlerBroken"


def test_non_dict_yaml_is_ignored(tmp_path: Path) -> None:
    contract = _write(tmp_path, "- just\n- a\n- list\n")
    assert validate_file(contract) == []


def test_invalid_yaml_is_ignored(tmp_path: Path) -> None:
    contract = _write(tmp_path, "name: [unterminated\n")
    assert validate_file(contract) == []
