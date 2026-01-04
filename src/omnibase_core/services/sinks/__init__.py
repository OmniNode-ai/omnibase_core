# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""
Event sink implementations for contract validation.

This package provides sink implementations for routing contract validation
events to different destinations (memory, file, kafka).

.. versionadded:: 0.4.0
"""

from omnibase_core.services.sinks.sink_file import SinkFile
from omnibase_core.services.sinks.sink_memory import SinkMemory

__all__ = [
    "SinkFile",
    "SinkMemory",
]
