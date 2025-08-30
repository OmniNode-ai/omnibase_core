from pydantic import BaseModel


class ModelEntrypointBlock(BaseModel):
    type: str
    target: str  # Always the filename stem (no extension)
    # No URI string logic, only type/target

    @classmethod
    def from_uri(cls, uri: str) -> "ModelEntrypointBlock":
        """
        Parse a URI string (e.g., 'python://main') into type/target and return ModelEntrypointBlock.
        The target is always the filename stem (no extension).
        """
        if "://" not in uri:
            raise ValueError(f"Invalid entrypoint URI: {uri}")
        type_, target = uri.split("://", 1)
        return cls(type=type_, target=target)

    def to_uri(self) -> str:
        """
        Return the entrypoint as a URI string (e.g., 'python://main') for display/CLI only.
        The target is always the filename stem (no extension).
        """
        return f"{self.type}://{self.target}"


# Backward compatibility alias
EntrypointBlock = ModelEntrypointBlock
