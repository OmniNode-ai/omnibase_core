#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Model Configuration for ONEX Security Context.

Strongly-typed configuration class for ONEX security context with frozen setting
and custom JSON encoders for UUID and datetime serialization.
"""


class ModelConfig:
    """Pydantic configuration for ONEX security context."""

    frozen = True
    use_enum_values = True
