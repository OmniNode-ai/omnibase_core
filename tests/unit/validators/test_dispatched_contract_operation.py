# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Tests for the dispatched-contract handlers[0].operation guard (OMN-13324)."""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.validators.dispatched_contract_operation import (
    main,
    validate_file,
    validate_paths,
)

pytestmark = pytest.mark.unit


_PASSING_CONTRACT = """\
name: example_compute
node_type: compute
handler_routing:
  routing_strategy: operation_match
  handlers:
    - operation: scan
      handler:
        name: HandlerExample
        module: pkg.nodes.node_example.handlers.handler_example
"""

_MISSING_OPERATION_CONTRACT = """\
name: example_broken
node_type: compute
handler_routing:
  routing_strategy: operation_match
  handlers:
    - handler:
        name: HandlerBroken
        module: pkg.nodes.node_broken.handlers.handler_broken
"""

# payload_type_match is EXEMPT in the operation_match guard (OMN-13530) but a
# dispatch target still needs handlers[0].operation for the unwrap (OMN-13324).
_PAYLOAD_TYPE_MATCH_MISSING = """\
name: example_payload_broken
node_type: compute
handler_routing:
  routing_strategy: payload_type_match
  handlers:
    - event_model:
        name: ModelExampleCommand
        module: pkg.nodes.node_example.models.model_example_command
      handler:
        name: HandlerPayload
        module: pkg.nodes.node_example.handlers.handler_payload
"""

_PAYLOAD_TYPE_MATCH_PRESENT = """\
name: example_payload_ok
node_type: compute
handler_routing:
  routing_strategy: payload_type_match
  handlers:
    - operation: dispatch
      event_model:
        name: ModelExampleCommand
        module: pkg.nodes.node_example.models.model_example_command
      handler:
        name: HandlerPayload
        module: pkg.nodes.node_example.handlers.handler_payload
"""

_ABSENT_STRATEGY_MISSING = """\
name: example_absent
node_type: compute
handler_routing:
  handlers:
    - handler:
        name: HandlerAbsent
        module: pkg.nodes.node_absent.handlers.handler_absent
"""

# Second handler missing operation does NOT trip this gate — it only asserts on
# handlers[0]. (OMN-13530 covers the rest.)
_FIRST_OK_SECOND_MISSING = """\
name: example_multi
node_type: effect
handler_routing:
  routing_strategy: operation_match
  handlers:
    - operation: embed
      handler:
        name: HandlerEmbed
        module: pkg.handlers.handler_embed
    - handler:
        name: HandlerAnalyze
        module: pkg.handlers.handler_analyze
"""

# No handler_routing.handlers list — not a dispatch target, out of scope.
_NO_HANDLERS_CONTRACT = """\
name: example_no_routing
node_type: compute
event_bus:
  subscribe_topics: []
"""

_EMPTY_OPERATION_CONTRACT = """\
name: example_empty_op
node_type: compute
handler_routing:
  routing_strategy: operation_match
  handlers:
    - operation: "   "
      handler:
        name: HandlerEmpty
        module: pkg.handlers.handler_empty
"""


def _write(tmp_path: Path, body: str) -> Path:
    contract = tmp_path / "contract.yaml"
    contract.write_text(body, encoding="utf-8")
    return contract


def test_passing_contract_has_no_finding(tmp_path: Path) -> None:
    contract = _write(tmp_path, _PASSING_CONTRACT)
    assert validate_file(contract) is None


def test_missing_operation_is_flagged(tmp_path: Path) -> None:
    contract = _write(tmp_path, _MISSING_OPERATION_CONTRACT)
    finding = validate_file(contract)
    assert finding is not None
    assert finding.handler_name == "HandlerBroken"
    assert finding.routing_strategy == "operation_match"


def test_payload_type_match_missing_is_flagged(tmp_path: Path) -> None:
    # Distinct from OMN-13530: payload_type_match is NOT exempt here because the
    # dispatch-envelope unwrap reads handlers[0].operation regardless of strategy.
    contract = _write(tmp_path, _PAYLOAD_TYPE_MATCH_MISSING)
    finding = validate_file(contract)
    assert finding is not None
    assert finding.handler_name == "HandlerPayload"
    assert finding.routing_strategy == "payload_type_match"


def test_payload_type_match_with_operation_passes(tmp_path: Path) -> None:
    contract = _write(tmp_path, _PAYLOAD_TYPE_MATCH_PRESENT)
    assert validate_file(contract) is None


def test_absent_strategy_missing_is_flagged(tmp_path: Path) -> None:
    contract = _write(tmp_path, _ABSENT_STRATEGY_MISSING)
    finding = validate_file(contract)
    assert finding is not None
    assert finding.handler_name == "HandlerAbsent"
    assert finding.routing_strategy == ""


def test_only_first_handler_is_checked(tmp_path: Path) -> None:
    # handlers[0] has an operation; handlers[1] does not — this gate is clean.
    contract = _write(tmp_path, _FIRST_OK_SECOND_MISSING)
    assert validate_file(contract) is None


def test_contract_without_handlers_is_out_of_scope(tmp_path: Path) -> None:
    contract = _write(tmp_path, _NO_HANDLERS_CONTRACT)
    assert validate_file(contract) is None


def test_whitespace_only_operation_is_flagged(tmp_path: Path) -> None:
    contract = _write(tmp_path, _EMPTY_OPERATION_CONTRACT)
    finding = validate_file(contract)
    assert finding is not None
    assert finding.handler_name == "HandlerEmpty"


def test_main_returns_nonzero_on_violation(tmp_path: Path) -> None:
    _write(tmp_path, _MISSING_OPERATION_CONTRACT)
    assert main([str(tmp_path)]) == 1


def test_main_returns_zero_when_clean(tmp_path: Path) -> None:
    _write(tmp_path, _PASSING_CONTRACT)
    assert main([str(tmp_path)]) == 0


def test_validate_paths_scans_directory_recursively(tmp_path: Path) -> None:
    broken = tmp_path / "nodes" / "node_broken"
    broken.mkdir(parents=True)
    (broken / "contract.yaml").write_text(_MISSING_OPERATION_CONTRACT, encoding="utf-8")
    good = tmp_path / "nodes" / "node_ok"
    good.mkdir(parents=True)
    (good / "contract.yaml").write_text(_PASSING_CONTRACT, encoding="utf-8")
    findings = validate_paths([tmp_path])
    assert len(findings) == 1
    assert findings[0].handler_name == "HandlerBroken"
