from __future__ import annotations

from typing import TypedDict

"""
Execution-related factory parameters.
Implements omnibase_spi protocols:
- Configurable: Configuration management capabilities
- Serializable: Data serialization/deserialization
- Validatable: Validation and verification
- Nameable: Name management interface
"""


class TypedDictExecutionParams(TypedDict, total=False):
    """Execution-related factory parameters.
    Implements omnibase_spi protocols:
    - Configurable: Configuration management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    - Nameable: Name management interface
    """

    success: bool
    exit_code: int
    error_message: str
    data: object  # ONEX compliance - use object instead of Any for generic data
