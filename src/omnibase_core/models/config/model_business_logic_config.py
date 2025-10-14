from pydantic import BaseModel, Field


class ModelBusinessLogicConfig(BaseModel):
    """Business logic configuration model."""

    customer_purchase_threshold: float = Field(
        default=1000.0, description="Customer purchase amount threshold"
    )
    customer_loyalty_years_threshold: int = Field(
        default=2, description="Customer loyalty years threshold"
    )
    customer_support_tickets_threshold: int = Field(
        default=3, description="Max support tickets for good score"
    )
    customer_premium_score_threshold: int = Field(
        default=30, description="Score threshold for premium tier"
    )
    customer_purchase_score_points: int = Field(
        default=20, description="Points for high purchase history"
    )
    customer_loyalty_score_points: int = Field(
        default=15, description="Points for loyalty"
    )
    customer_support_score_points: int = Field(
        default=10, description="Points for low support tickets"
    )
