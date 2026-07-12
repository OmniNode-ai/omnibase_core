# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelDuplicateIdCheckSpec — one manifest entry declaring a single
config/registry file to check for duplicate ids (OMN-14401)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ModelDuplicateIdCheckSpec(BaseModel):
    """One manifest entry: a single registry file to check for duplicate ids."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    path: str
    list_path: str
    id_field: str
    disambiguator_field: str | None = None
