"""ModelSemVerConstraint - Strongly typed semantic version constraints."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.model.core.model_semver import ModelSemVer


class ModelSemVerConstraint(BaseModel):
    """Strongly typed semver constraint - no string support.

    Supports multiple constraint patterns through structured data:
    - Range constraints: min/max version with inclusive/exclusive bounds
    - Exact version: exact match required
    - Compatible version: ^x.y.z style (same major version)
    - Minimum version: >= x.y.z with no upper bound
    """

    # Range constraint fields
    min_version: ModelSemVer | None = Field(None, alias="min")
    max_version: ModelSemVer | None = Field(None, alias="max")
    min_inclusive: bool = True
    max_inclusive: bool = False

    # Shorthand fields (processed by validator)
    exact: ModelSemVer | None = None
    compatible: ModelSemVer | None = None
    minimum: ModelSemVer | None = None

    # Optional constraints
    allow_prerelease: bool = False
    allow_unstable: bool = False

    model_config = ConfigDict(
        populate_by_name=True,
    )  # Allow both "min_version" and "min"

    @model_validator(mode="before")
    @classmethod
    def parse_constraint_string(cls, v: Any) -> Any:
        """Parse constraint strings like '>=1.0.0,<2.0.0' into ModelSemVerConstraint fields."""
        if isinstance(v, str):
            # Parse common constraint patterns
            if "," in v:
                # Range constraint like ">=1.0.0,<2.0.0"
                parts = [p.strip() for p in v.split(",")]
                result = {}
                for part in parts:
                    if part.startswith(">="):
                        result["min_version"] = ModelSemVer.parse(part[2:])
                        result["min_inclusive"] = True
                    elif part.startswith(">"):
                        result["min_version"] = ModelSemVer.parse(part[1:])
                        result["min_inclusive"] = False
                    elif part.startswith("<="):
                        result["max_version"] = ModelSemVer.parse(part[2:])
                        result["max_inclusive"] = True
                    elif part.startswith("<"):
                        result["max_version"] = ModelSemVer.parse(part[1:])
                        result["max_inclusive"] = False
                    elif part.startswith("="):
                        result["exact"] = ModelSemVer.parse(part[1:])
                    else:
                        # Assume exact match
                        result["exact"] = ModelSemVer.parse(part)
                return result
            if v.startswith(">="):
                return {"min_version": ModelSemVer.parse(v[2:]), "min_inclusive": True}
            if v.startswith(">"):
                return {"min_version": ModelSemVer.parse(v[1:]), "min_inclusive": False}
            if v.startswith("<="):
                return {"max_version": ModelSemVer.parse(v[2:]), "max_inclusive": True}
            if v.startswith("<"):
                return {"max_version": ModelSemVer.parse(v[1:]), "max_inclusive": False}
            if v.startswith("^"):
                return {"compatible": ModelSemVer.parse(v[1:])}
            if v.startswith("~"):
                return {"minimum": ModelSemVer.parse(v[1:])}
            # Assume exact version
            return {"exact": ModelSemVer.parse(v)}
        if isinstance(v, dict):
            return v
        if hasattr(v, "__dict__"):
            return v.__dict__
        return v

    @model_validator(mode="after")
    def apply_shorthands(self) -> "ModelSemVerConstraint":
        """Convert shorthand properties to full constraints."""
        if self.exact:
            # Exact version match
            self.min_version = self.exact
            self.max_version = self.exact
            self.min_inclusive = True
            self.max_inclusive = True
            self.exact = None  # Clear shorthand
        elif self.compatible:
            # Compatible range (^x.y.z style) - same major version
            v = self.compatible
            self.min_version = v
            self.max_version = ModelSemVer(major=v.major + 1, minor=0, patch=0)
            self.min_inclusive = True
            self.max_inclusive = False
            self.compatible = None  # Clear shorthand
        elif self.minimum:
            # Minimum version only (>= x.y.z)
            self.min_version = self.minimum
            self.max_version = None
            self.min_inclusive = True
            self.minimum = None  # Clear shorthand

        return self

    def matches(self, version: ModelSemVer) -> bool:
        """Check if version satisfies this constraint."""
        # Check minimum bound
        if self.min_version:
            if self.min_inclusive:
                if version < self.min_version:
                    return False
            elif version <= self.min_version:
                return False

        # Check maximum bound
        if self.max_version:
            if self.max_inclusive:
                if version > self.max_version:
                    return False
            elif version >= self.max_version:
                return False

        # Check prerelease policy
        return not (not self.allow_prerelease and version.prerelease)

    def __str__(self) -> str:
        """Human-readable constraint representation."""
        if self.min_version and self.max_version:
            min_op = ">=" if self.min_inclusive else ">"
            max_op = "<=" if self.max_inclusive else "<"
            return f"{min_op}{self.min_version},{max_op}{self.max_version}"
        if self.min_version:
            op = ">=" if self.min_inclusive else ">"
            return f"{op}{self.min_version}"
        if self.max_version:
            op = "<=" if self.max_inclusive else "<"
            return f"{op}{self.max_version}"
        return "any version"
