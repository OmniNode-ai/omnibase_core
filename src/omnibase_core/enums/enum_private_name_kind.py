# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""The kinds of private name a deployment's overlays hold."""

from __future__ import annotations

from enum import StrEnum


class EnumPrivateNameKind(StrEnum):
    """What a private name names; the check reports the kind, never the value."""

    REPOSITORY = "repository"
    HOST = "host"
    ORGANIZATION = "organization"
    LEDGER_PATH = "ledger_path"
    ENDPOINT = "endpoint"
