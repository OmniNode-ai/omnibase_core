# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Centralized ModelValidationConfig implementation."""

from pydantic import BaseModel


class ModelValidationConfig(BaseModel):
    """Generic validationconfig model for common use."""
