# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Kinds of public surface another repository can depend on (OMN-26194)."""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper


@unique
class EnumPublicSurfaceKind(UtilStrValueHelper, str, Enum):
    """One kind of public surface; each kind has exactly one extraction rule."""

    PYTHON_SYMBOL = "python_symbol"
    PYTHON_MODULE = "python_module"
    NODE = "node"
    CONTRACT_FIELD = "contract_field"
    TOPIC = "topic"
    OVERLAY_KEY = "overlay_key"
    ENDPOINT = "endpoint"
    CLI_VERB = "cli_verb"
