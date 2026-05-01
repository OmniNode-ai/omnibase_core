# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

import pytest

from omnibase_core.validation.receipt_gate import EVIDENCE_HANDLERS


@pytest.mark.unit
def test_completion_verify_handler_registered() -> None:
    assert "completion-verify" in EVIDENCE_HANDLERS


@pytest.mark.unit
def test_completion_verify_handler_is_callable() -> None:
    handler = EVIDENCE_HANDLERS["completion-verify"]
    assert callable(handler)


@pytest.mark.unit
def test_completion_verify_handler_exactly_one_registration() -> None:
    # dict keyed by string — idempotent by construction; just assert key exists once
    keys = list(EVIDENCE_HANDLERS.keys())
    assert keys.count("completion-verify") == 1
