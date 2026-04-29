# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Fixture: file with no identity-field optionality violations.

Used by test_identity_field_optionality.py to verify the gate stays silent.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel


class ModelClean(BaseModel):
    correlation_id: UUID
    session_id: str
    request_id: UUID
    # parent_span_id is legitimately optional for root spans — NOT in the banned list
    parent_span_id: UUID | None = None


def handler_clean(trace_id: UUID) -> None:
    pass


async def async_handler_clean(span_id: UUID) -> None:
    pass


def handler_with_allow(
    tenant_id: UUID | None = None,  # substrate-allow: multi-tenant bootstrap sentinel
) -> None:
    pass
