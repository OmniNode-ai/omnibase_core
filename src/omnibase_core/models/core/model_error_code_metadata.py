from pydantic import BaseModel


class ModelErrorCodeMetadata(BaseModel):
    """Represents error code metadata with enhanced information"""

    code: str
    number: int
    description: str
    exit_code: int
    category: str
