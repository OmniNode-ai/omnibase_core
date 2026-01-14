"""
Generic typed metrics model.

Unified generic model replacing type-specific metrics variants.
Follows ONEX one-model-per-file naming conventions.
"""

from __future__ import annotations

import hashlib
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.types import TypedDictMetadataDict, TypedDictSerializedModel
from omnibase_core.types.type_constraints import SimpleValueType

# Use consolidated SimpleValueType instead of redundant TypeVar


class ModelTypedMetrics[SimpleValueType](BaseModel):
    """Generic metrics model replacing type-specific variants.
    Implements Core protocols:
    - ProtocolMetadataProvider: Metadata management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    metric_id: UUID = Field(default=..., description="UUID for metric identifier")
    metric_display_name: str = Field(
        default="",
        description="Human-readable metric name",
    )
    value: SimpleValueType = Field(default=..., description="Typed metric value")
    unit: str = Field(default="", description="Unit of measurement")
    description: str = Field(default="", description="Metric description")

    @classmethod
    def string_metric(
        cls,
        name: str,
        value: str,
        unit: str = "",
        description: str = "",
    ) -> ModelTypedMetrics[str]:
        """Create a string metric."""
        import hashlib

        metric_hash = hashlib.sha256(name.encode()).hexdigest()
        metric_id = UUID(
            f"{metric_hash[:8]}-{metric_hash[8:12]}-{metric_hash[12:16]}-{metric_hash[16:20]}-{metric_hash[20:32]}",
        )

        return ModelTypedMetrics[str](
            metric_id=metric_id,
            metric_display_name=name,
            value=value,
            unit=unit,
            description=description,
        )

    @classmethod
    def int_metric(
        cls,
        name: str,
        value: int,
        unit: str = "",
        description: str = "",
    ) -> ModelTypedMetrics[int]:
        """Create an integer metric."""

        metric_hash = hashlib.sha256(name.encode()).hexdigest()
        metric_id = UUID(
            f"{metric_hash[:8]}-{metric_hash[8:12]}-{metric_hash[12:16]}-{metric_hash[16:20]}-{metric_hash[20:32]}",
        )

        return ModelTypedMetrics[int](
            metric_id=metric_id,
            metric_display_name=name,
            value=value,
            unit=unit,
            description=description,
        )

    @classmethod
    def float_metric(
        cls,
        name: str,
        value: float,
        unit: str = "",
        description: str = "",
    ) -> ModelTypedMetrics[float]:
        """Create a float metric."""

        metric_hash = hashlib.sha256(name.encode()).hexdigest()
        metric_id = UUID(
            f"{metric_hash[:8]}-{metric_hash[8:12]}-{metric_hash[12:16]}-{metric_hash[16:20]}-{metric_hash[20:32]}",
        )

        return ModelTypedMetrics[float](
            metric_id=metric_id,
            metric_display_name=name,
            value=value,
            unit=unit,
            description=description,
        )

    @classmethod
    def boolean_metric(
        cls,
        name: str,
        value: bool,
        unit: str = "",
        description: str = "",
    ) -> ModelTypedMetrics[bool]:
        """Create a boolean metric."""

        metric_hash = hashlib.sha256(name.encode()).hexdigest()
        metric_id = UUID(
            f"{metric_hash[:8]}-{metric_hash[8:12]}-{metric_hash[12:16]}-{metric_hash[16:20]}-{metric_hash[20:32]}",
        )

        return ModelTypedMetrics[bool](
            metric_id=metric_id,
            metric_display_name=name,
            value=value,
            unit=unit,
            description=description,
        )

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )

    # Protocol method implementations

    def get_metadata(self) -> TypedDictMetadataDict:
        """
        Get metadata as dictionary for ProtocolMetadataProvider protocol.

        Returns a TypedDictMetadataDict containing metric information with
        type-parameterized value. The metric display name and description
        map to standard top-level keys when present.

        Returns:
            TypedDictMetadataDict with the following structure:
            - "name": metric_display_name (only if non-empty string)
            - "description": description field (only if non-empty string)
            - "metadata": Dict containing:
                - "metric_id": String representation of the metric UUID
                - "value": The typed metric value (str, int, float, or bool
                  depending on generic type parameter)
                - "unit": Unit of measurement string (only if non-empty)

        Example:
            >>> metric = ModelTypedMetrics.int_metric(
            ...     name="request_count",
            ...     value=42,
            ...     unit="requests",
            ...     description="Total HTTP requests"
            ... )
            >>> metadata = metric.get_metadata()
            >>> metadata["name"]
            'request_count'
            >>> metadata["description"]
            'Total HTTP requests'
            >>> metadata["metadata"]["value"]
            42
            >>> metadata["metadata"]["unit"]
            'requests'
        """
        result: TypedDictMetadataDict = {}
        if self.metric_display_name:
            result["name"] = self.metric_display_name
        if self.description:
            result["description"] = self.description
        from typing import cast

        from omnibase_core.types.type_serializable_value import SerializableValue

        # Cast SimpleValueType to SerializableValue for type compatibility
        metadata_inner: dict[str, SerializableValue] = {
            "metric_id": str(self.metric_id),
            "value": cast(SerializableValue, self.value),
        }
        if (
            self.unit
        ):  # Only include unit if non-empty (consistent with name/description)
            metadata_inner["unit"] = self.unit
        result["metadata"] = metadata_inner
        return result

    def set_metadata(self, metadata: TypedDictMetadataDict) -> bool:
        """Set metadata from dictionary (ProtocolMetadataProvider protocol)."""
        try:
            for key, value in metadata.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except Exception:  # fallback-ok: protocol method contract requires bool return - False indicates metadata update failed safely
            return False

    def serialize(self) -> TypedDictSerializedModel:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol)."""
        return True


__all__ = ["ModelTypedMetrics"]
