# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Integration Surface Enum.

Operational probe categories for the /integration-sweep endpoint.
Distinct from EnumInterfaceSurface (which classifies interface change type).
"""

from enum import Enum, unique


@unique
class EnumIntegrationSurface(str, Enum):
    """Operational probe categories for integration sweep investigations.

    Classifies which operational surface a probe targets during the
    /integration-sweep workflow:
    - KAFKA: Kafka/Redpanda topic and consumer group probes
    - DB: Database schema and migration probes
    - CI: Continuous integration workflow probes
    - PLUGIN: omniclaude plugin and hook probes
    - GITHUB_CI: GitHub Actions workflow and runner probes
    - SCRIPT: Shell script and automation probes
    - CONTAINER_HEALTH: Docker container state probes (unconditional)
    - RUNTIME_HEALTH: Runtime service HTTP health endpoint probes (unconditional)
    - CROSS_REPO_BOUNDARY: Cross-repo schema round-trip and topic constant matching
    - PLAYWRIGHT_BEHAVIORAL: Playwright end-to-end data-flow and UI behavioral probes
    - SCHEMA_PARITY: Static schema-to-migration governance (ORM vs DDL agreement)
    """

    KAFKA = "kafka"
    """Kafka/Redpanda topic and consumer group probes."""

    DB = "db"
    """Database schema and migration probes."""

    CI = "ci"
    """Continuous integration workflow probes."""

    PLUGIN = "plugin"
    """omniclaude plugin and hook probes."""

    GITHUB_CI = "github_ci"
    """GitHub Actions workflow and runner probes."""

    SCRIPT = "script"
    """Shell script and automation probes."""

    CONTAINER_HEALTH = "container_health"
    """Docker container state probes — expected containers running and healthy."""

    RUNTIME_HEALTH = "runtime_health"
    """Runtime service HTTP health endpoint probes."""

    CROSS_REPO_BOUNDARY = "cross_repo_boundary"
    """Cross-repo Kafka schema round-trip and topic constant matching probes."""

    PLAYWRIGHT_BEHAVIORAL = "playwright_behavioral"
    """Playwright end-to-end data-flow and UI behavioral verification probes."""

    WIRING_VERIFICATION = "wiring_verification"
    """Structural topology probe for declared emitter/consumer/writer completeness."""

    SCHEMA_PARITY = "schema_parity"
    """Static schema-to-migration governance — validates ORM declarations match DDL."""

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value
