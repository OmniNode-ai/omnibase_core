# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed boundary for dynamic demo YAML documents."""

from pydantic import RootModel

from omnibase_core.types.type_json import StrictJsonType


class ModelDemoYamlDocument(RootModel[dict[str, StrictJsonType]]):
    """A demo YAML document with a mapping root and strict JSON-compatible values."""


__all__ = ["ModelDemoYamlDocument"]
