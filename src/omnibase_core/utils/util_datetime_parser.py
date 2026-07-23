# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Deprecated re-export shim for parse_datetime (OMN-14959).

The canonical definition moved to
``omnibase_core.types.converter_datetime_parser`` — its only real consumers
were the ``types/converter_*.py`` TypedDict converters, so the function now
lives in the ``types`` foundation package instead of creating a
``types -> utils`` import-linter edge. This module is a pure re-export shim
retained for the ``omnibase_core.utils`` public surface (lazy-loaded via
``utils.__getattr__``) and any external importers; ``utils -> types`` is
downward-legal and uncontracted.
"""

from __future__ import annotations

from omnibase_core.types.converter_datetime_parser import parse_datetime

__all__ = ["parse_datetime"]
