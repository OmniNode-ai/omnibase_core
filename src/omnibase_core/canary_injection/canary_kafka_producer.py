# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Canary (OMN-21433) targeting direct-kafka-producer. Do not merge."""

from aiokafka import AIOKafkaProducer


def canary_producer() -> AIOKafkaProducer:
    """Build a producer directly."""
    return AIOKafkaProducer(bootstrap_servers="broker:9092")
