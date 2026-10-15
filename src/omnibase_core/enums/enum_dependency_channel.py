# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The channel through which one repository depends on another (OMN-19998)."""

from __future__ import annotations

from enum import StrEnum, unique

__all__ = ["EnumDependencyChannel"]


@unique
class EnumDependencyChannel(StrEnum):
    """How a cross-repository dependency is expressed in a repository's tree.

    The values are written into each repository's dependency-direction
    baseline file, so they are a stable external surface.
    """

    PYTHON_IMPORT = "python_import"
    """An ``import`` or ``from ... import`` of another repository's package."""

    PYPROJECT = "pyproject"
    """A requirement, extra, dependency group or uv source in pyproject.toml."""

    REQUIREMENTS = "requirements"
    """A line in a requirements or constraints file."""

    DOCKERFILE = "dockerfile"
    """A Dockerfile instruction that installs, clones or fetches another repository."""

    WORKFLOW = "workflow"
    """A GitHub workflow or action that checks out, pins or uses another repository."""

    SCRIPT = "script"
    """A script or Makefile line that installs, clones or fetches another repository."""
