# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Canary (OMN-21433) targeting pydantic-extra-forbid. Do not merge."""

from pydantic import BaseModel


class ModelCanaryOpen(BaseModel):
    """Model that accepts unknown fields."""

    name: str
