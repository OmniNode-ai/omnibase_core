# SPDX-FileCopyrightText: 2026 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Finding model for the FSM handler drift validator (OMN-13735).

The validator reconciles every reducer ``contract.yaml``'s
``state_machine.transitions`` (filtered to a declared FSM type's state set)
against the handler module's exported ``VALID_TRANSITIONS`` and
``GUARD_CONDITIONS`` Python symbols.

Finding kinds:
* ``TRANSITION_MISSING_IN_HANDLER`` (ERROR) — contract declares a transition
  that the handler's VALID_TRANSITIONS dict does not contain.
* ``TRANSITION_EXTRA_IN_HANDLER`` (ERROR) — handler's VALID_TRANSITIONS
  contains a transition not declared in the contract.
* ``TRANSITION_TO_STATE_MISMATCH`` (ERROR) — a shared (from_state, trigger)
  key resolves to a different to_state in contract vs handler.
* ``GUARD_MISSING_IN_HANDLER`` (ERROR) — contract declares a guard_condition
  for a transition but handler's GUARD_CONDITIONS has no entry for it.
* ``GUARD_FIELD_MISMATCH`` (ERROR) — guard's field name differs.
* ``GUARD_VALUE_MISMATCH`` (ERROR) — guard's required value differs.
* ``HANDLER_FILE_NOT_FOUND`` (ERROR) — the declared handler_module cannot be
  resolved to a file on disk.
* ``SYMBOL_NOT_FOUND`` (ERROR) — the handler file does not export the
  declared symbol name.
* ``SYMBOL_PARSE_ERROR`` (ERROR) — AST parsing of the handler file failed.
* ``CONTRACT_SCHEMA_ERROR`` (ERROR) — the contract YAML does not conform to
  the expected fsm_handler_binding schema.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from omnibase_core.enums.enum_fsm_handler_drift import (
    EnumFsmHandlerDriftKind,
    EnumFsmHandlerDriftSeverity,
)


@dataclass(frozen=True, slots=True)
class ModelFsmHandlerDriftFinding:
    """A single FSM handler drift finding."""

    severity: EnumFsmHandlerDriftSeverity
    kind: EnumFsmHandlerDriftKind
    node: str
    contract_path: Path
    fsm_type: str
    handler_module: str
    detail: str
    from_state: str | None = None
    trigger: str | None = None
    to_state_contract: str | None = None
    to_state_handler: str | None = None

    def format(self) -> str:
        transition = ""
        if self.from_state is not None and self.trigger is not None:
            transition = f" ({self.from_state!r}, {self.trigger!r})"
            if self.to_state_contract is not None:
                transition += f" -> contract:{self.to_state_contract!r}"
            if self.to_state_handler is not None:
                transition += f" handler:{self.to_state_handler!r}"
        return (
            f"{self.contract_path}: [{self.severity.value}] "
            f"node={self.node} fsm_type={self.fsm_type}{transition}: {self.detail}"
        )
