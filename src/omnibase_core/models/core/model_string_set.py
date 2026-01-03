"""Model for managing sets of strings."""

from collections.abc import Iterator

from pydantic import BaseModel, Field


class ModelStringSet(BaseModel):
    """
    Strongly-typed model for managing sets of strings.

    Replaces Set[str] to comply with ONEX standards
    requiring specific typed models instead of generic types.
    """

    elements: list[str] = Field(
        default_factory=list,
        description="List of unique string elements",
    )

    def __post_init__(self) -> None:
        """Ensure uniqueness of elements."""
        self.elements = list(dict.fromkeys(self.elements))

    def add(self, element: str) -> None:
        """Add an element to the set."""
        if element not in self.elements:
            self.elements.append(element)

    def remove(self, element: str) -> bool:
        """Remove an element from the set."""
        if element in self.elements:
            self.elements.remove(element)
            return True
        return False

    def discard(self, element: str) -> None:
        """Remove element if present, no error if not."""
        self.remove(element)

    def contains(self, element: str) -> bool:
        """Check if element is in the set."""
        return element in self.elements

    def clear(self) -> None:
        """Remove all elements."""
        self.elements.clear()

    def size(self) -> int:
        """Get number of elements."""
        return len(self.elements)

    def is_empty(self) -> bool:
        """Check if set is empty."""
        return len(self.elements) == 0

    def to_list(self) -> list[str]:
        """Get list representation."""
        return self.elements.copy()

    def union(self, other: "ModelStringSet") -> "ModelStringSet":
        """Return union of two sets."""
        result = ModelStringSet(elements=self.elements.copy())
        for elem in other.elements:
            result.add(elem)
        return result

    def intersection(self, other: "ModelStringSet") -> "ModelStringSet":
        """Return intersection of two sets."""
        result = ModelStringSet()
        for elem in self.elements:
            if other.contains(elem):
                result.add(elem)
        return result

    def difference(self, other: "ModelStringSet") -> "ModelStringSet":
        """Return elements in self but not in other."""
        result = ModelStringSet()
        for elem in self.elements:
            if not other.contains(elem):
                result.add(elem)
        return result

    def __contains__(self, item: str) -> bool:
        """Support 'in' operator."""
        return self.contains(item)

    def __len__(self) -> int:
        """Support len() function."""
        return self.size()

    def __iter__(self) -> Iterator[str]:  # type: ignore[override]
        """Support iteration."""
        return iter(self.elements)
