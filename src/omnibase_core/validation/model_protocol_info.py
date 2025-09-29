"""
Protocol Information Model.

Dataclass for storing information about discovered protocols.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ModelProtocolInfo:
    """Information about a discovered protocol."""

    name: str
    file_path: str
    repository: str
    methods: list[str]
    signature_hash: str
    line_count: int
    imports: list[str]


# Export the model
__all__ = ["ModelProtocolInfo"]
