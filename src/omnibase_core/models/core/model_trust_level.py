"""
Trust Level Model

Nuanced trust level model that replaces hardcoded trust enums
with flexible, verifiable trust scores and metadata.
"""

from datetime import UTC, datetime

from pydantic import BaseModel, Field

from .model_verification_method import ModelVerificationMethod


class ModelTrustLevel(BaseModel):
    """
    Nuanced trust level model.

    This model provides a flexible trust scoring system that goes beyond
    simple enum values, supporting verification methods and expiration.
    """

    trust_score: float = Field(default=..., description="Trust score", ge=0.0, le=1.0)

    trust_category: str = Field(
        default=...,
        description="Trust category",
        pattern="^(untrusted|low|medium|high|verified|certified|custom)$",
    )

    display_name: str = Field(
        default=..., description="Human-readable trust level name"
    )

    verification_methods: list[ModelVerificationMethod] = Field(
        default_factory=list,
        description="How trust was established",
    )

    last_verified: datetime | None = Field(
        default=None,
        description="Last verification timestamp",
    )

    expires_at: datetime | None = Field(default=None, description="When trust expires")

    issuer: str | None = Field(default=None, description="Trust issuer")

    revocable: bool = Field(default=True, description="Can trust be revoked")

    requires_renewal: bool = Field(
        default=False,
        description="Whether trust needs periodic renewal",
    )

    renewal_period_days: int | None = Field(
        default=None,
        description="Days between required renewals",
    )

    def _get_current_utc(self) -> datetime:
        """Get current UTC datetime with timezone awareness"""
        return datetime.now(UTC)

    def _ensure_timezone_aware(self, dt: datetime) -> datetime:
        """Ensure datetime is timezone-aware"""
        if dt.tzinfo is None:
            # Assume naive datetimes are UTC
            return dt.replace(tzinfo=UTC)
        return dt

    def is_trusted(self, threshold: float = 0.5) -> bool:
        """Check if trust score meets threshold and trust is not expired."""
        if self.is_expired():
            return False  # Expired trust is never trusted
        return self.trust_score >= threshold

    def is_expired(self) -> bool:
        """Check if trust has expired."""
        if self.expires_at is None:
            return False

        current_time = self._get_current_utc()
        expires_at = self._ensure_timezone_aware(self.expires_at)
        return current_time > expires_at

    def needs_renewal(self) -> bool:
        """Check if trust needs renewal."""
        if not self.requires_renewal or self.last_verified is None:
            return False
        if self.renewal_period_days is None:
            return False

        current_time = self._get_current_utc()
        last_verified = self._ensure_timezone_aware(self.last_verified)
        days_since_verified = (current_time - last_verified).days
        return days_since_verified >= self.renewal_period_days

    def get_highest_verification_level(self) -> str | None:
        """Get the highest level of verification applied."""
        if not self.verification_methods:
            return None

        # Priority order of verification methods
        priority_order = [
            "cryptographic_signature",
            "manual_review",
            "automated_validation",
            "community_verification",
            "self_declared",
        ]

        for method in priority_order:
            if any(v.method_name == method for v in self.verification_methods):
                return method

        return (
            self.verification_methods[0].method_name
            if self.verification_methods
            else None
        )

    @classmethod
    def untrusted(cls) -> "ModelTrustLevel":
        """Create untrusted level."""
        return cls(
            trust_score=0.0,
            trust_category="untrusted",
            display_name="Untrusted",
            revocable=False,
        )

    @classmethod
    def unknown(cls) -> "ModelTrustLevel":
        """Create unknown trust level."""
        return cls(
            trust_score=0.0,
            trust_category="untrusted",
            display_name="Unknown",
            revocable=False,
        )

    @classmethod
    def validated(cls, verifier: str = "system") -> "ModelTrustLevel":
        """Create validated trust level."""
        return cls(
            trust_score=0.6,
            trust_category="verified",
            display_name="Validated",
            verification_methods=[
                ModelVerificationMethod(
                    method_name="automated_validation",
                    verifier=verifier,
                ),
            ],
            last_verified=datetime.now(UTC),
        )

    @classmethod
    def trusted(cls, verifier: str = "admin") -> "ModelTrustLevel":
        """Create trusted level."""
        return cls(
            trust_score=0.8,
            trust_category="high",
            display_name="Trusted",
            verification_methods=[
                ModelVerificationMethod(method_name="manual_review", verifier=verifier),
            ],
            last_verified=datetime.now(UTC),
        )

    @classmethod
    def certified(cls, issuer: str, signature: str) -> "ModelTrustLevel":
        """Create certified trust level."""
        return cls(
            trust_score=1.0,
            trust_category="certified",
            display_name="Certified",
            issuer=issuer,
            verification_methods=[
                ModelVerificationMethod(
                    method_name="cryptographic_signature",
                    verifier=issuer,
                    signature=signature,
                ),
            ],
            last_verified=datetime.now(UTC),
            revocable=True,
            requires_renewal=True,
            renewal_period_days=365,
        )


# Compatibility alias
TrustLevel = ModelTrustLevel
