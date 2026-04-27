# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for the Receipt-Gate CLI."""

from __future__ import annotations

import pytest

from omnibase_core.validation.receipt_gate_cli import _escape_github_actions_message

pytestmark = pytest.mark.unit


def test_escape_github_actions_message_payload() -> None:
    """Workflow command payloads must escape percent and line separators."""
    message = "PASS: OMN-1/dod-001/command (/tmp/r.yaml): 50%\r\nnext"

    assert (
        _escape_github_actions_message(message)
        == "PASS: OMN-1/dod-001/command (/tmp/r.yaml): 50%25%0D%0Anext"
    )
