"""Input State Source Type.

Type-safe input state source structure.
"""


class ModelInputStateSourceType(dict, total=False):
    """Type-safe input state source structure."""

    version: object | None  # Use object with runtime type checking instead of Any
    name: str
    description: str
    tags: list[str]
    priority: int
    metadata: dict[str, str]
    context: str
