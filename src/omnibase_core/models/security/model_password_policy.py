"""
Password Policy Model

Typed model for password policy configuration,
replacing Dict[str, Any] with structured fields.
"""

from pydantic import BaseModel, Field


class ModelPasswordPolicy(BaseModel):
    """
    Structured password policy configuration.

    Defines requirements for password strength, complexity,
    and lifecycle management.
    """

    # Length requirements
    min_length: int = Field(
        default=8,
        description="Minimum password length",
        ge=1,
        le=256,
    )

    max_length: int | None = Field(
        default=128,
        description="Maximum password length",
        ge=1,
        le=256,
    )

    # Character requirements
    require_uppercase: bool = Field(
        default=True,
        description="Require at least one uppercase letter",
    )

    require_lowercase: bool = Field(
        default=True,
        description="Require at least one lowercase letter",
    )

    require_numbers: bool = Field(
        default=True,
        description="Require at least one number",
    )

    require_symbols: bool = Field(
        default=False,
        description="Require at least one special symbol",
    )

    min_uppercase: int = Field(
        default=1,
        description="Minimum number of uppercase letters",
        ge=0,
    )

    min_lowercase: int = Field(
        default=1,
        description="Minimum number of lowercase letters",
        ge=0,
    )

    min_numbers: int = Field(
        default=1,
        description="Minimum number of numeric characters",
        ge=0,
    )

    min_symbols: int = Field(
        default=0,
        description="Minimum number of special symbols",
        ge=0,
    )

    # Symbol configuration
    allowed_symbols: str = Field(
        default="!@#$%^&*()_+-=[]{}|;:,.<>?",
        description="Allowed special symbols",
    )

    # Password lifecycle
    max_age_days: int | None = Field(
        default=90,
        description="Maximum password age in days",
        ge=1,
    )

    min_age_days: int = Field(
        default=1,
        description="Minimum password age before change allowed",
        ge=0,
    )

    history_count: int = Field(
        default=5,
        description="Number of previous passwords to remember",
        ge=0,
        le=100,
    )

    # Additional constraints
    prevent_common_passwords: bool = Field(
        default=True,
        description="Prevent use of common/weak passwords",
    )

    prevent_user_info: bool = Field(
        default=True,
        description="Prevent passwords containing user info",
    )

    prevent_dictionary_words: bool = Field(
        default=False,
        description="Prevent dictionary words in passwords",
    )

    require_change_on_first_login: bool = Field(
        default=True,
        description="Force password change on first login",
    )

    allow_password_reset: bool = Field(
        default=True,
        description="Allow users to reset their own passwords",
    )

    reset_token_validity_minutes: int = Field(
        default=60,
        description="Password reset token validity in minutes",
        ge=1,
    )

    # Failed attempt handling
    max_failed_attempts: int = Field(
        default=5,
        description="Maximum failed login attempts before lockout",
        ge=1,
    )

    lockout_duration_minutes: int = Field(
        default=30,
        description="Account lockout duration in minutes",
        ge=1,
    )

    @classmethod
    def create_minimal(cls) -> "ModelPasswordPolicy":
        """Create minimal password policy."""
        return cls(
            min_length=6,
            require_uppercase=False,
            require_lowercase=True,
            require_numbers=False,
            require_symbols=False,
            max_age_days=None,
            prevent_common_passwords=False,
            max_failed_attempts=10,
        )

    @classmethod
    def create_standard(cls) -> "ModelPasswordPolicy":
        """Create standard password policy."""
        return cls()  # Use defaults

    @classmethod
    def create_strict(cls) -> "ModelPasswordPolicy":
        """Create strict password policy."""
        return cls(
            min_length=12,
            require_uppercase=True,
            require_lowercase=True,
            require_numbers=True,
            require_symbols=True,
            min_symbols=1,
            max_age_days=60,
            history_count=10,
            prevent_dictionary_words=True,
            max_failed_attempts=3,
            lockout_duration_minutes=60,
        )

    @classmethod
    def create_maximum(cls) -> "ModelPasswordPolicy":
        """Create maximum security password policy."""
        return cls(
            min_length=16,
            require_uppercase=True,
            require_lowercase=True,
            require_numbers=True,
            require_symbols=True,
            min_uppercase=2,
            min_lowercase=2,
            min_numbers=2,
            min_symbols=2,
            max_age_days=30,
            min_age_days=1,
            history_count=24,
            prevent_common_passwords=True,
            prevent_user_info=True,
            prevent_dictionary_words=True,
            max_failed_attempts=3,
            lockout_duration_minutes=120,
            reset_token_validity_minutes=15,
        )
