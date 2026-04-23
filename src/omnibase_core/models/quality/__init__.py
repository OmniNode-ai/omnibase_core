# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Models for code-quality findings (mypy, ruff) and type-debt reports."""

from .model_mypy_finding import ModelMypyFinding
from .model_ruff_finding import ModelRuffFinding

__all__ = [
    "ModelMypyFinding",
    "ModelRuffFinding",
]
