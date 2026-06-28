# SPDX-FileCopyrightText: 2026 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for the FSM handler drift validator (OMN-13735).

TDD — three mandatory cases:
  1. Injected divergence (TRANSITION_MISSING_IN_HANDLER) asserts findings are raised.
  2. Aligned handler passes with zero findings.
  3. Hook script exits non-zero on divergence fixture, zero on aligned fixture.
"""

from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from omnibase_core.enums.enum_fsm_handler_drift import EnumFsmHandlerDriftKind
from omnibase_core.validators.fsm_handler_drift import (
    discover_fsm_binding_contracts,
    main,
    validate_root,
)

pytestmark = pytest.mark.unit


# --------------------------------------------------------------------------- #
# Fixture helpers
# --------------------------------------------------------------------------- #


def _make_node(
    root: Path,
    *,
    node: str,
    contract_yaml: str,
    handler_py: str | None = None,
    handler_subpath: str = "handlers/handler_fsm.py",
    pkg: str = "mypkg",
) -> tuple[Path, Path | None]:
    """Write a minimal node directory with contract.yaml and optional handler.

    The node directory is placed at ``root/src/<pkg>/nodes/<node>/`` so that
    a handler_module of ``<pkg>.nodes.<node>.handlers.handler_fsm`` resolves via
    the default src_subdir="src" lookup.

    Returns (contract_path, handler_path_or_None).
    """
    node_dir = root / "src" / pkg / "nodes" / node
    node_dir.mkdir(parents=True, exist_ok=True)
    contract_path = node_dir / "contract.yaml"
    contract_path.write_text(textwrap.dedent(contract_yaml), encoding="utf-8")

    handler_path: Path | None = None
    if handler_py is not None:
        handler_full = node_dir / handler_subpath
        handler_full.parent.mkdir(parents=True, exist_ok=True)
        handler_full.write_text(textwrap.dedent(handler_py), encoding="utf-8")
        handler_path = handler_full

    return contract_path, handler_path


_ALIGNED_CONTRACT = """\
    state_machine:
      state_machine_name: "test_fsm"
      initial_state: "idle"
      states:
        - state_name: "active"
        - state_name: "inactive"
        - state_name: "deleted"
      transitions:
        - from_state: "active"
          to_state: "inactive"
          trigger: "deactivate"
        - from_state: "inactive"
          to_state: "active"
          trigger: "reactivate"
        - from_state: "active"
          to_state: "deleted"
          trigger: "delete"
          guard_conditions:
            - field: "actor_role"
              operator: "eq"
              value: "admin"
              error_message: "delete requires admin"
    fsm_handler_binding:
      - fsm_type: "MY_FSM"
        handler_module: "mypkg.nodes.node_test.handlers.handler_fsm"
        valid_transitions_symbol: "VALID_TRANSITIONS"
        guard_conditions_symbol: "GUARD_CONDITIONS"
        state_filter:
          - "active"
          - "inactive"
          - "deleted"
"""

_ALIGNED_HANDLER = """\
    from typing import Final
    VALID_TRANSITIONS: Final[dict[tuple[str, str], str]] = {
        ("active", "deactivate"): "inactive",
        ("inactive", "reactivate"): "active",
        ("active", "delete"): "deleted",
    }
    GUARD_CONDITIONS: Final[dict[tuple[str, str], tuple[str, str, str]]] = {
        ("active", "delete"): ("actor_role", "admin", "delete requires admin"),
    }
"""

_DIVERGED_HANDLER = """\
    from typing import Final
    # INJECTED DRIFT: removed ("inactive", "reactivate") -> "active"
    # and changed ("active", "delete") -> "archived" (wrong to_state)
    VALID_TRANSITIONS: Final[dict[tuple[str, str], str]] = {
        ("active", "deactivate"): "inactive",
        ("active", "delete"): "archived",
    }
    GUARD_CONDITIONS: Final[dict[tuple[str, str], tuple[str, str, str]]] = {
        ("active", "delete"): ("actor_role", "admin", "delete requires admin"),
    }
