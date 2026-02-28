# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Shared private helpers for the intelligence models module.

Utility functions shared across multiple intelligence model files to avoid
duplication.
"""

from omnibase_core.models.primitives import ModelSemVer


def _default_schema_version() -> ModelSemVer:
    """Create default schema version 1.0.0."""
    return ModelSemVer(major=1, minor=0, patch=0)
