# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Centralized ModelNodeStatus implementation."""

from pydantic import BaseModel


class ModelNodeStatus(BaseModel):
    """Generic nodestatus model for common use."""
