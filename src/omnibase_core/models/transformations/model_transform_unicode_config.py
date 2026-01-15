"""
Configuration for unicode normalization.

This module defines the configuration model for NORMALIZE_UNICODE transformations
in contract-driven NodeCompute v1.0.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict

from omnibase_core.enums.enum_unicode_form import EnumUnicodeForm


class ModelTransformUnicodeConfig(BaseModel):
    """
    Configuration for unicode normalization.

    Attributes:
        config_type: Discriminator field for union type resolution.
        form: The unicode normalization form to apply. Defaults to NFC.
    """

    config_type: Literal["normalize_unicode"] = "normalize_unicode"
    form: EnumUnicodeForm = EnumUnicodeForm.NFC

    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)
