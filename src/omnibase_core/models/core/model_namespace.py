"""
Namespace model.
"""

from typing import TYPE_CHECKING, Any, ClassVar

from pydantic import BaseModel

if TYPE_CHECKING:
    from pathlib import Path


class ModelNamespace(BaseModel):
    """
    Canonical ONEX namespace type. Handles normalization, validation, and construction from file paths.
    Always enforces the canonical prefix from project.onex.yaml.
    Pattern: <filetype>://<prefix>.<subdirs>.<stem> (filetype is the extension, e.g., python, yaml, json, md)
    Serializes as a single-line URI string, never as a mapping.
    """

    value: str

    CANONICAL_SCHEME_MAP: ClassVar[dict[str, str]] = {
        "py": "python",
        "python": "python",
        "md": "markdown",
        "markdown": "markdown",
        "yml": "yaml",
        "yaml": "yaml",
        "json": "json",
        "cli": "cli",
        "docker": "docker",
    }

    @classmethod
    def normalize_scheme(cls, scheme: str) -> str:
        return cls.CANONICAL_SCHEME_MAP.get(scheme.lower(), scheme.lower())

    @classmethod
    def from_path(cls, path: "Path") -> "ModelNamespace":
        from omnibase_core.models.core.model_project_metadata import (
            get_canonical_namespace_prefix,
        )

        # Always use Path for safety
        if not hasattr(path, "parts"):
            from pathlib import Path as _Path

            path = _Path(path)
        raw_ext = path.suffix[1:] if path.suffix.startswith(".") else path.suffix
        # Canonical extension mapping
        ext_map = {
            "py": "python",
            "md": "markdown",
            "markdown": "markdown",
            "yaml": "yaml",
            "yml": "yaml",
            "log": "log",
            "txt": "text",
        }
        ext = ext_map.get(raw_ext.lower(), raw_ext.lower() or "file")
        parts = list(path.parts)
        # Remove any leading '.' from parts
        if parts and parts[0] == ".":
            parts = parts[1:]
        canonical_prefix = get_canonical_namespace_prefix()
        # Find the canonical prefix in the path and slice from there
        if canonical_prefix in parts:
            idx = parts.index(canonical_prefix)
            ns_parts = parts[idx:]
        else:
            ns_parts = parts
        # Remove any leading '.' from ns_parts again (paranoia)
        if ns_parts and ns_parts[0].startswith("."):
            ns_parts[0] = ns_parts[0].lstrip(".")
        # For all files, include the extension in the last segment for uniqueness, unless already present
        if ext and ext != "python":
            if not ns_parts[-1].endswith(f"_{ext}"):
                # Remove extension from last part if present
                if ns_parts[-1].endswith(f".{raw_ext}"):
                    ns_parts[-1] = ns_parts[-1][: -(len(raw_ext) + 1)]
                ns_parts[-1] = f"{ns_parts[-1]}_{ext}"
        # For python files, strip the extension
        elif raw_ext and ns_parts[-1].endswith(f".{raw_ext}"):
            ns_parts[-1] = ns_parts[-1][: -(len(raw_ext) + 1)]
        # Remove any accidental double dots
        ns = f"{ext}://{'.'.join(ns_parts)}"
        return cls(value=ns)

    def to_serializable_dict(self) -> str:
        return self.value

    def __str__(self) -> str:
        return self.value

    def model_dump(self, *args: Any, **kwargs: Any) -> str:  # type: ignore[override]  # Returns str instead of dict for namespace string serialization
        # Always dump as a string for YAML/JSON
        return self.value

    @classmethod
    def __get_pydantic_json_schema__(cls, core_schema: Any, handler: Any) -> Any:
        # Ensure schema is string, not object
        return {"type": "string"}
