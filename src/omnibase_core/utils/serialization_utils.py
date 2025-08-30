#!/usr/bin/env python3
"""
Serialization Utilities

Provides clean, efficient serialization utilities for common data conversion
tasks, particularly for event bus JSON serialization.
"""

import uuid
from typing import Any


class SerializationUtils:
    """Utility class for common serialization tasks."""

    @staticmethod
    def serialize_for_json(obj: Any, visited: set[int] | None = None) -> Any:
        """
        Recursively convert objects to JSON-serializable format.

        Handles:
        - UUID objects -> strings
        - Pydantic models -> dicts
        - Nested objects and collections
        - Circular reference prevention

        Args:
            obj: Object to serialize
            visited: Set of visited object IDs for cycle detection

        Returns:
            JSON-serializable representation of the object
        """
        if visited is None:
            visited = set()

        # Prevent infinite recursion
        obj_id = id(obj)
        if obj_id in visited:
            return str(obj) if hasattr(obj, "__str__") else repr(obj)

        # Skip callable objects
        if callable(obj):
            return None

        # Handle different types
        try:
            # UUID objects
            if isinstance(obj, uuid.UUID):
                return str(obj)

            # Check for UUID-like objects by type name
            if hasattr(obj, "__str__") and "UUID" in str(type(obj)):
                return str(obj)

            # Basic JSON-serializable types
            if obj is None or isinstance(obj, str | int | float | bool):
                return obj

            # Track this object to prevent cycles
            visited.add(obj_id)

            try:
                # Dictionaries
                if isinstance(obj, dict):
                    return {
                        k: SerializationUtils.serialize_for_json(v, visited)
                        for k, v in obj.items()
                        if not callable(v)
                    }

                # Lists and tuples
                if isinstance(obj, list | tuple):
                    return [
                        SerializationUtils.serialize_for_json(item, visited)
                        for item in obj
                        if not callable(item)
                    ]

                # Sets
                if isinstance(obj, set):
                    return [
                        SerializationUtils.serialize_for_json(item, visited)
                        for item in obj
                        if not callable(item)
                    ]

                # Pydantic models (have model_dump method)
                if hasattr(obj, "model_dump"):
                    try:
                        data = obj.model_dump(mode="json")
                        return SerializationUtils.serialize_for_json(data, visited)
                    except Exception:
                        # Fall through to __dict__ handling
                        pass

                # Objects with __dict__
                if hasattr(obj, "__dict__"):
                    return {
                        k: SerializationUtils.serialize_for_json(v, visited)
                        for k, v in obj.__dict__.items()
                        if not callable(v) and not k.startswith("_")
                    }

                # Fallback to string representation
                return str(obj)

            finally:
                visited.remove(obj_id)

        except Exception:
            # Safe fallback
            return str(obj) if hasattr(obj, "__str__") else repr(obj)

    @staticmethod
    def clean_event_data(
        event_data: dict[str, Any],
        exclude_fields: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Clean event data for JSON serialization, removing problematic fields.

        Args:
            event_data: Raw event data dictionary
            exclude_fields: Fields to exclude from output

        Returns:
            Cleaned dictionary ready for JSON serialization
        """
        if exclude_fields is None:
            exclude_fields = ["event_type", "node_id", "correlation_id", "timestamp"]

        # Remove excluded fields and serialize remaining data
        return {
            k: SerializationUtils.serialize_for_json(v)
            for k, v in event_data.items()
            if k not in exclude_fields and not callable(v)
        }

    @staticmethod
    def prepare_correlation_id(correlation_id: Any) -> str:
        """
        Ensure correlation ID is a string.

        Args:
            correlation_id: Correlation ID (may be UUID or string)

        Returns:
            String representation of correlation ID
        """
        if correlation_id is None:
            return None

        if isinstance(correlation_id, str):
            return correlation_id

        if isinstance(correlation_id, uuid.UUID):
            return str(correlation_id)

        # Handle UUID-like objects
        if hasattr(correlation_id, "__str__") and "UUID" in str(type(correlation_id)):
            return str(correlation_id)

        return str(correlation_id)
