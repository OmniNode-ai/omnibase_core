"""
Node Category Enum

Strongly typed enum for node categories following ONEX conventions.
Replaces string-based category field with type-safe enum values.
"""

from enum import Enum


class EnumNodeCategory(str, Enum):
    """
    Node category classification for organization and workflow management.

    Provides strongly typed categories for different types of nodes
    to improve type safety and development experience.
    """

    # Core generation nodes
    GENERATION = "generation"
    """Nodes that generate code, models, or other artifacts"""

    # Validation and compliance nodes
    VALIDATION = "validation"
    """Nodes that validate existing code, contracts, or compliance"""

    # Template processing nodes
    TEMPLATE = "template"
    """Nodes that process templates and token replacement"""

    # System maintenance nodes
    MAINTENANCE = "maintenance"
    """Nodes that handle maintenance operations and fixes"""

    # Command line interface nodes
    CLI = "cli"
    """Nodes that handle CLI commands and operations"""

    # Discovery and analysis nodes
    DISCOVERY = "discovery"
    """Nodes that discover and analyze existing code structure"""

    # Schema processing nodes
    SCHEMA = "schema"
    """Nodes that process, generate, or validate schemas"""

    # Runtime execution nodes
    RUNTIME = "runtime"
    """Nodes that handle runtime operations and execution"""

    # Logging and monitoring nodes
    LOGGING = "logging"
    """Nodes that handle logging, monitoring, and observability"""

    # Testing and quality assurance nodes
    TESTING = "testing"
    """Nodes that run tests and quality assurance operations"""

    # Unknown or miscellaneous nodes
    UNKNOWN = "unknown"
    """Nodes with unknown or miscellaneous functionality"""

    def __str__(self) -> str:
        """String representation returns the enum value."""
        return self.value

    @property
    def description(self) -> str:
        """Get human-readable description of the category."""
        descriptions = {
            self.GENERATION: "Nodes that generate code, models, or other artifacts",
            self.VALIDATION: "Nodes that validate existing code, contracts, or compliance",
            self.TEMPLATE: "Nodes that process templates and token replacement",
            self.MAINTENANCE: "Nodes that handle maintenance operations and fixes",
            self.CLI: "Nodes that handle CLI commands and operations",
            self.DISCOVERY: "Nodes that discover and analyze existing code structure",
            self.SCHEMA: "Nodes that process, generate, or validate schemas",
            self.RUNTIME: "Nodes that handle runtime operations and execution",
            self.LOGGING: "Nodes that handle logging, monitoring, and observability",
            self.TESTING: "Nodes that run tests and quality assurance operations",
            self.UNKNOWN: "Nodes with unknown or miscellaneous functionality",
        }
        return descriptions.get(self, "Unknown category")

    @property
    def priority_weight(self) -> int:
        """Get priority weight for execution ordering (higher = more priority)."""
        priorities = {
            self.RUNTIME: 100,  # Highest priority - core execution
            self.DISCOVERY: 95,  # Early phase - discover structure
            self.GENERATION: 90,  # High priority - generate artifacts
            self.VALIDATION: 80,  # High priority - validate results
            self.TEMPLATE: 70,  # Medium-high - template processing
            self.SCHEMA: 60,  # Medium - schema operations
            self.MAINTENANCE: 50,  # Medium - maintenance tasks
            self.CLI: 40,  # Medium-low - CLI operations
            self.LOGGING: 30,  # Low - logging and monitoring
            self.TESTING: 20,  # Low - testing operations
            self.UNKNOWN: 10,  # Lowest priority - unknown nodes
        }
        return priorities.get(self, 10)

    @classmethod
    def from_string(cls, value: str) -> "EnumNodeCategory":
        """
        Create enum from string value with fallback to UNKNOWN.

        Args:
            value: String value to convert

        Returns:
            Corresponding EnumNodeCategory, or UNKNOWN if not found
        """
        try:
            return cls(value.lower())
        except ValueError:
            return cls.UNKNOWN

    @classmethod
    def get_categories_by_priority(cls) -> list["EnumNodeCategory"]:
        """
        Get all categories ordered by execution priority (highest first).

        Returns:
            List of categories ordered by priority weight
        """
        return sorted(cls, key=lambda cat: cat.priority_weight, reverse=True)
