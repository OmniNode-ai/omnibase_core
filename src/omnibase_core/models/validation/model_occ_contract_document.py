# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed boundary for append-only OCC contract documents."""

from pydantic import RootModel

from omnibase_core.types.type_json import StrictJsonType


class ModelOccContractDocument(RootModel[dict[str, StrictJsonType]]):
    """An OCC contract document with a mapping root and strict JSON-compatible values."""


__all__ = ["ModelOccContractDocument"]
