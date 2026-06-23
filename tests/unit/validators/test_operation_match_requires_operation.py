# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Tests for the operation_match 'operation' field guard (OMN-13530)."""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.validators.operation_match_requires_operation import (
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

_MISSING_CONTRACT = """\
name: example_broken
node_type: compute
handler_routing:
  routing_strategy: operation_match
  handlers:
    - handler:
        name: HandlerBroken
        module: pkg.nodes.node_broken.handlers.handler_broken
"""

_ABSENT_STRATEGY_CONTRACT = """\
name: example_absent
node_type: compute
handler_routing:
  handlers:
    - handler:
        name: HandlerAbsent
        module: pkg.nodes.node_absent.handlers.handler_absent
"""

_PAYLOAD_TYPE_MATCH_CONTRACT = """\
name: example_payload
node_type: compute
handler_routing:
  routing_strategy: payload_type_match
  handlers:
    - event_model:
        name: ModelExampleCommand
        module: pkg.nodes.node_example.models.model_example_command
      handler:
        name: HandlerExample
        module: pkg.nodes.node_example.handlers.handler_example
"""

_MULTI_HANDLER_PARTIAL = """\
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


def _write(tmp_path: Path, body: str) -> Path:
    contract = tmp_path / "contract.yaml"
    contract.write_text(body, encoding="utf-8")
    return contract


def test_passing_contract_has_no_findings(tmp_path: Path) -> None:
    contract = _write(tmp_path, _PASSING_CONTRACT)
    assert validate_file(contract) == []


def test_missing_operation_is_flagged(tmp_path: Path) -> None:
    contract = _write(tmp_path, _MISSING_CONTRACT)
    findings = validate_file(contract)
    assert len(findings) == 1
    assert findings[0].handler_index == 0
    assert findings[0].handler_name == "HandlerBroken"
    assert findings[0].strategy == "operation_match"


def test_absent_strategy_requires_operation(tmp_path: Path) -> None:
    # RuntimeLocal defaults an absent routing_strategy into the operation_match
    # branch, so an absent strategy with no operation must also be flagged.
    contract = _write(tmp_path, _ABSENT_STRATEGY_CONTRACT)
    findings = validate_file(contract)
    assert len(findings) == 1
    assert findings[0].handler_name == "HandlerAbsent"


def test_payload_type_match_is_exempt(tmp_path: Path) -> None:
    # payload_type_match routes by event_model, never by operation.
    contract = _write(tmp_path, _PAYLOAD_TYPE_MATCH_CONTRACT)
    assert validate_file(contract) == []


def test_multi_handler_only_flags_missing_entries(tmp_path: Path) -> None:
    contract = _write(tmp_path, _MULTI_HANDLER_PARTIAL)
    findings = validate_file(contract)
    assert len(findings) == 1
    assert findings[0].handler_index == 1
    assert findings[0].handler_name == "HandlerAnalyze"


def test_main_returns_nonzero_on_violation(tmp_path: Path) -> None:
    _write(tmp_path, _MISSING_CONTRACT)
    assert main([str(tmp_path)]) == 1


def test_main_returns_zero_when_clean(tmp_path: Path) -> None:
    _write(tmp_path, _PASSING_CONTRACT)
    assert main([str(tmp_path)]) == 0


def test_validate_paths_scans_directory_recursively(tmp_path: Path) -> None:
    nested = tmp_path / "nodes" / "node_broken"
    nested.mkdir(parents=True)
    (nested / "contract.yaml").write_text(_MISSING_CONTRACT, encoding="utf-8")
    good = tmp_path / "nodes" / "node_ok"
    good.mkdir(parents=True)
    (good / "contract.yaml").write_text(_PASSING_CONTRACT, encoding="utf-8")
    findings = validate_paths([tmp_path])
    assert len(findings) == 1
    assert findings[0].handler_name == "HandlerBroken"
