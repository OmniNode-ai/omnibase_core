# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Demo handlers for ONEX framework examples.

Available handlers:

- support_assistant: AI support assistant demo for model evaluation (OMN-1201)

Note:
    This module uses lazy imports to avoid import-time side effects.
    Submodules are imported on first access via __getattr__.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from examples.demo.handlers import support_assistant as support_assistant

__all__ = ["support_assistant"]


def __getattr__(name: str) -> object:
    """Lazy import submodules on first access."""
    if name == "support_assistant":
        from examples.demo.handlers import support_assistant

        return support_assistant
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
