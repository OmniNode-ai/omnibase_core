"""Signature algorithm enumeration for JWT signing and artifact verification."""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumSignatureAlgorithm(StrValueHelper, str, Enum):
    """Supported cryptographic signature algorithms.

    RSA: RS256, RS384, RS512. RSA-PSS: PS256, PS384, PS512. ECDSA: ES256, ES384, ES512.
    EdDSA: ED25519 (recommended for handler packaging).
    """

    # RSA Algorithms (JWT - RFC 7518)
    RS256 = "RS256"
    """RSA PKCS#1 v1.5 with SHA-256. Widely supported for JWT."""
    RS384 = "RS384"
    """RSA PKCS#1 v1.5 with SHA-384."""
    RS512 = "RS512"
    """RSA PKCS#1 v1.5 with SHA-512."""

    # RSA-PSS Algorithms (JWT - RFC 7518)
    PS256 = "PS256"
    """RSA-PSS with SHA-256. More secure padding than RS256."""
    PS384 = "PS384"
    """RSA-PSS with SHA-384."""
    PS512 = "PS512"
    """RSA-PSS with SHA-512."""

    # ECDSA Algorithms (JWT - RFC 7518)
    ES256 = "ES256"
    """ECDSA with P-256 curve and SHA-256."""
    ES384 = "ES384"
    """ECDSA with P-384 curve and SHA-384."""
    ES512 = "ES512"
    """ECDSA with P-521 curve and SHA-512."""

    # EdDSA Algorithms (Artifact Verification)
    ED25519 = "ed25519"
    """EdDSA with Curve25519. Recommended for handler packaging (v1 supported)."""


__all__ = ["EnumSignatureAlgorithm"]
