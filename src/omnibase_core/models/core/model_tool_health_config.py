from pydantic import BaseModel, ConfigDict


class ModelConfig(BaseModel):
    """Configuration for tool health status model."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "healthy",
                "timestamp": "2024-01-01T00:00:00",
                "tool_name": "tool_example",
                "version": {
                    "major": 1,
                    "minor": 0,
                    "patch": 0,
                    "prerelease": None,
                    "build": None,
                },
                "checks": {
                    "contract_exists": True,
                    "models_valid": True,
                    "imports_resolvable": True,
                },
            },
        }
    )
