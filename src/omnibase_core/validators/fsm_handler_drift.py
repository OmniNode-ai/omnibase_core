# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""FSM YAML-vs-handler drift validator (OMN-13735).

Mechanically enforces the invariant described in
``handler_pattern_lifecycle.py:61``: every ``VALID_TRANSITIONS`` and
``GUARD_CONDITIONS`` entry in a reducer handler must exactly mirror the
matching ``state_machine.transitions`` entries in the node's ``contract.yaml``.

The contract opts in by declaring a ``fsm_handler_binding`` section:

.. code-block:: yaml

    fsm_handler_binding:
      - fsm_type: "PATTERN_LIFECYCLE"
        handler_module: "omnimarket.nodes.node_intelligence_reducer.handlers.handler_pattern_lifecycle"
        valid_transitions_symbol: "VALID_TRANSITIONS"
        guard_conditions_symbol: "GUARD_CONDITIONS"
        state_filter:
          - "candidate"
          - "provisional"
          - "validated"
          - "deprecated"

The validator:
1. Finds all ``contract.yaml`` files with a ``fsm_handler_binding`` section.
2. For each binding, locates the handler file by resolving the dotted module
   path against the scan root's ``src/`` tree (no import required).
3. Extracts ``VALID_TRANSITIONS`` and ``GUARD_CONDITIONS`` via AST literal
   evaluation — no code execution, no dependency import.
4. Filters the contract's ``state_machine.transitions`` to only those whose
   ``from_state`` is in the binding's ``state_filter``.
5. Compares the two tables; emits a ``ModelFsmHandlerDriftFinding`` for every
   divergence — missing transitions, extra transitions, wrong to_state, guard
   field/value mismatches.

Zero allowlist entries. Every divergence is a hard block.

Usage::

    check-fsm-handler-drift [ROOT] [--src-subdir PATH]
    python -m omnibase_core.validators.fsm_handler_drift src/

