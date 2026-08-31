# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Execution-locus-kind enum (OMN-17308).

*Where* a process ran, at the granularity that decides whether its output is a
statement about an operator's laptop or about a deployed lane. The OMN-17295
invalid probe turned entirely on this distinction: ``--bus kafka`` selects the
transport, it does not relocate execution, so an orchestrator resolved out of
``omnibase_infra/.venv`` produced a receipt that read as a lane result.
"""

from enum import StrEnum, unique


@unique
class EnumExecutionLocusKind(StrEnum):
    """The kind of place a stamped process was executing in."""

    VENV = "venv"
    """A Python virtual environment on a host. The locus value is the venv
    prefix — the surface that distinguishes the CLI venv from the daemon venv
    from a worktree venv (OMN-17190)."""

    CONTAINER = "container"
    """A container. The locus value is the container id, which binds the
    receipt to a specific running image rather than to an image tag."""

    SYSTEM = "system"
    """A system interpreter with no virtual environment and no container — the
    OMN-17284 shape, where stale builds sit in brew site-packages and their
    console scripts are on PATH."""


__all__: list[str] = ["EnumExecutionLocusKind"]
