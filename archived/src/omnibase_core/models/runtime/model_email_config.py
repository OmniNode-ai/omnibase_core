"""Email notification configuration model."""

from pydantic import BaseModel, Field


class ModelEmailConfig(BaseModel):
    """Email notification configuration."""

    smtp_server: str = Field(..., description="SMTP server hostname")
    smtp_port: int = Field(default=587, description="SMTP server port")
    username: str = Field(..., description="SMTP username")
    password: str = Field(..., description="SMTP password")
    from_email: str = Field(..., description="From email address")
    to_emails: list[str] = Field(..., description="Recipient email addresses")
    use_tls: bool = Field(default=True, description="Use TLS encryption")
