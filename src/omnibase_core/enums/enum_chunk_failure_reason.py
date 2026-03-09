# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Enumeration of chunk series failure reasons."""

from enum import Enum


class EnumChunkFailureReason(str, Enum):
    """Reason a chunk series was abandoned."""

    TIMEOUT = "timeout"
    CHECKSUM_MISMATCH = "checksum_mismatch"
    DUPLICATE_CHUNK = "duplicate_chunk"
    CORRUPT_CHUNK = "corrupt_chunk"
    PARTIAL_PROCESSING_PREVENTED = "partial_processing_prevented"
