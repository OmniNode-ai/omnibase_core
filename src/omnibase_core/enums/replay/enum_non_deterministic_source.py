"""
EnumNonDeterministicSource - Non-deterministic source classification enum.

This module provides the EnumNonDeterministicSource enum that identifies
the source of non-determinism in effects for replay safety enforcement.

Design:
    Seven categories capture common non-determinism sources:
    - TIME: Time-based operations (datetime.now(), time.time())
    - RANDOM: Random number generation (random.random(), secrets)
    - UUID: UUID generation (uuid.uuid4())
    - NETWORK: Network operations (HTTP calls, sockets)
    - DATABASE: Database operations (queries with external state)
    - FILESYSTEM: File I/O with external state
    - ENVIRONMENT: Environment variables and system state

Usage:
    .. code-block:: python

        from omnibase_core.enums.replay import EnumNonDeterministicSource

        # Identify time-based non-determinism
        source = EnumNonDeterministicSource.TIME

        # Identify network-based non-determinism
        source = EnumNonDeterministicSource.NETWORK

        # Identify random number generator usage
        source = EnumNonDeterministicSource.RANDOM

Related:
    - OMN-1150: Replay Safety Enforcement
    - EnumEffectDeterminism: Classification of effect determinism
    - EnumEnforcementMode: How to handle non-deterministic effects
    - ModelEnforcementDecision: Decision outcome model

.. versionadded:: 0.6.3
"""

from __future__ import annotations

__all__ = ["EnumNonDeterministicSource"]

from enum import Enum


class EnumNonDeterministicSource(str, Enum):
    """
    Source of non-determinism in effects.

    Identifies the category of non-determinism for appropriate mitigation
    strategies during replay safety enforcement.

    Values:
        TIME: Time-based operations such as datetime.now(), time.time(),
            or any operation that depends on current time.
        RANDOM: Random number generation including random.random(),
            secrets module, or cryptographic random sources.
        UUID: UUID generation, particularly uuid.uuid4() which uses
            random data for uniqueness.
        NETWORK: Network operations including HTTP requests, socket
            connections, or any external service calls.
        DATABASE: Database operations that depend on external state,
            including queries, transactions, or connection pooling.
        FILESYSTEM: File I/O operations that interact with external
            state, such as reading files that may change between runs.
        ENVIRONMENT: Environment variables, system properties, or
            other runtime environment state that may vary.

    Example:
        >>> from omnibase_core.enums.replay import EnumNonDeterministicSource
        >>> source = EnumNonDeterministicSource.NETWORK
        >>> source.value
        'network'
        >>> source == EnumNonDeterministicSource.TIME
        False

    .. versionadded:: 0.6.3
    """

    TIME = "time"
    RANDOM = "random"
    UUID = "uuid"
    NETWORK = "network"
    DATABASE = "database"
    FILESYSTEM = "filesystem"
    ENVIRONMENT = "environment"
