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

from omnibase_core.topics import TopicBase

DELEGATION_COMMAND_TOPIC = TopicBase.HARNESS_DELEGATION_COMMAND
DELEGATION_INFER_TOPIC = TopicBase.HARNESS_DELEGATION_INFER
DELEGATION_COMPLETED_TOPIC = TopicBase.HARNESS_DELEGATION_COMPLETED

SEA_COMMAND_TOPIC = TopicBase.HARNESS_SEA_COMMAND
SEA_INFER_TOPIC = TopicBase.HARNESS_SEA_INFER
SEA_COMPLETED_TOPIC = TopicBase.HARNESS_SEA_COMPLETED


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
