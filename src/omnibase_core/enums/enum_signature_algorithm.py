# SPDX-FileCopyrightText: 2025 OmniNode Team
# SPDX-License-Identifier: Apache-2.0
"""
Signature Algorithm Enumeration.

Defines supported cryptographic signature algorithms for JWT signing and
artifact signature verification.

Algorithm Categories:
    - **RSA (RS*)**: Traditional RSA signatures with SHA-2 hash functions.
      Widely supported but requires larger key sizes (2048+ bits) for security.

    - **RSA-PSS (PS*)**: Probabilistic Signature Scheme variant of RSA.
      More secure than PKCS#1 v1.5 padding used in RS* algorithms.

    - **ECDSA (ES*)**: Elliptic Curve Digital Signature Algorithm.
      Smaller keys than RSA with equivalent security. Uses NIST curves.

    - **EdDSA (ED25519)**: Edwards-curve Digital Signature Algorithm.
      Modern, fast, and secure. Uses Curve25519. Recommended for new systems.

Handler Packaging (v1):
    For handler packaging signatures, only ED25519 is supported in v1.
    This choice provides:
    - Compact signatures (64 bytes)
    - Fast verification
    - Deterministic signatures (no random nonce)
    - Strong security guarantees

Thread Safety:
    Enum values are immutable and thread-safe.

See Also:
    - EnumHashAlgorithm: Supported hash algorithms for integrity verification
    - ModelHandlerPackaging: Uses signature algorithms for artifact verification
"""

from enum import Enum


