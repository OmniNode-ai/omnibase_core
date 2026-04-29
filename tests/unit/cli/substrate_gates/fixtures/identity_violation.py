# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Fixture: file containing identity-field optionality violations.

Used by test_identity_field_optionality.py to verify the gate fires.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel


class ModelWithViolation(BaseModel):
    correlation_id: UUID | None = None
    session_id: str | None = None
    request_id: UUID | None = None


def handler_with_violation(trace_id: str | None = None) -> None:
    pass


async def async_handler_with_violation(span_id: UUID | None = None) -> None:
    pass
