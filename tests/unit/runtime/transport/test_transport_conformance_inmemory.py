# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Run the shared transport conformance suite against ``InMemoryTransport``.

This is the in-memory side of the substitutability oracle (ticket OMN-14720, epic
OMN-14717). The identical suite is subclassed with a Kafka-backed environment in
omnibase_infra (S3), which is what licenses "in-memory golden chain ⇒ Kafka golden
chain". The base suite lives in
``omnibase_core.runtime.transport.runtime_transport_conformance`` and is deliberately
importable (pytest-free, protocols-hub-free) so infra can subclass it.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

import pytest

from omnibase_core.runtime.transport.runtime_in_memory_broker import InMemoryBroker
from omnibase_core.runtime.transport.runtime_in_memory_transport import (
    InMemoryTransport,
)
from omnibase_core.runtime.transport.runtime_transport_conformance import (
    TransportConformanceSuite,
)


class TestInMemoryTransportConformance(TransportConformanceSuite):
    """Parametrize the shared conformance suite over the in-memory transport."""

    # pytest.ini runs asyncio in STRICT mode, so every async test needs the marker.
    # Setting it at class level applies it to the inherited async test methods, which
    # keeps the shared suite itself free of any pytest import.
    pytestmark = pytest.mark.asyncio

    @pytest.fixture
    def _broker(self) -> InMemoryBroker:
        # >=2 partitions so the shared suite's multi-partition nack test
        # (test_nack_on_one_partition_does_not_strand_sibling_partitions, OMN-14757)
        # has real siblings to strand. Same-key tests still land on one partition, so
        # the existing single-partition assertions are unaffected.
        return InMemoryBroker(num_partitions=2)

    @pytest.fixture
    def transport_producer(self, _broker: InMemoryBroker) -> InMemoryTransport:
        return InMemoryTransport(broker=_broker, group="conformance-producer")

    @pytest.fixture
    def transport_consumer_factory(
        self, _broker: InMemoryBroker
    ) -> Callable[..., InMemoryTransport]:
        def factory(*, group: str, topics: Sequence[str]) -> InMemoryTransport:
            return InMemoryTransport(broker=_broker, group=group, topics=topics)

        return factory
