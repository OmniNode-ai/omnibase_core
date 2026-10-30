# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Container-resolved interface of the report publisher's collaborator."""

from __future__ import annotations

from typing import Protocol, TypeVar, runtime_checkable

__all__ = ["ValidatorRunEventsInterface"]

TRequest_contra = TypeVar("TRequest_contra", contravariant=True)
TResponse_co = TypeVar("TResponse_co", covariant=True)


@runtime_checkable
class ValidatorRunEventsInterface(Protocol[TRequest_contra, TResponse_co]):
    """The report publisher's ValidatorRunEvents dependency."""

    def handle(self, request: TRequest_contra) -> TResponse_co:
        """Handle the canonical request."""
        ...
