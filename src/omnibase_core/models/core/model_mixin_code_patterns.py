"""Pydantic model for mixin code generation patterns.

This module provides the ModelMixinCodePatterns class for defining
code generation patterns for mixins.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.core.model_mixin_method import ModelMixinMethod
from omnibase_core.models.core.model_mixin_property import ModelMixinProperty


class ModelMixinCodePatterns(BaseModel):
    """Code generation patterns for mixin.

    Attributes:
        inheritance: Inheritance pattern
        initialization: Initialization code
        methods: Method definitions
        properties: Property definitions
    """

    model_config = ConfigDict(extra="forbid")

    inheritance: str = Field("", description="Inheritance pattern")
    initialization: str = Field("", description="Initialization code")
    methods: list[ModelMixinMethod] = Field(default_factory=list, description="Methods")
    properties: list[ModelMixinProperty] = Field(
        default_factory=list, description="Properties"
    )
