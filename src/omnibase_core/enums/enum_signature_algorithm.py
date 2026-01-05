# SPDX-FileCopyrightText: 2025 OmniNode Team
# SPDX-License-Identifier: Apache-2.0
"""
Signature Algorithm Enumeration.

Defines supported cryptographic signature algorithms for JWT signing and
artifact signature verification.

Thread Safety:
    Enum values are immutable and thread-safe.
"""

from enum import Enum


class EnumSignatureAlgorithm(str, Enum):
    """
    Supported cryptographic signature algorithms.

    Includes both JWT signing algorithms (RS*, PS*, ES*) and
    raw signature algorithms (ED25519) for artifact verification.

    For handler packaging signatures (v1), ED25519 is the recommended algorithm
    due to its compact signatures, fast verification, and modern security.
    """

    # RSA algorithms (JWT)
    RS256 = "RS256"  # RSA with SHA-256
    RS384 = "RS384"  # RSA with SHA-384
    RS512 = "RS512"  # RSA with SHA-512

    # RSA-PSS algorithms (JWT)
    PS256 = "PS256"  # RSA-PSS with SHA-256
    PS384 = "PS384"  # RSA-PSS with SHA-384
    PS512 = "PS512"  # RSA-PSS with SHA-512

    # ECDSA algorithms (JWT)
    ES256 = "ES256"  # ECDSA with SHA-256
    ES384 = "ES384"  # ECDSA with SHA-384
    ES512 = "ES512"  # ECDSA with SHA-512

    # EdDSA algorithms (raw signatures, artifact verification)
    ED25519 = "ed25519"  # Edwards-curve Digital Signature Algorithm
