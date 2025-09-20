"""
Data handling declaration model.
"""

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class ModelDataHandlingDeclaration(BaseModel):
    """Data handling and classification declaration."""

    processes_sensitive_data: bool = Field(
        ...,
        description="Whether this component processes sensitive data requiring special handling",
    )
    data_residency_required: str | None = Field(
        None,
        description="Required data residency region (e.g., 'EU', 'US', 'GDPR-compliant')",
        min_length=2,
        max_length=50,
        pattern=r"^[A-Z][A-Z0-9_-]*$",
    )
    data_classification: (
        Literal["PUBLIC", "INTERNAL", "CONFIDENTIAL", "RESTRICTED"] | None
    ) = Field(
        None, description="Data classification level following security standards"
    )

    @model_validator(mode="after")
    def validate_data_handling_consistency(self) -> "ModelDataHandlingDeclaration":
        """Validate consistency between fields."""
        # If processing sensitive data, should have classification or residency requirements
        if self.processes_sensitive_data:
            if not self.data_classification and not self.data_residency_required:
                raise ValueError(
                    "When processing sensitive data, either data_classification or "
                    "data_residency_required must be specified"
                )

            # Certain classifications require residency requirements
            if self.data_classification in ["CONFIDENTIAL", "RESTRICTED"]:
                if not self.data_residency_required:
                    raise ValueError(
                        f"Data classification '{self.data_classification}' requires "
                        "data_residency_required to be specified"
                    )

        return self
