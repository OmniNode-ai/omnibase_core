"""
Node Output Type Enum

Strongly typed enum for node output types following ONEX conventions.
Replaces string-based output_type field with type-safe enum values.
"""

from enum import Enum


class EnumNodeOutputType(str, Enum):
    """
    Node output type classification for result handling and processing.

    Provides strongly typed output types for different kinds of node results
    to improve type safety and development experience.
    """

    # Code generation outputs
    MODELS = "models"
    """Generates Pydantic models or data structures"""

    ENUMS = "enums"
    """Generates enum definitions and constants"""

    PROTOCOLS = "protocols"
    """Generates protocol interfaces and contracts"""

    # File system outputs
    FILES = "files"
    """Generates physical files on the file system"""

    TEXT = "text"
    """Generates text content or documentation"""

    # Validation and analysis outputs
    REPORTS = "reports"
    """Generates analysis or validation reports"""

    REPORT = "report"
    """Generates a single analysis or validation report"""

    # System and infrastructure outputs
    METADATA = "metadata"
    """Generates metadata, introspection, or configuration data"""

    SCHEMAS = "schemas"
    """Generates JSON schemas or data structure definitions"""

    NODE = "node"
    """Generates complete node structures or configurations"""

    # Maintenance and fix outputs
    FIXES = "fixes"
    """Generates code fixes or corrections"""

    REPORT_AND_FIXES = "report_and_fixes"
    """Generates both analysis reports and fixes"""

    # Command line and interaction outputs
    COMMANDS = "commands"
    """Generates CLI commands or command definitions"""

    # Discovery and analysis outputs
    NODES = "nodes"
    """Discovers and returns node information"""

    # Runtime execution outputs
    BACKEND = "backend"
    """Selects or configures backend systems"""

    RESULT = "result"
    """Generic execution result or outcome"""

    STATUS = "status"
    """System status or health information"""

    # Logging and monitoring outputs
    LOGS = "logs"
    """Generates log entries or logging data"""

    # Testing outputs
    RESULTS = "results"
    """Generates test results or execution outcomes"""

    def __str__(self) -> str:
        """String representation returns the enum value."""
        return self.value

    @property
    def description(self) -> str:
        """Get human-readable description of the output type."""
        descriptions = {
            self.MODELS: "Generates Pydantic models or data structures",
            self.ENUMS: "Generates enum definitions and constants",
            self.PROTOCOLS: "Generates protocol interfaces and contracts",
            self.FILES: "Generates physical files on the file system",
            self.TEXT: "Generates text content or documentation",
            self.REPORTS: "Generates analysis or validation reports",
            self.REPORT: "Generates a single analysis or validation report",
            self.METADATA: "Generates metadata, introspection, or configuration data",
            self.SCHEMAS: "Generates JSON schemas or data structure definitions",
            self.NODE: "Generates complete node structures or configurations",
            self.FIXES: "Generates code fixes or corrections",
            self.REPORT_AND_FIXES: "Generates both analysis reports and fixes",
            self.COMMANDS: "Generates CLI commands or command definitions",
            self.NODES: "Discovers and returns node information",
            self.BACKEND: "Selects or configures backend systems",
            self.RESULT: "Generic execution result or outcome",
            self.STATUS: "System status or health information",
            self.LOGS: "Generates log entries or logging data",
            self.RESULTS: "Generates test results or execution outcomes",
        }
        return descriptions.get(self, "Unknown output type")

    @property
    def is_generator_output(self) -> bool:
        """Check if this output type indicates code/artifact generation."""
        generator_types = {
            self.MODELS,
            self.ENUMS,
            self.PROTOCOLS,
            self.FILES,
            self.TEXT,
            self.METADATA,
            self.SCHEMAS,
            self.NODE,
            self.FIXES,
            self.COMMANDS,
        }
        return self in generator_types

    @property
    def is_analysis_output(self) -> bool:
        """Check if this output type indicates analysis or validation."""
        analysis_types = {
            self.REPORTS,
            self.REPORT,
            self.REPORT_AND_FIXES,
            self.NODES,
            self.STATUS,
            self.RESULTS,
        }
        return self in analysis_types

    @property
    def is_runtime_output(self) -> bool:
        """Check if this output type indicates runtime execution."""
        runtime_types = {
            self.BACKEND,
            self.RESULT,
            self.STATUS,
            self.LOGS,
        }
        return self in runtime_types

    @classmethod
    def from_string(cls, value: str | None) -> "EnumNodeOutputType | None":
        """
        Create enum from string value with fallback to None.

        Args:
            value: String value to convert (can be None)

        Returns:
            Corresponding EnumNodeOutputType, or None if not found or None input
        """
        if value is None:
            return None

        try:
            return cls(value.lower())
        except ValueError:
            return None

    @classmethod
    def get_generator_types(cls) -> list["EnumNodeOutputType"]:
        """
        Get all output types that indicate code/artifact generation.

        Returns:
            List of generator output types
        """
        return [output_type for output_type in cls if output_type.is_generator_output]

    @classmethod
    def get_analysis_types(cls) -> list["EnumNodeOutputType"]:
        """
        Get all output types that indicate analysis or validation.

        Returns:
            List of analysis output types
        """
        return [output_type for output_type in cls if output_type.is_analysis_output]

    @classmethod
    def get_runtime_types(cls) -> list["EnumNodeOutputType"]:
        """
        Get all output types that indicate runtime execution.

        Returns:
            List of runtime output types
        """
        return [output_type for output_type in cls if output_type.is_runtime_output]
