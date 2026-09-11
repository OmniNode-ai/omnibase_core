# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed boundary for FSM handler-binding contract documents."""

from pydantic import RootModel

from omnibase_core.types.type_json import StrictJsonType


class ModelFsmContractDocument(RootModel[dict[str, StrictJsonType]]):
    """An FSM contract document with a mapping root and strict JSON-compatible values."""


__all__ = ["ModelFsmContractDocument"]
