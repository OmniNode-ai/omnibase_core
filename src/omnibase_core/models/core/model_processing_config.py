# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Centralized ModelProcessingConfig implementation."""

from pydantic import BaseModel


class ModelProcessingConfig(BaseModel):
    """Generic processingconfig model for common use."""
