# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Structured conditions, never executable expressions."""

from pydantic import BaseModel, ConfigDict


class ModelErrorRuleConditions(BaseModel):
    """An empty dimension matches all values in that dimension."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    host_roles: tuple[str, ...] = ()
    repositories: tuple[str, ...] = ()
    ticket_states: tuple[str, ...] = ()
