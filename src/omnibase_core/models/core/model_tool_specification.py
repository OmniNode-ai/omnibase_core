"""Tool specification model for ContractLoader."""

from pydantic import BaseModel, Field


class ModelToolSpecification(BaseModel):
    """Tool specification from contract."""

    main_tool_class: str = Field(description="Main tool class name")
    business_logic_pattern: str = Field(
        default="stateful",
        description="Business logic pattern",
    )

    model_config = {
        "extra": "allow",
    }
