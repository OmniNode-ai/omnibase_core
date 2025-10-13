"""ModelRequiredFieldsModel.

Strongly typed model for the required fields in a JSON schema.
Wraps a list[Any]of required property names.
"""

from typing import Any

from pydantic import RootModel


class ModelRequiredFieldsModel(RootModel[Any]):
    """
    Strongly typed model for the required fields in a JSON schema.
    Wraps a list[Any]of required property names.
    """

    root: list[str]


# Compatibility alias
RequiredFieldsModel = ModelRequiredFieldsModel
