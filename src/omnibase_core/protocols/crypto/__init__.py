# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Cryptographic protocol definitions for key management.

This module provides the ProtocolKeyProvider interface for runtime
public key lookup during envelope signature verification.
"""

from omnibase_core.protocols.crypto.protocol_key_provider import ProtocolKeyProvider
from omnibase_core.protocols.crypto.protocol_multi_key_provider import (
    ProtocolMultiKeyProvider,
)

__all__ = ["ProtocolKeyProvider", "ProtocolMultiKeyProvider"]