ROOT defaults to the current working directory.
``--src-subdir`` overrides the default ``src`` sub-directory that contains the
Python package tree (used to locate handler files from dotted module paths).
"""

from __future__ import annotations

import argparse
import ast
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import yaml

from omnibase_core.enums.enum_fsm_handler_drift import (
    EnumFsmHandlerDriftKind,
    EnumFsmHandlerDriftSeverity,
)
from omnibase_core.models.validation.model_fsm_handler_drift_finding import (
    ModelFsmHandlerDriftFinding,
)

# Default sub-directory containing the Python package tree relative to repo root.
DEFAULT_SRC_SUBDIR = "src"

_ERROR = EnumFsmHandlerDriftSeverity.ERROR


# --------------------------------------------------------------------------- #
# Typed internal model for one fsm_handler_binding entry
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class _FsmHandlerBinding:
    fsm_type: str
    handler_module: str
    valid_transitions_symbol: str
    guard_conditions_symbol: str | None
    state_filter: frozenset[str]


# --------------------------------------------------------------------------- #
# Contract discovery
# --------------------------------------------------------------------------- #


def _is_fsm_binding_contract(data: object) -> bool:
    return (
        isinstance(data, dict)
        and isinstance(data.get("fsm_handler_binding"), list)
        and len(data["fsm_handler_binding"]) > 0
    )


def discover_fsm_binding_contracts(root: Path) -> list[Path]:
    """Return every ``contract.yaml`` under ``root`` that declares a fsm_handler_binding."""
    found: list[Path] = []
    for contract_path in sorted(root.rglob("contract.yaml")):
        if any(
            part in {"__pycache__", ".git", ".venv", "node_modules"}
            for part in contract_path.parts
        ):
            continue
        try:
            data = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
        except (yaml.YAMLError, UnicodeDecodeError, OSError):
            continue
        if _is_fsm_binding_contract(data):
            found.append(contract_path)
    return found


# --------------------------------------------------------------------------- #
# Binding schema parsing
# --------------------------------------------------------------------------- #


def _parse_bindings(
    data: dict[str, object],
    contract_path: Path,
    node: str,
) -> tuple[list[_FsmHandlerBinding], list[ModelFsmHandlerDriftFinding]]:
    """Parse and validate the ``fsm_handler_binding`` list from a contract.

    Returns (valid_bindings, schema_error_findings).
    """
    raw_bindings = data.get("fsm_handler_binding")
    if not isinstance(raw_bindings, list):
        return [], [
            ModelFsmHandlerDriftFinding(
                severity=_ERROR,
                kind=EnumFsmHandlerDriftKind.CONTRACT_SCHEMA_ERROR,
                node=node,
                contract_path=contract_path,
                fsm_type="",
                handler_module="",
                detail="fsm_handler_binding must be a list",
            )
        ]

    bindings: list[_FsmHandlerBinding] = []
    errors: list[ModelFsmHandlerDriftFinding] = []

    for idx, entry in enumerate(raw_bindings):
        if not isinstance(entry, dict):
            errors.append(
                ModelFsmHandlerDriftFinding(
                    severity=_ERROR,
                    kind=EnumFsmHandlerDriftKind.CONTRACT_SCHEMA_ERROR,
                    node=node,
                    contract_path=contract_path,
                    fsm_type="",
                    handler_module="",
                    detail=f"fsm_handler_binding[{idx}] must be a dict",
                )
            )
            continue

        fsm_type = entry.get("fsm_type")
        handler_module = entry.get("handler_module")
        valid_transitions_symbol = entry.get("valid_transitions_symbol")
        state_filter_raw = entry.get("state_filter")

        if not isinstance(fsm_type, str) or not fsm_type:
            errors.append(
                ModelFsmHandlerDriftFinding(
                    severity=_ERROR,
                    kind=EnumFsmHandlerDriftKind.CONTRACT_SCHEMA_ERROR,
                    node=node,
                    contract_path=contract_path,
                    fsm_type=str(fsm_type or ""),
                    handler_module=str(handler_module or ""),
                    detail=f"fsm_handler_binding[{idx}].fsm_type must be a non-empty string",
                )
            )
            continue
        if not isinstance(handler_module, str) or not handler_module:
            errors.append(
                ModelFsmHandlerDriftFinding(
                    severity=_ERROR,
                    kind=EnumFsmHandlerDriftKind.CONTRACT_SCHEMA_ERROR,
                    node=node,
                    contract_path=contract_path,
                    fsm_type=fsm_type,
                    handler_module="",
                    detail=f"fsm_handler_binding[{idx}].handler_module must be a non-empty string",
                )
            )
            continue
        if (
            not isinstance(valid_transitions_symbol, str)
            or not valid_transitions_symbol
        ):
            errors.append(
                ModelFsmHandlerDriftFinding(
                    severity=_ERROR,
                    kind=EnumFsmHandlerDriftKind.CONTRACT_SCHEMA_ERROR,
                    node=node,
                    contract_path=contract_path,
                    fsm_type=fsm_type,
                    handler_module=handler_module,
                    detail=(
                        f"fsm_handler_binding[{idx}].valid_transitions_symbol "
                        "must be a non-empty string"
                    ),
                )
            )
            continue
        if not isinstance(state_filter_raw, list) or not state_filter_raw:
            errors.append(
                ModelFsmHandlerDriftFinding(
                    severity=_ERROR,
                    kind=EnumFsmHandlerDriftKind.CONTRACT_SCHEMA_ERROR,
                    node=node,
                    contract_path=contract_path,
                    fsm_type=fsm_type,
                    handler_module=handler_module,
                    detail=(
                        f"fsm_handler_binding[{idx}].state_filter "
                        "must be a non-empty list of state name strings"
                    ),
                )
            )
            continue
        if not all(isinstance(s, str) for s in state_filter_raw):
            errors.append(
                ModelFsmHandlerDriftFinding(
                    severity=_ERROR,
                    kind=EnumFsmHandlerDriftKind.CONTRACT_SCHEMA_ERROR,
                    node=node,
                    contract_path=contract_path,
                    fsm_type=fsm_type,
                    handler_module=handler_module,
                    detail=(
                        f"fsm_handler_binding[{idx}].state_filter "
                        "every entry must be a string"
                    ),
                )
            )
            continue

        guard_symbol = entry.get("guard_conditions_symbol")
        guard_symbol_str: str | None = None
        if guard_symbol is not None:
            if not isinstance(guard_symbol, str) or not guard_symbol:
                errors.append(
                    ModelFsmHandlerDriftFinding(
                        severity=_ERROR,
                        kind=EnumFsmHandlerDriftKind.CONTRACT_SCHEMA_ERROR,
                        node=node,
                        contract_path=contract_path,
                        fsm_type=fsm_type,
                        handler_module=handler_module,
                        detail=(
                            f"fsm_handler_binding[{idx}].guard_conditions_symbol "
                            "must be a non-empty string when present"
                        ),
                    )
                )
                continue
            guard_symbol_str = guard_symbol

        bindings.append(
            _FsmHandlerBinding(
                fsm_type=fsm_type,
                handler_module=handler_module,
                valid_transitions_symbol=valid_transitions_symbol,
                guard_conditions_symbol=guard_symbol_str,
                state_filter=frozenset(str(s).lower() for s in state_filter_raw),
            )
        )

    return bindings, errors


# --------------------------------------------------------------------------- #
# Handler file resolution
# --------------------------------------------------------------------------- #


def _resolve_handler_file(
    handler_module: str,
    scan_root: Path,
    src_subdir: str = DEFAULT_SRC_SUBDIR,
) -> Path | None:
    """Resolve a dotted module path to a ``.py`` file path.

    Searches:
      1. ``<scan_root>/<src_subdir>/<module_as_path>.py``
      2. ``<scan_root>/<module_as_path>.py``

    Returns the first matching path, or ``None`` if neither exists.
    """
    rel = Path(*handler_module.split("."))
    candidates = [
        scan_root / src_subdir / rel.with_suffix(".py"),
        scan_root / rel.with_suffix(".py"),
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


# --------------------------------------------------------------------------- #
# AST symbol extraction
# --------------------------------------------------------------------------- #


def _extract_literal_symbol(
    source_path: Path,
    symbol_name: str,
) -> tuple[object | None, str | None]:
    """Extract a module-level literal constant by name via AST.

    Uses ``ast.literal_eval`` — no code execution, no import required.

    Returns (value, error_message). If successful, error_message is None.
    """
    try:
        source = source_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return None, f"cannot read handler file: {exc}"

    try:
        tree = ast.parse(source, filename=str(source_path))
    except SyntaxError as exc:
        return None, f"syntax error in handler file: {exc}"

    for node in ast.walk(tree):
        # Match annotated assignment: VALID_TRANSITIONS: Final[...] = {...}
        if isinstance(node, ast.AnnAssign):
            if (
                isinstance(node.target, ast.Name)
                and node.target.id == symbol_name
                and node.value is not None
            ):
                try:
                    return ast.literal_eval(node.value), None
                except (ValueError, TypeError) as exc:
                    return None, (
                        f"symbol {symbol_name!r} in {source_path} "
                        f"is not a literal expression: {exc}"
                    )
        # Match plain assignment: VALID_TRANSITIONS = {...}
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == symbol_name:
                    try:
                        return ast.literal_eval(node.value), None
                    except (ValueError, TypeError) as exc:
                        return None, (
                            f"symbol {symbol_name!r} in {source_path} "
                            f"is not a literal expression: {exc}"
                        )

    return None, f"symbol {symbol_name!r} not found in {source_path}"


# --------------------------------------------------------------------------- #
# Transition table normalization from contract YAML
# --------------------------------------------------------------------------- #


def _normalize_contract_transitions(
    state_machine: dict[str, object],
    state_filter: frozenset[str],
) -> dict[tuple[str, str], str]:
    """Extract (from_state, trigger) -> to_state from contract YAML transitions.

    Only includes transitions whose ``from_state`` is in ``state_filter``
    (case-insensitive).
    """
    transitions_raw = state_machine.get("transitions")
    if not isinstance(transitions_raw, list):
        return {}

    result: dict[tuple[str, str], str] = {}
    for t in transitions_raw:
        if not isinstance(t, dict):
            continue
        from_state = t.get("from_state")
        to_state = t.get("to_state")
        trigger = t.get("trigger")
        if not (
            isinstance(from_state, str)
            and isinstance(to_state, str)
            and isinstance(trigger, str)
        ):
            continue
        from_lower = from_state.lower()
        if from_lower not in state_filter:
            continue
        result[(from_lower, trigger.lower())] = to_state.lower()
    return result


def _normalize_contract_guards(
    state_machine: dict[str, object],
    state_filter: frozenset[str],
) -> dict[tuple[str, str], tuple[str, str]]:
    """Extract (from_state, trigger) -> (field, required_value) guards from contract YAML.

    Only includes guards on transitions whose ``from_state`` is in ``state_filter``.
    """
    transitions_raw = state_machine.get("transitions")
    if not isinstance(transitions_raw, list):
        return {}

    result: dict[tuple[str, str], tuple[str, str]] = {}
    for t in transitions_raw:
        if not isinstance(t, dict):
            continue
        from_state = t.get("from_state")
        trigger = t.get("trigger")
        guards = t.get("guard_conditions")
        if not (isinstance(from_state, str) and isinstance(trigger, str)):
            continue
        from_lower = from_state.lower()
        if from_lower not in state_filter:
            continue
        if not isinstance(guards, list) or not guards:
            continue
        # Take the first guard per transition (typical pattern)
        first = guards[0]
        if not isinstance(first, dict):
            continue
        field = first.get("field")
        value = first.get("value")
        if isinstance(field, str) and isinstance(value, str):
            result[(from_lower, trigger.lower())] = (field, value)
    return result


# --------------------------------------------------------------------------- #
# Handler VALID_TRANSITIONS normalization
# --------------------------------------------------------------------------- #


def _normalize_handler_transitions(
    raw: object,
    source_path: Path,
    node: str,
    contract_path: Path,
    fsm_type: str,
    handler_module: str,
) -> tuple[dict[tuple[str, str], str], list[ModelFsmHandlerDriftFinding]]:
    """Normalize the raw value of VALID_TRANSITIONS from AST literal eval.

    Expected shape: ``{(str, str): str, ...}``
    Returns (transitions_dict, error_findings).
    """
    if not isinstance(raw, dict):
        return {}, [
            ModelFsmHandlerDriftFinding(
                severity=_ERROR,
                kind=EnumFsmHandlerDriftKind.SYMBOL_PARSE_ERROR,
                node=node,
                contract_path=contract_path,
                fsm_type=fsm_type,
                handler_module=handler_module,
                detail=(
                    f"VALID_TRANSITIONS in {source_path} is not a dict "
                    f"(got {type(raw).__name__})"
                ),
            )
        ]

    result: dict[tuple[str, str], str] = {}
    errors: list[ModelFsmHandlerDriftFinding] = []
    for key, val in raw.items():
        if not (
            isinstance(key, tuple)
            and len(key) == 2
            and isinstance(key[0], str)
            and isinstance(key[1], str)
        ):
            errors.append(
                ModelFsmHandlerDriftFinding(
                    severity=_ERROR,
                    kind=EnumFsmHandlerDriftKind.SYMBOL_PARSE_ERROR,
                    node=node,
                    contract_path=contract_path,
                    fsm_type=fsm_type,
                    handler_module=handler_module,
                    detail=(
                        f"VALID_TRANSITIONS in {source_path}: "
                        f"key {key!r} is not a (str, str) tuple"
                    ),
                )
            )
            continue
        if not isinstance(val, str):
            errors.append(
                ModelFsmHandlerDriftFinding(
                    severity=_ERROR,
                    kind=EnumFsmHandlerDriftKind.SYMBOL_PARSE_ERROR,
                    node=node,
                    contract_path=contract_path,
                    fsm_type=fsm_type,
                    handler_module=handler_module,
                    detail=(
                        f"VALID_TRANSITIONS in {source_path}: "
                        f"value for key {key!r} is not a str (got {type(val).__name__})"
                    ),
                )
            )
            continue
        result[(key[0].lower(), key[1].lower())] = val.lower()
    return result, errors


def _normalize_handler_guards(
    raw: object,
    source_path: Path,
    node: str,
    contract_path: Path,
    fsm_type: str,
    handler_module: str,
) -> tuple[dict[tuple[str, str], tuple[str, str]], list[ModelFsmHandlerDriftFinding]]:
    """Normalize the raw value of GUARD_CONDITIONS from AST literal eval.

    Expected shape: ``{(str, str): (str, str, str), ...}``
    (from_state, trigger) -> (field, required_value, error_message)
    Returns (guards_dict, error_findings).
    """
    if not isinstance(raw, dict):
        return {}, [
            ModelFsmHandlerDriftFinding(
                severity=_ERROR,
                kind=EnumFsmHandlerDriftKind.SYMBOL_PARSE_ERROR,
                node=node,
                contract_path=contract_path,
                fsm_type=fsm_type,
                handler_module=handler_module,
                detail=(
                    f"GUARD_CONDITIONS in {source_path} is not a dict "
                    f"(got {type(raw).__name__})"
                ),
            )
        ]

    result: dict[tuple[str, str], tuple[str, str]] = {}
    errors: list[ModelFsmHandlerDriftFinding] = []
    for key, val in raw.items():
        if not (
            isinstance(key, tuple)
            and len(key) == 2
            and isinstance(key[0], str)
            and isinstance(key[1], str)
        ):
            errors.append(
                ModelFsmHandlerDriftFinding(
                    severity=_ERROR,
                    kind=EnumFsmHandlerDriftKind.SYMBOL_PARSE_ERROR,
                    node=node,
                    contract_path=contract_path,
                    fsm_type=fsm_type,
                    handler_module=handler_module,
                    detail=(
                        f"GUARD_CONDITIONS in {source_path}: "
                        f"key {key!r} is not a (str, str) tuple"
                    ),
                )
            )
            continue
        if not (
            isinstance(val, tuple)
            and len(val) >= 2
            and isinstance(val[0], str)
            and isinstance(val[1], str)
        ):
            errors.append(
                ModelFsmHandlerDriftFinding(
                    severity=_ERROR,
                    kind=EnumFsmHandlerDriftKind.SYMBOL_PARSE_ERROR,
                    node=node,
                    contract_path=contract_path,
                    fsm_type=fsm_type,
                    handler_module=handler_module,
                    detail=(
                        f"GUARD_CONDITIONS in {source_path}: "
                        f"value for key {key!r} must be a tuple of at least (str, str, ...)"
                    ),
                )
            )
            continue
        result[(key[0].lower(), key[1].lower())] = (val[0], val[1])
    return result, errors


# --------------------------------------------------------------------------- #
# Drift comparison
# --------------------------------------------------------------------------- #


def _diff_transitions(
    contract_transitions: dict[tuple[str, str], str],
    handler_transitions: dict[tuple[str, str], str],
    node: str,
    contract_path: Path,
    fsm_type: str,
    handler_module: str,
) -> list[ModelFsmHandlerDriftFinding]:
    findings: list[ModelFsmHandlerDriftFinding] = []

    all_keys = set(contract_transitions.keys()) | set(handler_transitions.keys())
    for key in sorted(all_keys):
        from_state, trigger = key
        in_contract = key in contract_transitions
        in_handler = key in handler_transitions

        if in_contract and not in_handler:
            findings.append(
                ModelFsmHandlerDriftFinding(
                    severity=_ERROR,
                    kind=EnumFsmHandlerDriftKind.TRANSITION_MISSING_IN_HANDLER,
                    node=node,
                    contract_path=contract_path,
                    fsm_type=fsm_type,
                    handler_module=handler_module,
                    from_state=from_state,
                    trigger=trigger,
                    to_state_contract=contract_transitions[key],
                    detail=(
                        f"contract declares ({from_state!r}, {trigger!r}) -> "
                        f"{contract_transitions[key]!r} but VALID_TRANSITIONS "
                        "has no such entry"
                    ),
                )
            )
        elif in_handler and not in_contract:
            findings.append(
                ModelFsmHandlerDriftFinding(
                    severity=_ERROR,
                    kind=EnumFsmHandlerDriftKind.TRANSITION_EXTRA_IN_HANDLER,
                    node=node,
                    contract_path=contract_path,
                    fsm_type=fsm_type,
                    handler_module=handler_module,
                    from_state=from_state,
                    trigger=trigger,
                    to_state_handler=handler_transitions[key],
                    detail=(
                        f"handler VALID_TRANSITIONS has ({from_state!r}, {trigger!r}) -> "
                        f"{handler_transitions[key]!r} but contract has no such transition "
                        f"for the {fsm_type} state_filter"
                    ),
                )
            )
        else:
            # Both present — check to_state agreement
            contract_to = contract_transitions[key]
            handler_to = handler_transitions[key]
            if contract_to != handler_to:
                findings.append(
                    ModelFsmHandlerDriftFinding(
                        severity=_ERROR,
                        kind=EnumFsmHandlerDriftKind.TRANSITION_TO_STATE_MISMATCH,
                        node=node,
                        contract_path=contract_path,
                        fsm_type=fsm_type,
                        handler_module=handler_module,
                        from_state=from_state,
                        trigger=trigger,
                        to_state_contract=contract_to,
                        to_state_handler=handler_to,
                        detail=(
                            f"({from_state!r}, {trigger!r}): contract says to_state="
                            f"{contract_to!r} but handler says {handler_to!r}"
                        ),
                    )
                )

    return findings


def _diff_guards(
    contract_guards: dict[tuple[str, str], tuple[str, str]],
    handler_guards: dict[tuple[str, str], tuple[str, str]],
    node: str,
    contract_path: Path,
    fsm_type: str,
    handler_module: str,
) -> list[ModelFsmHandlerDriftFinding]:
    findings: list[ModelFsmHandlerDriftFinding] = []

    for key in sorted(contract_guards.keys()):
        from_state, trigger = key
        if key not in handler_guards:
            findings.append(
                ModelFsmHandlerDriftFinding(
                    severity=_ERROR,
                    kind=EnumFsmHandlerDriftKind.GUARD_MISSING_IN_HANDLER,
                    node=node,
                    contract_path=contract_path,
                    fsm_type=fsm_type,
                    handler_module=handler_module,
                    from_state=from_state,
                    trigger=trigger,
                    detail=(
                        f"contract declares guard on ({from_state!r}, {trigger!r}) "
                        "but GUARD_CONDITIONS has no such entry"
                    ),
                )
            )
            continue

        contract_field, contract_value = contract_guards[key]
        handler_field, handler_value = handler_guards[key]

        if contract_field != handler_field:
            findings.append(
                ModelFsmHandlerDriftFinding(
                    severity=_ERROR,
                    kind=EnumFsmHandlerDriftKind.GUARD_FIELD_MISMATCH,
                    node=node,
                    contract_path=contract_path,
                    fsm_type=fsm_type,
                    handler_module=handler_module,
                    from_state=from_state,
                    trigger=trigger,
                    detail=(
                        f"guard for ({from_state!r}, {trigger!r}): "
                        f"contract field={contract_field!r} but handler field={handler_field!r}"
                    ),
                )
            )
        if contract_value != handler_value:
            findings.append(
                ModelFsmHandlerDriftFinding(
                    severity=_ERROR,
                    kind=EnumFsmHandlerDriftKind.GUARD_VALUE_MISMATCH,
                    node=node,
                    contract_path=contract_path,
                    fsm_type=fsm_type,
                    handler_module=handler_module,
                    from_state=from_state,
                    trigger=trigger,
                    detail=(
                        f"guard for ({from_state!r}, {trigger!r}): "
                        f"contract value={contract_value!r} but handler value={handler_value!r}"
                    ),
                )
            )

    # Extra guards in handler not in contract are also a drift
    for key in sorted(handler_guards.keys()):
        if key not in contract_guards:
            from_state, trigger = key
            handler_field, handler_value = handler_guards[key]
            findings.append(
                ModelFsmHandlerDriftFinding(
                    severity=_ERROR,
                    kind=EnumFsmHandlerDriftKind.GUARD_MISSING_IN_HANDLER,
                    node=node,
                    contract_path=contract_path,
                    fsm_type=fsm_type,
                    handler_module=handler_module,
                    from_state=from_state,
                    trigger=trigger,
                    detail=(
                        f"handler GUARD_CONDITIONS has ({from_state!r}, {trigger!r}) "
                        f"with field={handler_field!r}/value={handler_value!r} "
                        "but contract declares no guard for this transition"
                    ),
                )
            )

    return findings


# --------------------------------------------------------------------------- #
# Per-contract validation
# --------------------------------------------------------------------------- #


def validate_contract(
    contract_path: Path,
    scan_root: Path,
    src_subdir: str = DEFAULT_SRC_SUBDIR,
) -> list[ModelFsmHandlerDriftFinding]:
    """Validate one contract's fsm_handler_binding entries."""
    try:
        data = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
    except (yaml.YAMLError, UnicodeDecodeError, OSError):
        return []

    if not _is_fsm_binding_contract(data):
        return []

    node_dir = contract_path.parent
    node = node_dir.name
    all_findings: list[ModelFsmHandlerDriftFinding] = []

    bindings, schema_errors = _parse_bindings(data, contract_path, node)
    all_findings.extend(schema_errors)

    state_machine = data.get("state_machine")
    if not isinstance(state_machine, dict) and bindings:
        all_findings.append(
            ModelFsmHandlerDriftFinding(
                severity=_ERROR,
                kind=EnumFsmHandlerDriftKind.CONTRACT_SCHEMA_ERROR,
                node=node,
                contract_path=contract_path,
                fsm_type="",
                handler_module="",
                detail="contract has fsm_handler_binding but no state_machine section",
            )
        )
        return all_findings

    for binding in bindings:
        # 1. Resolve handler file
        handler_file = _resolve_handler_file(
            binding.handler_module, scan_root, src_subdir
        )
        if handler_file is None:
            all_findings.append(
                ModelFsmHandlerDriftFinding(
                    severity=_ERROR,
                    kind=EnumFsmHandlerDriftKind.HANDLER_FILE_NOT_FOUND,
                    node=node,
                    contract_path=contract_path,
                    fsm_type=binding.fsm_type,
                    handler_module=binding.handler_module,
                    detail=(
                        f"handler_module {binding.handler_module!r} could not be resolved "
                        f"to a file under {scan_root}/{src_subdir}/ or {scan_root}/"
                    ),
                )
            )
            continue

        # 2. Extract VALID_TRANSITIONS via AST
        raw_vt, vt_err = _extract_literal_symbol(
            handler_file, binding.valid_transitions_symbol
        )
        if vt_err is not None:
            all_findings.append(
                ModelFsmHandlerDriftFinding(
                    severity=_ERROR,
                    kind=EnumFsmHandlerDriftKind.SYMBOL_NOT_FOUND
                    if "not found" in vt_err
                    else EnumFsmHandlerDriftKind.SYMBOL_PARSE_ERROR,
                    node=node,
                    contract_path=contract_path,
                    fsm_type=binding.fsm_type,
                    handler_module=binding.handler_module,
                    detail=vt_err,
                )
            )
            continue

        handler_transitions, norm_errors = _normalize_handler_transitions(
            raw_vt,
            handler_file,
            node,
            contract_path,
            binding.fsm_type,
            binding.handler_module,
        )
        all_findings.extend(norm_errors)
        if norm_errors:
            continue

        # 3. Normalize contract transitions (filtered by state_filter)
        assert isinstance(state_machine, dict)  # guaranteed above
        contract_transitions = _normalize_contract_transitions(
            state_machine, binding.state_filter
        )

        # 4. Diff transitions
        all_findings.extend(
            _diff_transitions(
                contract_transitions,
                handler_transitions,
                node,
                contract_path,
                binding.fsm_type,
                binding.handler_module,
            )
        )

        # 5. Extract and diff GUARD_CONDITIONS if declared
        if binding.guard_conditions_symbol:
            raw_gc, gc_err = _extract_literal_symbol(
                handler_file, binding.guard_conditions_symbol
            )
            if gc_err is not None:
                all_findings.append(
                    ModelFsmHandlerDriftFinding(
                        severity=_ERROR,
                        kind=EnumFsmHandlerDriftKind.SYMBOL_NOT_FOUND
                        if "not found" in gc_err
                        else EnumFsmHandlerDriftKind.SYMBOL_PARSE_ERROR,
                        node=node,
                        contract_path=contract_path,
                        fsm_type=binding.fsm_type,
                        handler_module=binding.handler_module,
                        detail=gc_err,
                    )
                )
            else:
                handler_guards, guard_norm_errors = _normalize_handler_guards(
                    raw_gc,
                    handler_file,
                    node,
                    contract_path,
                    binding.fsm_type,
                    binding.handler_module,
                )
                all_findings.extend(guard_norm_errors)
                if not guard_norm_errors:
                    contract_guards = _normalize_contract_guards(
                        state_machine, binding.state_filter
                    )
                    all_findings.extend(
                        _diff_guards(
                            contract_guards,
                            handler_guards,
                            node,
                            contract_path,
                            binding.fsm_type,
                            binding.handler_module,
                        )
                    )

    return all_findings


