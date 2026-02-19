#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Model Configuration for ONEX Reply.

Strongly-typed configuration class for ONEX reply with frozen setting
and custom JSON encoders for UUID and datetime serialization.
"""


class ModelConfig:
    """Pydantic configuration for ONEX reply."""

    frozen = True
    use_enum_values = True
