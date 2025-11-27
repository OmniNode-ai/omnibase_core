from pydantic import BaseModel, ConfigDict, Field


class ModelContractDependency(BaseModel):
    """Model representing a single dependency in a contract."""

    model_config = ConfigDict(extra="ignore")

    name: str = Field(default=..., description="Dependency service name")
    type: str = Field(
        default=..., description="Dependency type (utility, protocol, service)"
    )
    class_name: str | None = Field(
        default=None,
        alias="class",
        description="Class name for the dependency",
    )
    module: str | None = Field(
        default=None, description="Module path for the dependency"
    )
    description: str | None = Field(default=None, description="Dependency description")
