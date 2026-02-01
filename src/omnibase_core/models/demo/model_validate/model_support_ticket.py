"""Support ticket input model for model-validate demo scenario."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums import EnumCustomerTier, EnumSupportChannel


class ModelSupportTicket(BaseModel):
    """Input model representing a customer support ticket.

    This model captures the essential information from a support ticket
    that would be passed to an LLM for classification and response generation.
    """

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    ticket_id: str = Field(  # string-id-ok: external ticketing system identifier
        description="Unique identifier for the ticket"
    )
    created_at: datetime = Field(description="Timestamp when ticket was created")
    customer_tier: EnumCustomerTier = Field(
        description="Customer subscription tier (free, pro, enterprise)"
    )
    channel: EnumSupportChannel = Field(
        description="Communication channel (email, chat, web)"
    )
    language: str = Field(
        default="en", description="ISO 639-1 language code of the ticket content"
    )
    subject: str = Field(description="Subject line of the support ticket")
    body: str = Field(description="Full text content of the support ticket")

    # Optional fields for richer context
    attachments: list[str] | None = Field(
        default=None, description="List of attachment filenames if any"
    )
    product_area: str | None = Field(
        default=None, description="Product area or feature the ticket relates to"
    )
    priority_hint: str | None = Field(
        default=None, description="Customer-indicated priority (low, medium, high)"
    )
    previous_contact_count: int | None = Field(
        default=None,
        ge=0,
        description="Number of previous contacts from this customer",
    )


__all__ = ["ModelSupportTicket"]
