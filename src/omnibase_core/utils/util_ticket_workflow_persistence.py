# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Persistence helpers for ``ModelTicketWorkflowState``.

Provides extraction, in-description updates, and on-disk persistence for the
workflow state YAML embedded in Linear ticket descriptions.

``persist_workflow_state_locally`` writes to ``$ONEX_STATE_DIR/tickets/``.
``~/.claude/tickets/`` is never written to by any path in this module (CLAUDE.md
agent-session write rule — see OMN-9142).
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from omnibase_core.models.ticket.model_ticket_workflow_state import (
    ModelTicketWorkflowState,
)

_CONTRACT_MARKER = "## Contract"
_YAML_FENCE_RE = re.compile(r"```(?:yaml|YAML)?\s*\n(.*?)\n\s*```", re.DOTALL)


def workflow_state_to_yaml(state: ModelTicketWorkflowState) -> str:
    """Serialize a workflow state to YAML for embedding in a ticket description."""
    data = state.model_dump(mode="json", exclude_none=False)
    return yaml.safe_dump(data, default_flow_style=False, sort_keys=False)


def extract_workflow_state(description: str) -> ModelTicketWorkflowState | None:
    """Extract and parse the workflow-state YAML from a Linear description.

    Looks for the last ``## Contract`` section with a fenced yaml block.
    Returns ``None`` if the marker is missing, the fence is missing, the YAML
    is malformed, or validation against ``ModelTicketWorkflowState`` fails.
    """
    if _CONTRACT_MARKER not in description:
        return None

    idx = description.rfind(_CONTRACT_MARKER)
    contract_section = description[idx:]

    match = _YAML_FENCE_RE.search(contract_section)
    if not match:
        return None

    # Parse then validate: the YAML fence may contain arbitrary Markdown
    # content on disk, so bad input must degrade to ``None`` rather than
    # raising. ``yaml.safe_load`` (no Python-object tags) is sufficient here
    # because the only consumers are Pydantic-validated below.
    try:
        raw: Any = yaml.safe_load(match.group(1))
    except yaml.YAMLError:
        return None

    if not isinstance(raw, dict):
        return None

    try:
        return ModelTicketWorkflowState.model_validate(raw)
    except ValidationError:
        return None


def update_description_with_workflow_state(
    description: str, state: ModelTicketWorkflowState
) -> str:
    """Insert or replace the ``## Contract`` YAML block in a ticket description."""
    contract_yaml = workflow_state_to_yaml(state)
    contract_block = f"\n---\n{_CONTRACT_MARKER}\n\n```yaml\n{contract_yaml}```\n"

    if _CONTRACT_MARKER in description:
        idx = description.rfind(_CONTRACT_MARKER)
        delimiter_match = re.search(r"\n---\n\s*$", description[:idx])
        if delimiter_match:
            return description[: delimiter_match.start()] + contract_block
        return description[:idx] + contract_block

    return description.rstrip() + contract_block


def _tickets_dir() -> Path:
    """Resolve the on-disk tickets directory.

    Honors ``ONEX_STATE_DIR`` when set; otherwise falls back to
    ``~/.onex_state``. Never reads or writes ``~/.claude/``.
    """
    base = os.environ.get("ONEX_STATE_DIR")
    root = Path(base) if base else Path.home() / ".onex_state"
    return root / "tickets"


def persist_workflow_state_locally(
    ticket_id: str, state: ModelTicketWorkflowState
) -> None:
    """Persist a workflow state to ``$ONEX_STATE_DIR/tickets/<ticket_id>/contract.yaml``.

    Writes atomically via a ``.tmp`` sibling followed by ``os.replace``.
    """
    target_dir = _tickets_dir() / ticket_id
    target_dir.mkdir(parents=True, exist_ok=True)

    contract_path = target_dir / "contract.yaml"
    tmp_path = contract_path.with_suffix(".yaml.tmp")
    tmp_path.write_text(workflow_state_to_yaml(state))
    tmp_path.replace(contract_path)


__all__ = [
    "extract_workflow_state",
    "persist_workflow_state_locally",
    "update_description_with_workflow_state",
    "workflow_state_to_yaml",
]
