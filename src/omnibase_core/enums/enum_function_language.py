"""
Function language enumeration.

Defines supported languages for function discovery and tool definitions.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumFunctionLanguage(StrValueHelper, str, Enum):
    """
    Supported function discovery languages.

    Represents the programming or configuration languages that can be
    used for function definitions and tool discovery.
    """

    PYTHON = "python"  # Python functions and scripts
    JAVASCRIPT = "javascript"  # JavaScript functions
    TYPESCRIPT = "typescript"  # TypeScript functions
    BASH = "bash"  # Bash shell scripts
    SHELL = "shell"  # Generic shell scripts
    YAML = "yaml"  # YAML-based configuration
    JSON = "json"  # JSON-based configuration

    @classmethod
    def is_scripting_language(cls, language: EnumFunctionLanguage) -> bool:
        """
        Check if language is a scripting language.

        Args:
            language: The language to check

        Returns:
            True if language is PYTHON, BASH, SHELL, or JAVASCRIPT
        """
        return language in {cls.PYTHON, cls.BASH, cls.SHELL, cls.JAVASCRIPT}

    @classmethod
    def is_typed_language(cls, language: EnumFunctionLanguage) -> bool:
        """
        Check if language supports static typing.

        Args:
            language: The language to check

        Returns:
            True if language is TYPESCRIPT or PYTHON (with type hints)
        """
        return language in {cls.TYPESCRIPT, cls.PYTHON}

    @classmethod
    def is_configuration_format(cls, language: EnumFunctionLanguage) -> bool:
        """
        Check if language is a configuration format.

        Args:
            language: The language to check

        Returns:
            True if language is YAML or JSON
        """
        return language in {cls.YAML, cls.JSON}

    @classmethod
    def get_file_extension(cls, language: EnumFunctionLanguage) -> str:
        """
        Get typical file extension for language.

        Args:
            language: The language to get extension for

        Returns:
            File extension string (e.g., ".py", ".ts")
        """
        extensions = {
            cls.PYTHON: ".py",
            cls.JAVASCRIPT: ".js",
            cls.TYPESCRIPT: ".ts",
            cls.BASH: ".sh",
            cls.SHELL: ".sh",
            cls.YAML: ".yaml",
            cls.JSON: ".json",
        }
        return extensions.get(language, "")


# Export the enum
__all__ = ["EnumFunctionLanguage"]
