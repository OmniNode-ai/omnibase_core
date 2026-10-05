# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Literal selector configuration gathered without executing repository code."""

from pydantic import BaseModel, ConfigDict


class ModelTestRootCollectionSelector(BaseModel):
    """Facts consumed by the infra collocated-selector parity check."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    mapped_roots: tuple[str, ...] = ()
    tests_prefix: str = "tests/"
    error: str | None = None
