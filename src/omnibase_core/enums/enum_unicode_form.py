"""
Unicode normalization forms for contract-driven NodeCompute.

This module defines the unicode normalization forms available for NORMALIZE_UNICODE transformations.
"""

from enum import Enum


class EnumUnicodeForm(str, Enum):
    """
    Unicode normalization forms.

    Attributes:
        NFC: Canonical Decomposition, followed by Canonical Composition.
        NFD: Canonical Decomposition.
        NFKC: Compatibility Decomposition, followed by Canonical Composition.
        NFKD: Compatibility Decomposition.
    """

    NFC = "NFC"
    NFD = "NFD"
    NFKC = "NFKC"
    NFKD = "NFKD"
