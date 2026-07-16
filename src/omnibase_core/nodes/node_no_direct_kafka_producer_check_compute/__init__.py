# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""no_direct_kafka_producer_check COMPUTE node package (OMN-14659).

Exposes :class:`NodeNoDirectKafkaProducerCheckCompute` — AST-scans explicit
(path, source) pairs for direct Kafka producer client usage
(``AIOKafkaProducer``, ``KafkaProducer``, ``confluent_kafka``, ``aiokafka``)
outside the shared publisher layer, and returns a ``ModelValidationReport``.
"""

from omnibase_core.nodes.node_no_direct_kafka_producer_check_compute.handler import (
    NodeNoDirectKafkaProducerCheckCompute,
)

__all__ = ["NodeNoDirectKafkaProducerCheckCompute"]