class EnumSignatureAlgorithm(str, Enum):
    """
    Supported cryptographic signature algorithms.

    This enum defines algorithms for two main use cases:

    1. **JWT Signing (RS*, PS*, ES*)**: Used for token-based authentication
       and authorization. These algorithms sign JSON Web Tokens per RFC 7518.

    2. **Artifact Verification (ED25519)**: Used for verifying the authenticity
       of handler packages and other artifacts in the ONEX ecosystem.

    Algorithm Selection Guide:
        - **New systems**: Use ED25519 for its security, speed, and simplicity.
        - **JWT compatibility**: Use RS256 or ES256 for broad library support.
        - **High security JWT**: Use PS256 (RSA-PSS) or ES384/ES512.
        - **Legacy systems**: RS256 for maximum compatibility.

    Handler Packaging v1:
        Only ED25519 is supported for handler packaging signatures. Future
        versions may expand support to include ES256 for ECDSA-based workflows.

    Example:
        >>> from omnibase_core.enums.enum_signature_algorithm import (
        ...     EnumSignatureAlgorithm,
        ... )
        >>> algo = EnumSignatureAlgorithm.ED25519
        >>> algo.value
        'ed25519'
        >>> algo == EnumSignatureAlgorithm.ED25519
        True

    Attributes:
        RS256: RSA PKCS#1 v1.5 signature with SHA-256 hash. Key size: 2048+ bits.
        RS384: RSA PKCS#1 v1.5 signature with SHA-384 hash. Key size: 2048+ bits.
        RS512: RSA PKCS#1 v1.5 signature with SHA-512 hash. Key size: 2048+ bits.
        PS256: RSA-PSS signature with SHA-256 hash. More secure padding than RS*.
        PS384: RSA-PSS signature with SHA-384 hash. More secure padding than RS*.
        PS512: RSA-PSS signature with SHA-512 hash. More secure padding than RS*.
        ES256: ECDSA with P-256 curve and SHA-256 hash. 256-bit key size.
        ES384: ECDSA with P-384 curve and SHA-384 hash. 384-bit key size.
        ES512: ECDSA with P-521 curve and SHA-512 hash. 521-bit key size.
        ED25519: EdDSA with Curve25519. 256-bit key, 64-byte signatures.
            Recommended for handler packaging (v1 supported algorithm).
    """

    # =========================================================================
    # RSA Algorithms (JWT - RFC 7518)
    # =========================================================================

    RS256 = "RS256"
    """RSA PKCS#1 v1.5 signature with SHA-256 hash.

    Standard RSA signature algorithm using PKCS#1 v1.5 padding.
    Widely supported across JWT libraries. Requires 2048+ bit keys.

    Use Case: JWT signing for maximum compatibility.
    Security: Good, but PS256 recommended for new systems.
    """

    RS384 = "RS384"
    """RSA PKCS#1 v1.5 signature with SHA-384 hash.

    Higher security variant of RS256 with SHA-384 hash function.
    Requires 2048+ bit keys for adequate security.

    Use Case: JWT signing when SHA-256 is insufficient.
    Security: Good, but PS384 recommended for new systems.
    """

    RS512 = "RS512"
    """RSA PKCS#1 v1.5 signature with SHA-512 hash.

    Highest security RSA variant with SHA-512 hash function.
    Requires 2048+ bit keys for adequate security.

    Use Case: High-security JWT signing with RSA.
    Security: Good, but PS512 recommended for new systems.
    """

    # =========================================================================
    # RSA-PSS Algorithms (JWT - RFC 7518)
    # =========================================================================

    PS256 = "PS256"
    """RSA-PSS signature with SHA-256 hash and MGF1.

    Probabilistic Signature Scheme with more secure padding than RS256.
    Provides provable security in the random oracle model.

    Use Case: Secure JWT signing when RSA is required.
    Security: Recommended over RS256 for new systems.
    """

    PS384 = "PS384"
    """RSA-PSS signature with SHA-384 hash and MGF1.

    Higher security variant of PS256 with SHA-384 hash function.

    Use Case: High-security JWT signing with RSA-PSS.
    Security: Excellent.
    """

    PS512 = "PS512"
    """RSA-PSS signature with SHA-512 hash and MGF1.

    Highest security RSA-PSS variant with SHA-512 hash function.

    Use Case: Maximum security JWT signing with RSA.
    Security: Excellent.
    """

    # =========================================================================
    # ECDSA Algorithms (JWT - RFC 7518)
    # =========================================================================

    ES256 = "ES256"
    """ECDSA signature with P-256 curve and SHA-256 hash.

    Elliptic Curve Digital Signature Algorithm using NIST P-256 curve.
    Smaller keys (256-bit) than RSA with equivalent security to RSA-3072.

    Use Case: Efficient JWT signing with strong security.
    Security: Excellent. Widely supported.
    """

    ES384 = "ES384"
    """ECDSA signature with P-384 curve and SHA-384 hash.

    Higher security ECDSA variant using NIST P-384 curve.
    384-bit keys provide security equivalent to RSA-7680.

    Use Case: High-security JWT signing with elliptic curves.
    Security: Excellent.
    """

    ES512 = "ES512"
    """ECDSA signature with P-521 curve and SHA-512 hash.

    Highest security ECDSA variant using NIST P-521 curve.
    521-bit keys provide security equivalent to RSA-15360.

    Use Case: Maximum security JWT signing with elliptic curves.
    Security: Excellent.
    """

    # =========================================================================
    # EdDSA Algorithms (Artifact Verification)
    # =========================================================================

    ED25519 = "ed25519"
    """Edwards-curve Digital Signature Algorithm with Curve25519.

    Modern signature algorithm designed for speed and security.
    Uses twisted Edwards curve (Curve25519) with 256-bit keys.

    Properties:
        - Key size: 256 bits (32 bytes)
        - Signature size: 512 bits (64 bytes)
        - Deterministic: Same message always produces same signature
        - Fast: ~20,000 signatures/sec on modern hardware
        - Secure: Resistant to timing attacks by design

    Use Case: Handler packaging artifact verification (v1 supported).
    Security: Excellent. Recommended for new systems.

    Note:
        This is the ONLY algorithm supported for handler packaging
        signatures in ONEX v1. Future versions may add ES256 support.
    """