"""


# --------------------------------------------------------------------------- #
# TDD Case 1: Injected divergence raises findings
# --------------------------------------------------------------------------- #


def test_injected_divergence_raises_findings(tmp_path: Path) -> None:
    """TDD case 1: validator fires on injected YAML-vs-handler divergence.

    Divergence injected: handler VALID_TRANSITIONS is missing a transition that
    the contract declares, and has a wrong to_state for another.
    """
    _make_node(
        tmp_path,
        node="node_test",
        contract_yaml=_ALIGNED_CONTRACT,
        handler_py=_DIVERGED_HANDLER,
        handler_subpath="handlers/handler_fsm.py",
    )

    findings = validate_root(tmp_path)
    # Should find: TRANSITION_MISSING_IN_HANDLER for ("inactive", "reactivate")
    # and TRANSITION_TO_STATE_MISMATCH for ("active", "delete")
    assert len(findings) >= 2, (
        f"Expected at least 2 findings for injected drift, got {len(findings)}: "
        + "\n".join(f.format() for f in findings)
    )
    kinds = {f.kind for f in findings}
    assert EnumFsmHandlerDriftKind.TRANSITION_MISSING_IN_HANDLER in kinds, (
        f"Expected TRANSITION_MISSING_IN_HANDLER in {kinds}"
    )
    assert EnumFsmHandlerDriftKind.TRANSITION_TO_STATE_MISMATCH in kinds, (
        f"Expected TRANSITION_TO_STATE_MISMATCH in {kinds}"
    )


def test_injected_divergence_main_exits_nonzero(tmp_path: Path) -> None:
    """TDD case 1b: main() exits with code 1 on divergence."""
    _make_node(
        tmp_path,
        node="node_test",
        contract_yaml=_ALIGNED_CONTRACT,
        handler_py=_DIVERGED_HANDLER,
        handler_subpath="handlers/handler_fsm.py",
    )
    result = main([str(tmp_path)])
    assert result == 1, f"Expected exit code 1, got {result}"


# --------------------------------------------------------------------------- #
# TDD Case 2: Aligned handler passes with zero findings
# --------------------------------------------------------------------------- #


def test_aligned_handler_zero_findings(tmp_path: Path) -> None:
    """TDD case 2: zero findings when handler matches contract exactly."""
    _make_node(
        tmp_path,
        node="node_test",
        contract_yaml=_ALIGNED_CONTRACT,
        handler_py=_ALIGNED_HANDLER,
        handler_subpath="handlers/handler_fsm.py",
    )
    findings = validate_root(tmp_path)
    assert findings == [], "\n".join(f.format() for f in findings)


def test_aligned_handler_main_exits_zero(tmp_path: Path) -> None:
    """TDD case 2b: main() exits with code 0 on aligned fixture."""
    _make_node(
        tmp_path,
        node="node_test",
        contract_yaml=_ALIGNED_CONTRACT,
        handler_py=_ALIGNED_HANDLER,
        handler_subpath="handlers/handler_fsm.py",
    )
    result = main([str(tmp_path)])
    assert result == 0, f"Expected exit code 0, got {result}"


# --------------------------------------------------------------------------- #
# TDD Case 3: Hook script subprocess exit codes
# --------------------------------------------------------------------------- #


def test_hook_script_subprocess_nonzero_on_divergence(tmp_path: Path) -> None:
    """TDD case 3a: subprocess invocation exits non-zero on divergence fixture."""
    _make_node(
        tmp_path,
        node="node_test",
        contract_yaml=_ALIGNED_CONTRACT,
        handler_py=_DIVERGED_HANDLER,
        handler_subpath="handlers/handler_fsm.py",
    )
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "omnibase_core.validators.fsm_handler_drift",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1, (
        f"Expected exit code 1 (divergence), got {result.returncode}\n"
        f"stderr: {result.stderr}"
    )
    assert "ERROR" in result.stderr, f"Expected ERROR in stderr, got: {result.stderr}"


def test_hook_script_subprocess_zero_on_aligned(tmp_path: Path) -> None:
    """TDD case 3b: subprocess invocation exits zero on aligned fixture."""
    _make_node(
        tmp_path,
        node="node_test",
        contract_yaml=_ALIGNED_CONTRACT,
        handler_py=_ALIGNED_HANDLER,
        handler_subpath="handlers/handler_fsm.py",
    )
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "omnibase_core.validators.fsm_handler_drift",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        f"Expected exit code 0 (aligned), got {result.returncode}\n"
        f"stderr: {result.stderr}"
    )


# --------------------------------------------------------------------------- #
# Additional edge cases
# --------------------------------------------------------------------------- #


def test_no_fsm_binding_skipped(tmp_path: Path) -> None:
    """Contracts without fsm_handler_binding are silently skipped."""
    node_dir = tmp_path / "src" / "mypkg" / "nodes" / "node_plain"
    node_dir.mkdir(parents=True, exist_ok=True)
    (node_dir / "contract.yaml").write_text(
        "name: node_plain\nnode_type: COMPUTE\n", encoding="utf-8"
    )
    findings = validate_root(tmp_path)
    assert findings == []


def test_handler_file_not_found(tmp_path: Path) -> None:
    """Missing handler file produces HANDLER_FILE_NOT_FOUND finding."""
    contract_yaml = """\
        state_machine:
          state_machine_name: "x"
          initial_state: "a"
          states: []
          transitions: []
        fsm_handler_binding:
          - fsm_type: "X"
            handler_module: "nonexistent.module.handler"
            valid_transitions_symbol: "VALID_TRANSITIONS"
            state_filter: ["a"]
    """
    _make_node(
        tmp_path,
        node="node_nf",
        contract_yaml=contract_yaml,
    )
    findings = validate_root(tmp_path)
    assert len(findings) == 1
    assert findings[0].kind == EnumFsmHandlerDriftKind.HANDLER_FILE_NOT_FOUND


def test_extra_transition_in_handler(tmp_path: Path) -> None:
    """Handler with extra transition not in contract produces TRANSITION_EXTRA_IN_HANDLER."""
    contract_yaml = """\
        state_machine:
          state_machine_name: "x"
          initial_state: "a"
          states:
            - state_name: "a"
            - state_name: "b"
          transitions:
            - from_state: "a"
              to_state: "b"
              trigger: "go"
        fsm_handler_binding:
          - fsm_type: "X"
            handler_module: "mypkg.nodes.node_extra.handlers.handler_fsm"
            valid_transitions_symbol: "VALID_TRANSITIONS"
            state_filter: ["a", "b"]
    """
    handler_py = """\
        from typing import Final
        VALID_TRANSITIONS: Final[dict[tuple[str, str], str]] = {
            ("a", "go"): "b",
            ("b", "return"): "a",  # EXTRA: not in contract
        }
    """
    _make_node(
        tmp_path,
        node="node_extra",
        contract_yaml=contract_yaml,
        handler_py=handler_py,
        handler_subpath="handlers/handler_fsm.py",
    )
    findings = validate_root(tmp_path)
    assert any(
        f.kind == EnumFsmHandlerDriftKind.TRANSITION_EXTRA_IN_HANDLER for f in findings
    ), "\n".join(f.format() for f in findings)


def test_guard_value_mismatch(tmp_path: Path) -> None:
    """Guard value mismatch between contract and handler raises GUARD_VALUE_MISMATCH."""
    contract_yaml = """\
        state_machine:
          state_machine_name: "g"
          initial_state: "a"
          states:
            - state_name: "a"
            - state_name: "b"
          transitions:
            - from_state: "a"
              to_state: "b"
              trigger: "promote"
              guard_conditions:
                - field: "role"
                  operator: "eq"
                  value: "superadmin"
                  error_message: "requires superadmin"
        fsm_handler_binding:
          - fsm_type: "G"
            handler_module: "mypkg.nodes.node_guard.handlers.handler_fsm"
            valid_transitions_symbol: "VALID_TRANSITIONS"
            guard_conditions_symbol: "GUARD_CONDITIONS"
            state_filter: ["a", "b"]
    """
    handler_py = """\
        from typing import Final
        VALID_TRANSITIONS: Final[dict[tuple[str, str], str]] = {
            ("a", "promote"): "b",
        }
        GUARD_CONDITIONS: Final[dict[tuple[str, str], tuple[str, str, str]]] = {
            ("a", "promote"): ("role", "admin", "requires admin"),  # wrong value: admin vs superadmin
        }
    """
    _make_node(
        tmp_path,
        node="node_guard",
        contract_yaml=contract_yaml,
        handler_py=handler_py,
        handler_subpath="handlers/handler_fsm.py",
    )
    findings = validate_root(tmp_path)
    assert any(
        f.kind == EnumFsmHandlerDriftKind.GUARD_VALUE_MISMATCH for f in findings
    ), "\n".join(f.format() for f in findings)


def test_discover_no_contracts(tmp_path: Path) -> None:
    """Root with no contracts yields empty discovery list."""
    contracts = discover_fsm_binding_contracts(tmp_path)
    assert contracts == []


def test_contract_schema_error_missing_state_filter(tmp_path: Path) -> None:
    """fsm_handler_binding missing state_filter produces CONTRACT_SCHEMA_ERROR."""
    contract_yaml = """\
        state_machine:
          state_machine_name: "x"
          initial_state: "a"
          states: []
          transitions: []
        fsm_handler_binding:
          - fsm_type: "X"
            handler_module: "mypkg.handler"
            valid_transitions_symbol: "VALID_TRANSITIONS"
    """
    _make_node(tmp_path, node="node_schema", contract_yaml=contract_yaml)
    findings = validate_root(tmp_path)
    assert any(
        f.kind == EnumFsmHandlerDriftKind.CONTRACT_SCHEMA_ERROR for f in findings
    )
