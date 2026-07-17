# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Concrete transports for the unified runtime dispatch loop.

Net-new foundation (epic OMN-14717). Exposes the in-memory transport that models
Kafka's per-partition offset semantics. The parametrized conformance suite lives in
:mod:`omnibase_core.runtime.transport.runtime_transport_conformance` and is imported
directly by tests (never from this ``__init__``) so the production import graph stays
free of any test-framework dependency.
"""

from omnibase_core.runtime.transport.runtime_in_memory_broker import InMemoryBroker
from omnibase_core.runtime.transport.runtime_in_memory_transport import (
    InMemoryTransport,
)

__all__ = ["InMemoryBroker", "InMemoryTransport"]