def validate_root(
    root: Path,
    src_subdir: str = DEFAULT_SRC_SUBDIR,
) -> list[ModelFsmHandlerDriftFinding]:
    """Validate every contract with fsm_handler_binding discovered under ``root``."""
    findings: list[ModelFsmHandlerDriftFinding] = []
    for contract_path in discover_fsm_binding_contracts(root):
        findings.extend(validate_contract(contract_path, root, src_subdir))
    return findings


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def _parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Reconcile reducer node contract.yaml fsm_handler_binding declarations "
            "against the handler module's VALID_TRANSITIONS and GUARD_CONDITIONS symbols."
        )
    )
    parser.add_argument(
        "root",
        nargs="?",
        type=Path,
        default=Path(),
        help="Repository root to scan for contracts (default: cwd).",
    )
    parser.add_argument(
        "--src-subdir",
        default=DEFAULT_SRC_SUBDIR,
        help=(
            "Sub-directory under root containing the Python package tree "
            f"(default: {DEFAULT_SRC_SUBDIR!r})."
        ),
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    findings = validate_root(args.root, args.src_subdir)

    for finding in findings:
        sys.stderr.write(f"ERROR {finding.format()}\n")

    if findings:
        sys.stderr.write(
            f"\nfsm-handler-drift: {len(findings)} blocking error(s) — "
            "the handler's VALID_TRANSITIONS or GUARD_CONDITIONS diverges from the "
            "contract's state_machine.transitions. Fix the handler or the contract "
            "to restore alignment.\n"
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())  # error-ok: CLI entry point requires SystemExit
