# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Canonical-shaped topic constants for the local runtime harness (OMN-13420).

Topic names mirror the ``onex.cmd.*`` / ``onex.evt.*`` routing keys node authors
see in the broker-backed lane (per
``docs/evidence/2026-06-15-runtime-integration/publish_runtime_probe.py``) so the
in-process harness exercises the same routing-key shape. These are fixed wire
identifiers, not environment-tunable settings.
"""

from __future__ import annotations

# env-var-ok: fixed canonical topic identifiers, not environment-tunable settings
DELEGATION_COMMAND_TOPIC = "onex.cmd.omnibase-core.harness-delegation-request.v1"
# env-var-ok: fixed canonical topic identifier
DELEGATION_INFER_TOPIC = "onex.evt.omnibase-core.harness-delegation-infer.v1"
# env-var-ok: fixed canonical topic identifier
DELEGATION_COMPLETED_TOPIC = "onex.evt.omnibase-core.harness-delegation-completed.v1"

# env-var-ok: fixed canonical topic identifier
SEA_COMMAND_TOPIC = "onex.cmd.omnibase-core.harness-sea-request.v1"
# env-var-ok: fixed canonical topic identifier
SEA_INFER_TOPIC = "onex.evt.omnibase-core.harness-sea-infer.v1"
# env-var-ok: fixed canonical topic identifier
SEA_COMPLETED_TOPIC = "onex.evt.omnibase-core.harness-sea-completed.v1"


def infer_topic(workflow: str) -> str:
    """Return the inference-request topic for a workflow."""
    return DELEGATION_INFER_TOPIC if workflow == "delegation" else SEA_INFER_TOPIC


def completed_topic(workflow: str) -> str:
    """Return the terminal completed topic for a workflow."""
    return (
        DELEGATION_COMPLETED_TOPIC if workflow == "delegation" else SEA_COMPLETED_TOPIC
    )


def command_topic(workflow: str) -> str:
    """Return the command topic for a workflow."""
    return DELEGATION_COMMAND_TOPIC if workflow == "delegation" else SEA_COMMAND_TOPIC


__all__ = [
    "DELEGATION_COMMAND_TOPIC",
    "DELEGATION_COMPLETED_TOPIC",
    "DELEGATION_INFER_TOPIC",
    "SEA_COMMAND_TOPIC",
    "SEA_COMPLETED_TOPIC",
    "SEA_INFER_TOPIC",
    "command_topic",
    "completed_topic",
    "infer_topic",
]
