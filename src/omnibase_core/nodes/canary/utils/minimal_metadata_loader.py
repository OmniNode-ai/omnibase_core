"""
Minimal metadata loader for canary testing.

Provides basic metadata without complex schema loading when we already have Pydantic models.
"""


class MinimalMetadataLoader:
    """
    Minimal metadata loader that provides basic node information.

    This is a simplified implementation for canary testing that doesn't
    require complex schema loading since Pydantic models handle validation.
    """

    def __init__(self):
        """Initialize with basic metadata."""
        self.metadata = {
            "name": "canary_node",
            "version": "1.0.0",
            "description": "Canary testing node",
            "author": "ONEX",
            "meta_type": "node",
            "lifecycle": "active",
        }

    def get_schema(self, schema_name: str) -> dict:
        """Get a basic schema (not used with Pydantic models)."""
        return {"type": "object", "properties": {}}

    def validate_data(self, data: dict, schema_name: str) -> bool:
        """Validation is handled by Pydantic models."""
        return True

    def load_metadata(self) -> dict:
        """Load basic metadata."""
        return self.metadata.copy()
