"""Artifact type enumeration for ONEX core."""

import enum


class EnumArtifactType(enum.StrEnum):
    """Artifact types for ONEX ecosystem."""

    TOOL = "tool"
    NODE = "node"
    MODEL = "model"
    SCHEMA = "schema"
    CONTRACT = "contract"
    MANIFEST = "manifest"
    TEMPLATE = "template"
