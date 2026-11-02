# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed ports for the boundary import effect's existing collaborators."""

from __future__ import annotations

from typing import Protocol, TypeVar, runtime_checkable

RequestT_contra = TypeVar("RequestT_contra", contravariant=True)
ResultT_co = TypeVar("ResultT_co", covariant=True)


@runtime_checkable
class ValidationReportWriteInterface(Protocol[RequestT_contra, ResultT_co]):
    """Persist a canonical validation report."""

    def handle(self, request: RequestT_contra) -> ResultT_co:
        """Return report persistence evidence."""
        ...
