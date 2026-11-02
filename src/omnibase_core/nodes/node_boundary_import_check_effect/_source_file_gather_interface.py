# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed ports for the boundary import effect's existing collaborators."""

from __future__ import annotations

from typing import Protocol, TypeVar, runtime_checkable

RequestT_contra = TypeVar("RequestT_contra", contravariant=True)
ResultT_co = TypeVar("ResultT_co", covariant=True)


@runtime_checkable
class SourceFileGatherInterface(Protocol[RequestT_contra, ResultT_co]):
    """Read eligible source files and retain skipped-file diagnostics."""

    def handle(self, request: RequestT_contra) -> ResultT_co:
        """Return source content and read errors."""
        ...
