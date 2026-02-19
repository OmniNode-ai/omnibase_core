# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Service protocols for ONEX infrastructure.

This module provides protocol definitions for various services
used by ONEX components, including secret management.
"""

from omnibase_core.protocols.services.protocol_secret_service import (
    ProtocolSecretService,
)

__all__ = [
    "ProtocolSecretService",
]
